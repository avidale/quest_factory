# -*- coding: utf-8 -*-
"""
This is the main executable file of the Tolstoy Telegram bot
"""
import config
import telebot  # need to pip install pyTelegramBotAPI
from dialogue_manager import StupidLinearDialogue  # the main logic here!
import pandas as pd
import re
import os
import time
import logging

STATIC_DIR = 'static'

logging.basicConfig(level=logging.INFO, filename=config.LOG_FILENAME)

bot = telebot.TeleBot(config.TOKEN)

dialogues = dict()

# read the dialogue script from Excel
script = pd.read_excel(config.SCRIPT_FILENAME, sheetname='script')
script = script[script.notnull().max(axis=1)].reset_index(drop=True)


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
    logging.info('IN:' + str(message.chat.id) + ':'
                 + message.text.replace('\n', ' <newline> '))
    if message.chat.id not in dialogues:
        greeting1(message)
        return
    
    response = dialogues[message.chat.id].next(message)
    responce_text, responce_images = strip_content(response, 'image')
    responce_text, responce_audios = strip_content(responce_text, 'audio')
    
    if len(responce_text) > 0:
        bot.send_message(message.chat.id, responce_text)
        logging.info('OUT:' + str(message.chat.id) + ':'
                     + responce_text.replace('\n', ' <newline> '))
    for filename in responce_images:
        try:
            with open(os.path.join(STATIC_DIR, filename), 'rb') as file:
                bot.send_photo(message.chat.id, file)
        except FileNotFoundError:
            bot.send_message(message.chat.id, "(Тут должно быть фото {})".format(filename))
        logging.info('OUT:' + str(message.chat.id) + ':' + filename)
    for filename in responce_audios:
        try:
            with open(os.path.join(STATIC_DIR, filename), 'rb') as file:
                bot.send_audio(message.chat.id, file)
        except FileNotFoundError:
            bot.send_message(message.chat.id, "(Тут должно быть аудио {})".format(filename))
        logging.info('OUT:' + str(message.chat.id) + ':' + filename)
    pause = dialogues[message.chat.id].check_pause()
    if pause is not None:
        # todo: set timer for exactly this user, and go on proactively after pause
        pass


@bot.message_handler(commands=['reset'])
def give_help(message):
    bot.send_message(message.chat.id, "Команды /start и /reset обе переводят тебя в начало диалога.")


while True:
    try:
        bot.polling(none_stop=True)
    # ConnectionError and ReadTimeout arise
    # because of possible timout of the requests library
    # TypeError for moviepy errors
    # maybe there are others, therefore Exception
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt")
        break
    except Exception as e:
        print(time.ctime())
        print(e)
        time.sleep(15)

# todo: pickle bot state and try to recreate everything on restart.
# todo: 
