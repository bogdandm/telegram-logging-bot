import json
import logging
import pickle
import sys
import threading
from signal import SIGABRT, SIGTERM, SIGINT
from time import sleep

import redis.exceptions
from telegram import Bot, Update, Chat, ParseMode
from telegram.ext import Updater, ConversationHandler
from telegram.utils.promise import Promise

from telegram_logging.utils.telegram import command_handler, regex_handler


TELEGRAM_MSG_MAX_LEN = 4096 - 10
WAIT_PASSWORD, AUTHORIZED, LISTENING = range(3)


def map_state(st):
    return ["WAIT_PASSWORD", "AUTHORIZED", "LISTENING"][st]


"""
States workflow:

START -> WAIT_PASSWORD <-> AUTHORIZED <-> LISTENING
                 ^                            |
                 |                            |
                 ------------------------------
"""


def get_state(conv_handler: ConversationHandler, chat: Chat):
    state = conv_handler.conversations[(chat.id,) * 2]
    return map_state(state)


STOP_SIGNALS = (SIGINT, SIGTERM, SIGABRT)


class LoggingBot:
    def __init__(self, config_path: str, token: str, password: str):
        self.config = json.load(open(config_path, "r"))
        self.password = password

        self._stopped = threading.Event()
        self.redis_listener_thread = threading.Thread(target=self.redis_listener, name="redis_listener_thread")
        self.data_lock = threading.Lock()
        self.data_saver_thread = threading.Thread(target=self.data_saver, name="data_saver_thread")

        self.updater = Updater(token, user_sig_handler=self.signal_handler)
        self.dispatcher = self.updater.dispatcher
        self.listeners = set()  # Set[chat_id]

        # ===== HANDLERS ======

        @command_handler('start')
        def start_handler(bot: Bot, update: Update):
            bot.send_message(chat_id=update.message.chat_id, text="Please type access password:")
            return WAIT_PASSWORD

        @regex_handler(r"^\w+$")
        def read_password(bot: Bot, update: Update):
            if update.message.text.strip() == self.password:
                bot.send_message(
                    chat_id=update.message.chat_id,
                    parse_mode=ParseMode.MARKDOWN,
                    text="You successfully logged in.\n"
                         "\n"
                         "List of commands:\n"
                         "`/logout` - Logout\n"
                         "`/listen` - Subscribe for error notifications\n"
                         "`/unlisten` (after `/listen`) - Unsubscribe\n"
                )
                return AUTHORIZED
            else:
                bot.send_message(chat_id=update.message.chat_id, text="Wrong password :(")

        @command_handler('logout')
        def logout_handler(bot: Bot, update: Update):
            try:
                self.listeners.remove(update.message.chat_id)
            except KeyError:
                pass
            else:
                bot.send_message(chat_id=update.message.chat_id, text="Stop listening to errors")
            bot.send_message(chat_id=update.message.chat_id, text="You successfully logged out. "
                                                                  "Type password again to log in.")
            return WAIT_PASSWORD

        @command_handler('listen')
        def listen_handler(bot: Bot, update: Update):
            self.listeners.add(update.message.chat_id)
            bot.send_message(chat_id=update.message.chat_id, text="Listen to errors")
            return LISTENING

        @command_handler('unlisten')
        def unlisten(bot: Bot, update: Update):
            self.listeners.remove(update.message.chat_id)
            bot.send_message(chat_id=update.message.chat_id, text="Stop listening to errors")
            return AUTHORIZED

        @command_handler('debug')
        def debug_handler(bot: Bot, update: Update):
            global main_conversation
            bot.send_message(
                chat_id=update.message.chat_id,
                text=json.dumps(update.__dict__, default=lambda o: repr(o), indent=4, sort_keys=True)
            )
            bot.send_message(
                chat_id=update.message.chat_id,
                text=json.dumps(update.message.__dict__, default=lambda o: repr(o), indent=4, sort_keys=True)
            )

        @command_handler('state')
        def state_handler(bot: Bot, update: Update):
            bot.send_message(chat_id=update.message.chat_id,
                             text=get_state(self.main_conversation, update.effective_chat))

        @regex_handler(r'^/\w+$')
        def unknown_command_handler(bot: Bot, update: Update):
            bot.send_message(chat_id=update.message.chat_id, text="Unknown command {}".format(update.message.text))

        def error(bot: Bot, update: Update, error: Exception):
            logger.warning('Update "%s" caused error "%s"', update, error)

        # ===== END HANDLERS ======

        self.dispatcher.add_error_handler(error)

        global_handlers = [debug_handler, state_handler]

        self.main_conversation = ConversationHandler(
            entry_points=[start_handler],
            states={
                WAIT_PASSWORD: [start_handler, read_password] + global_handlers,
                AUTHORIZED: [logout_handler, listen_handler] + global_handlers,
                LISTENING: [logout_handler, unlisten] + global_handlers
            },
            fallbacks=(unknown_command_handler,),
            per_chat=True
        )

        self.dispatcher.add_handler(self.main_conversation)

    def signal_handler(self, *args, **kwargs):
        self._stopped.set()
        self.save_data()

    @property
    def is_stopped(self):
        return self._stopped.is_set()

    def run(self):
        self.load_data()
        self.updater.start_polling(.1)
        self.redis_listener_thread.start()
        self.data_saver_thread.start()
        self.updater.idle(STOP_SIGNALS)
        self.redis_listener_thread.join()

    def redis_listener(self):
        while not self.is_stopped:
            try:
                r = redis.StrictRedis(**self.config["REDIS"])
                pubsub = r.pubsub(ignore_subscribe_messages=True)
                pubsub.subscribe(self.config["REDIS_CHANNEL"])
                connected = True
            except Exception as e:
                logger.warning(e)
                connected = False
                sleep(1)
            while connected and not self.is_stopped:
                try:
                    message = pubsub.get_message()
                except redis.exceptions.ConnectionError:
                    connected = False

                while message and connected and not self.is_stopped:
                    if message["type"] == "message":
                        data = message["data"].decode('utf-8')
                        for chat_id in self.listeners:
                            self.updater.bot.send_message(chat_id, data, parse_mode=ParseMode.MARKDOWN)

                    try:
                        message = pubsub.get_message()
                    except redis.exceptions.ConnectionError:
                        connected = False

                if not connected:
                    logger.info("Lost Redis connection -> reconnect")
                else:
                    sleep(0.1)

    def load_data(self):
        with self.data_lock:
            logger.debug("Loaing data...")
            try:
                with open(os.path.join(self.config["BACKUP_PATH"], 'conversations'), 'rb') as f:
                    self.main_conversation.conversations = pickle.load(f)
                with open(os.path.join(self.config["BACKUP_PATH"], 'listeners'), 'rb') as f:
                    self.listeners = pickle.load(f)
                with open(os.path.join(self.config["BACKUP_PATH"], 'userdata'), 'rb') as f:
                    self.dispatcher.user_data = pickle.load(f)
            except FileNotFoundError:
                logger.error("Data file not found")
            except:
                logger.error(sys.exc_info()[0])
            else:
                logger.debug("Data loaded")

    def save_data(self):
        with self.data_lock:
            logger.debug("Saving data...")
            resolved = dict()
            for k, v in self.main_conversation.conversations.items():
                if isinstance(v, tuple) and len(v) is 2 and isinstance(v[1], Promise):
                    try:
                        new_state = v[1].result()  # Result of async function
                    except:
                        new_state = v[0]  # In case async function raised an error, fallback to old state
                    resolved[k] = new_state
                else:
                    resolved[k] = v
            try:
                with open(os.path.join(self.config["BACKUP_PATH"], 'conversations'), 'wb+') as f:
                    pickle.dump(resolved, f)
                with open(os.path.join(self.config["BACKUP_PATH"], 'listeners'), 'wb+') as f:
                    pickle.dump(self.listeners, f)
                with open(os.path.join(self.config["BACKUP_PATH"], 'userdata'), 'wb+') as f:
                    pickle.dump(self.dispatcher.user_data, f)
            except Exception as e:
                logger.exception(e)
            else:
                logger.debug("Data saved")

    def data_saver(self):
        while not self._stopped.wait(self.config["AUTOSAVE"]):
            self.save_data()


if __name__ == '__main__':
    import os
    from telegram_logging.utils import get_env

    DEBUG = bool(int(os.environ.get("DEBUG", "0")))

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.DEBUG if DEBUG else logging.WARNING)
    logger = logging.getLogger(__name__)

    CONFIG_PATH = os.environ.get("CONFIG_PATH")
    TOKEN = get_env("TELEGRAM_TOKEN").strip()
    PASSWORD = get_env("TELEGRAM_ACCESS_PASSWORD").strip()

    bot = LoggingBot(CONFIG_PATH, TOKEN, PASSWORD)
    bot.run()
