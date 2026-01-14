import telebot
from django.conf import settings


def send_telegram_message(text: str):
    bot = telebot.TeleBot(settings.TELEGRAM_BOT_TOKEN)
    bot.send_message(settings.TELEGRAM_CHAT_ID, text)
