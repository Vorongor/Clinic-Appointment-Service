import os

import telebot
from django.conf import settings


def send_telegram_message(text: str):
    bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
    bot.send_message(os.getenv("TELEGRAM_CHAT_ID"))
