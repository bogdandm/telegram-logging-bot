import logging

from telegram import Bot, Update
from telegram.ext import Updater

from handlers import main_conversation

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def error(bot: Bot, update: Update, error: Exception):
    logger.warning('Update "%s" caused error "%s"', update, error)


#
# def loadData():
#     try:
#         f = open('backup/conversations', 'rb')
#         conv_handler.conversations = pickle.load(f)
#         f.close()
#         f = open('backup/userdata', 'rb')
#         dp.user_data = pickle.load(f)
#         f.close()
#     except FileNotFoundError:
#         utils.logging.error("Data file not found")
#     except:
#         utils.logging.error(sys.exc_info()[0])
#
# def saveData():
#     while True:
#         time.sleep(60)
#         # Before pickling
#         resolved = dict()
#         for k, v in conv_handler.conversations.items():
#             if isinstance(v, tuple) and len(v) is 2 and isinstance(v[1], Promise):
#                 try:
#                     new_state = v[1].result()  # Result of async function
#                 except:
#                     new_state = v[0]  # In case async function raised an error, fallback to old state
#                 resolved[k] = new_state
#             else:
#                 resolved[k] = v
#         try:
#             f = open('backup/conversations', 'wb+')
#             pickle.dump(resolved, f)
#             f.close()
#             f = open('backup/userdata', 'wb+')
#             pickle.dump(dp.user_data, f)
#             f.close()
#         except:
#             logging.error(sys.exc_info()[0])


def main(token: str):
    updater = Updater(token)
    dispatcher = updater.dispatcher
    dispatcher.add_error_handler(error)

    dispatcher.add_handler(main_conversation)

    updater.start_polling(.1)


if __name__ == '__main__':
    from utils import get_env

    TOKEN = get_env("TELEGRAM_TOKEN")
    main(TOKEN)
