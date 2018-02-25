import json
import logging

from telegram import Bot, Update
from telegram.ext import CommandHandler, MessageHandler, Filters

from utils import *

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def start(bot: Bot, update: Update):
    bot.send_message(chat_id=update.message.chat_id, text="I'm a bot, please talk to me!")
    return GUEST


def debug(bot: Bot, update: Update):
    global main_conversation
    bot.send_message(
        chat_id=update.message.chat_id,
        text=json.dumps(update.__dict__, default=lambda o: repr(o), indent=4, sort_keys=True)
    )
    return GUEST


def echo(bot: Bot, update: Update):
    bot.send_message(chat_id=update.message.chat_id, text=update.message.text.replace("/", "\\"))


def state(bot: Bot, update: Update):
    global main_conversation
    bot.send_message(chat_id=update.message.chat_id, text=get_state(main_conversation, update.effective_chat))


start_handler = CommandHandler('start', start)
debug_handler = CommandHandler('debug', debug)
state_handler = CommandHandler('state', state)
echo_handler = MessageHandler(Filters.text, echo),

main_conversation = ConversationHandler(
    entry_points=[start_handler],
    states={
        GUEST: [debug_handler, state_handler],
        AUTHORIZED: (),
        LISTENING: ()
    },
    fallbacks=(echo_handler,),
    per_chat=True
)
