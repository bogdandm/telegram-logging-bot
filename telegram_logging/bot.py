import json
import logging
import threading
from signal import SIGABRT, SIGTERM, SIGINT
from time import sleep
from typing import Callable, Tuple, Optional, List

import redis.exceptions
from telegram import Bot, Update, Chat, ParseMode
from telegram.ext import Updater, ConversationHandler

from telegram_logging.utils.telegram import command_handler, regex_handler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

TELEGRAM_MSG_MAX_LEN = 4096 - 10
WAIT_PASSWORD, AUTHORIZED, LISTENING = range(3)


def map_state(st):
    return ["WAIT_PASSWORD", "AUTHORIZED", "LISTENING"][st]


"""
START -> WAIT_PASSWORD -> AUTHORIZED <-> LISTENING
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

        self.updater = Updater(token, user_sig_handler=self.signal_handler)
        self.dispatcher = self.updater.dispatcher
        self.listeners_4xx = set()  # Set[chat_id]
        self.listeners_5xx = set()  # Set[chat_id]

        # ===== HANDLERS ======

        @command_handler('start')
        def start_handler(bot: Bot, update: Update):
            bot.send_message(chat_id=update.message.chat_id, text="Please type access password:")
            return WAIT_PASSWORD

        @regex_handler(r"^\w+$")
        def read_password(bot: Bot, update: Update):
            if update.message.text.strip() == self.password:
                bot.send_message(chat_id=update.message.chat_id, text="Valid password!")
                return AUTHORIZED
            else:
                bot.send_message(chat_id=update.message.chat_id, text="Invalid password :(")

        @command_handler('listen_all')
        def listen_all_handler(bot: Bot, update: Update):
            self.listeners_4xx.add(update.message.chat_id)
            self.listeners_5xx.add(update.message.chat_id)
            bot.send_message(chat_id=update.message.chat_id, text="Listen to 4xx and 5xx errors")
            return LISTENING

        @command_handler('listen_400')
        def listen_400(bot: Bot, update: Update):
            self.listeners_4xx.add(update.message.chat_id)
            bot.send_message(chat_id=update.message.chat_id, text="Listen to 4xx errors")
            return LISTENING

        @command_handler('listen_500')
        def listen_500(bot: Bot, update: Update):
            self.listeners_5xx.add(update.message.chat_id)
            bot.send_message(chat_id=update.message.chat_id, text="Listen to 5xx errors")
            return LISTENING

        @command_handler('unlisten')
        def unlisten(bot: Bot, update: Update):
            self.listeners_4xx.remove(update.message.chat_id)
            self.listeners_5xx.remove(update.message.chat_id)
            bot.send_message(chat_id=update.message.chat_id, text="Stop listen to errors")
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
                WAIT_PASSWORD: [read_password] + global_handlers,
                AUTHORIZED: [listen_all_handler, listen_400, listen_500] + global_handlers,
                LISTENING: [unlisten] + global_handlers
            },
            fallbacks=(unknown_command_handler,),
            per_chat=True
        )

        self.dispatcher.add_handler(self.main_conversation)

    def signal_handler(self, *args, **kwargs):
        print("SIG")
        self._stopped.set()

    @property
    def is_stopped(self):
        return self._stopped.is_set()

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
                sleep(0.1)
            while connected and not self.is_stopped:
                try:
                    message = pubsub.get_message()
                except redis.exceptions.ConnectionError:
                    connected = False

                while message and connected:
                    if message["type"] == "message":
                        lines = message["data"].decode('utf-8').split("\n") # type: List[str]
                        out_lines = []
                        _flag = False
                        for line in map(str.strip, lines):
                            if _flag:
                                line = ">>> " + line
                            if line.startswith("File"):
                                out_lines.append(" ")
                                _flag = True
                            else:
                                _flag = False
                            out_lines.append(line)

                        data = "```{}```".format("\n".join(out_lines))
                        for chat_id in self.listeners_5xx:
                            self.updater.bot.send_message(chat_id, data, parse_mode=ParseMode.MARKDOWN)

                    try:
                        message = pubsub.get_message()
                    except redis.exceptions.ConnectionError:
                        connected = False

                if not connected:
                    logger.info("Lost Redis connection -> reconnect")
                else:
                    sleep(0.1)

    def run(self):
        self.updater.start_polling(.1)
        self.redis_listener_thread.start()
        self.updater.idle(STOP_SIGNALS)
        self.redis_listener_thread.join()


if __name__ == '__main__':
    import os
    from telegram_logging.utils import get_env

    CONFIG_PATH = os.environ.get("CONFIG_PATH")
    TOKEN = get_env("TELEGRAM_TOKEN")
    PASSWORD = get_env("TELEGRAM_ACCESS_PASSWORD")

    bot = LoggingBot(CONFIG_PATH, TOKEN, PASSWORD)
    bot.run()
