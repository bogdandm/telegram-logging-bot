import json
import logging

from telegram import Bot, Update

from utils import get_env
from utils.telegram import *

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

PASSWORD = get_env('TELEGRAM_ACCESS_PASSWORD')


@command_handler('start')
def start_handler(bot: Bot, update: Update):
    bot.send_message(chat_id=update.message.chat_id, text="Please type access password:")
    return WAIT_PASSWORD


@regex_handler(r"^\w+$")
def read_password(bot: Bot, update: Update):
    if update.message.text.strip() == PASSWORD:
        bot.send_message(chat_id=update.message.chat_id, text="Valid password!")
        return AUTHORIZED
    else:
        bot.send_message(chat_id=update.message.chat_id, text="Invalid password :(")


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
    return PASSWORD


@command_handler('state')
def state_handler(bot: Bot, update: Update):
    global main_conversation
    bot.send_message(chat_id=update.message.chat_id, text=get_state(main_conversation, update.effective_chat))


all_states = [debug_handler, state_handler]

main_conversation = ConversationHandler(
    entry_points=[start_handler],
    states={
        WAIT_PASSWORD: [read_password] + all_states,
        AUTHORIZED: [] + all_states,
        LISTENING: [] + all_states
    },
    fallbacks=(),
    per_chat=True
)
