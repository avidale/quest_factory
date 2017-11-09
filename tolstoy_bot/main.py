# -*- coding: utf-8 -*-
import config
import telebot
# pip install pyTelegramBotAPI

bot = telebot.TeleBot(config.token)

dialogues = dict()

from dialogue_manager import StupidLinearDialogue

import pandas as pd

script = pd.read_excel('botanik.xlsx', sheetname='script')
script = script[script.notnull().max(axis=1)].reset_index(drop=True)
script.columns = ['action', 'reaction']

import re
import os
import time

STATIC_DIR = 'static'

def strip_content(text, tag='image'):
    """ Extract patterns like [image|tolstoy.jpg] from text """
    pat = r'\[' + tag + r'\|(.*)\]'
    new_text = re.sub(pat, '', text)
    images = [t for t in re.findall(pat, text)]
    return new_text, images
			
@bot.message_handler(commands=['start'])
def greeting1(message):
    dialogues[message.chat.id] = StupidLinearDialogue(script)
    thematic_response(message)
    
@bot.message_handler(commands=['reset'])
def greeting2(message):
    bot.send_message(message.chat.id, "Делаю ресет...")
    greeting1(message)
		
@bot.message_handler(content_types=["text"])
def thematic_response(message):
    if message.chat.id not in dialogues:
        greeting1(message)
        return
    
    responce = dialogues[message.chat.id].next(message)
    responce_text, responce_images = strip_content(responce, 'image')
    responce_text, responce_audios = strip_content(responce_text, 'audio')
    
    if len(responce_text) > 0:
        bot.send_message(message.chat.id, responce_text)
    for filename in responce_images:
        try:
            with open(os.path.join(STATIC_DIR, filename), 'rb') as file:
                bot.send_photo(message.chat.id, file)
        except FileNotFoundError:
            bot.send_message(message.chat.id, "(Тут должно быть фото {})".format(filename))
    for filename in responce_audios:
        try:
            with open(os.path.join(STATIC_DIR, filename), 'rb') as file:
                bot.send_audio(message.chat.id, file)
        except FileNotFoundError:
            bot.send_message(message.chat.id, "(Тут должно быть аудио {})".format(filename))
    pause = dialogues[message.chat.id].check_pause()
    if pause is not None:
        # todo: set timer for exactly this user, and go on proactively after pause
        pass


@bot.message_handler(commands=['reset'])
def give_help(message):
    bot.send_message(message.chat.id, """ Команды /start и /reset обе переводят тебя в начало диалога. """)

while True:
    try:
        bot.polling(none_stop=True)
    # ConnectionError and ReadTimeout because of possible timout of the requests library
    # TypeError for moviepy errors
    # maybe there are others, therefore Exception
    except Exception as e:
        print(time.ctime())
        print(e)
        time.sleep(15)

# todo: pickle bot state and try to recreate everything on restart.
# todo: 
