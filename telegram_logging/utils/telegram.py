from telegram.ext import CommandHandler, RegexHandler


def command_handler(*args, **kwargs):
    def decorator(fn):
        return CommandHandler(*args, callback=fn, **kwargs)

    return decorator


def regex_handler(*args, **kwargs):
    def decorator(fn):
        return RegexHandler(*args, callback=fn, **kwargs)

    return decorator
