import os

import telebot
from django.conf import settings


def send_telegram_message(text: str):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    bot = telebot.TeleBot(token)
    bot.send_message(chat_id, text)
