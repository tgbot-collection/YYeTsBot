# coding: utf-8
# YYeTsBot - messenger.py
# 2019/11/6 12:42

__author__ = 'Benny <benny.think@gmail.com>'

from config import TOKEN
import telebot
import sys

bot = telebot.TeleBot(TOKEN)


def send_msg(argv):
    uid = argv[1]
    msg = argv[2]
    bot.send_chat_action(uid, 'typing')
    bot.send_message(uid, msg, parse_mode='html')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Need ID and message!")
        sys.exit(2)

    send_msg(sys.argv)
