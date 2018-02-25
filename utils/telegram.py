from telegram import Chat
from telegram.ext import ConversationHandler, CommandHandler, RegexHandler

WAIT_PASSWORD, AUTHORIZED, LISTENING = range(3)


def map_state(st):
    return ["WAIT_PASSWORD", "AUTHORIZED", "LISTENING"][st]


def get_state(conv_handler: ConversationHandler, chat: Chat):
    state = conv_handler.conversations[(chat.id,) * 2]
    return map_state(state)


def command_handler(*args, **kwargs):
    def decorator(fn):
        return CommandHandler(*args, callback=fn, **kwargs)

    return decorator


def regex_handler(*args, **kwargs):
    def decorator(fn):
        return RegexHandler(*args, callback=fn, **kwargs)

    return decorator
