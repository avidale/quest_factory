# -*- coding: utf-8 -*-
"""
This is the main executable file of the Tolstoy Telegram bot
"""
import config
import telebot  # need to pip install pyTelegramBotAPI
from dialogue_manager import StupidLinearDialogue  # the main logic here!
import threading
import time

import pandas as pd
import re
import os
import time
import logging  # todo: log with timestamps
import pickle

STATIC_DIR = 'static'

logging.basicConfig(level=logging.INFO, filename=config.LOG_FILENAME)

# todo: move all the meaningful work into functions

bot = telebot.TeleBot(config.TOKEN)

dialogues = dict()

# read the dialogue script from Excel
script = pd.read_excel(config.SCRIPT_FILENAME, sheetname='script')
script = script[script.notnull().max(axis=1)].reset_index(drop=True)


def dump_dialogues(filename):
    """ Write position of each dialogue to a file """
    positions = dict()
    for key, dial_object in dialogues.items():
        positions[key] = dial_object.position
    with open(filename, 'wb') as f:
        pickle.dump(positions, f)


def load_dialogues(filename):
    """ Restore position of each dialogue from a file, if it is here """
    if os.path.isfile(filename):
        with open(filename, 'rb') as f:
            positions = pickle.load(f)
            for key, position in positions.items():
                if key not in dialogues:
                    # todo: make dialogue-creation a function
                    dialogues[key] = StupidLinearDialogue(script)
                    dialogues[key].position = position

# read the dialogues right now!
load_dialogues(config.STATE_FILENAME)


def strip_content(text, tag='image'):
    """ Extract patterns like [image|tolstoy.jpg] from text """
    pat = r'\[' + tag + r'\|(.*)\]'
    new_text = re.sub(pat, '', text)
    images = [t for t in re.findall(pat, text)]
    return new_text, images


@bot.message_handler(commands=['start'])
def greeting1(message):
    """ Initiate a new dialogue for this particular user."""
    dialogues[message.chat.id] = StupidLinearDialogue(script)
    thematic_response(message)


@bot.message_handler(commands=['reset'])
def greeting2(message):
    """ Hard restart the dialogue for this user. """
    bot.send_message(message.chat.id, "Делаю ресет...")
    greeting1(message)


@bot.message_handler(content_types=["text"])
def thematic_response(message):
    """ This function gives user messages to dialogue manager
    and sends back to the user its response.
    """
    # todo: log input types other than text
    # todo: separate input processing from response processing
    logging.info('IN:' + str(message.chat.id) + ':'
                 + message.text.replace('\n', ' <newline> '))
    if message.chat.id not in dialogues:
        greeting1(message)
        return
    
    response = dialogues[message.chat.id].react(message)
    response_text, response_images = strip_content(response, 'image')
    response_text, response_audios = strip_content(response_text, 'audio')
    
    if len(response_text) > 0:
        bot.send_message(message.chat.id, response_text)
        logging.info('OUT:' + str(message.chat.id) + ':'
                     + response_text.replace('\n', ' <newline> '))
    for filename in response_images:
        try:
            with open(os.path.join(STATIC_DIR, filename), 'rb') as file:
                bot.send_photo(message.chat.id, file)
        except FileNotFoundError:
            bot.send_message(message.chat.id, "(Тут должно быть фото {})".format(filename))
        logging.info('OUT:' + str(message.chat.id) + ':' + filename)
    for filename in response_audios:
        try:
            with open(os.path.join(STATIC_DIR, filename), 'rb') as file:
                bot.send_audio(message.chat.id, file)
        except FileNotFoundError:
            bot.send_message(message.chat.id, "(Тут должно быть аудио {})".format(filename))
        logging.info('OUT:' + str(message.chat.id) + ':' + filename)


@bot.message_handler(commands=['reset'])
def give_help(message):
    bot.send_message(message.chat.id, "Команды /start и /reset "
                     + "обе переводят тебя в начало диалога.")


class Object:
    """ Just an empty object to use anywhere """
    pass


class DummyMessage:
    """ A dummy message that comes after a pause """
    def __init__(self, chat_id, text='A_DUMMY_MESSAGE'):
        self.chat = Object()
        self.chat.id = chat_id
        self.text = text


def proactive():
    """ Proactively send something to all the users, if needed.
        This function may be called with small time interval.
    """
    for chat_id, dialog in dialogues.items():
        if dialog.needs_proactive():
            dummy = DummyMessage(chat_id)
            thematic_response(dummy)
    # save state of each dialogue to a file
    dump_dialogues(config.STATE_FILENAME)


def start_proactive(pause=10):
    while True:
        # logging.info('WAKE_UP')
        try:
            proactive()
        except Exception as ex:
            print('thread exception')
            print(ex)
        time.sleep(pause)

# start proactive checking
proactive_thread = threading.Thread(target=start_proactive, daemon=True,
                                    args=(5,))
proactive_thread.start()


restart = True

if not restart:
    bot.polling(none_stop=False)

while restart:
    try:
        bot.polling(none_stop=True)
    # ConnectionError and ReadTimeout arise
    # because of possible timout of the requests library
    # TypeError for moviepy errors
    # maybe there are others, therefore Exception
    # todo: for some errors, do NOT break!
    # todo: correctly manage keyboard stopping
    # requests.exceptions.ReadTimeout: HTTPSConnectionPool(
    # host='api.telegram.org', port=443): Read timed out. (read timeout=30)
    # можно просто ждать telebot.apihelper.ApiException: A request to the Telegram
    # API was unsuccessful. The server returned HTTP 429 Too Many Requests.
    # Response body: [b'{"ok":false,"error_code":429,"description":
    # "Too Many Requests: retry after 75","parameters":{"retry_after":75}}']
    # telebot.apihelper.ApiException: A request to the Telegram API was
    # unsuccessful. The server returned HTTP 409 Conflict. Response body:
    # [b'{"ok":false,"error_code":409,"description":
    # "Conflict: terminated by other long poll or webhook"}']


    except KeyboardInterrupt:
        logging.info("Keyboard interrupt")
        restart = False
        bot.stop_polling()
    except Exception as e:
        print(time.ctime())
        print(e)
        bot.stop_polling()
        #restart = False
        #break
        time.sleep(15)
