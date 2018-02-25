from telegram import Chat
from telegram.ext import ConversationHandler

GUEST, AUTHORIZED, LISTENING = range(3)


def map_state(st):
    return ["GUEST", "AUTHORIZED", "LISTENING"][st]


def get_state(conv_handler: ConversationHandler, chat: Chat):
    state = conv_handler.conversations[(chat.id,) * 2]
    return map_state(state)
