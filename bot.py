# coding: utf-8
# YYeTsBot - bot.py
# 2019/8/15 18:27

__author__ = 'Benny <benny.think@gmail.com>'

import os
import time
import logging

import telebot
from telebot import types
from config import TOKEN, MAINTAINER
from html_parser import parser
from html_request import get_html
from utils import bunch_upsert, get, save_dump

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(filename)s [%(levelname)s]: %(message)s')
# from telebot import apihelper

# apihelper.proxy = {'socks5': 'socks5://127.0.0.1:1080'}

bot = telebot.TeleBot(os.environ.get('TOKEN') or TOKEN)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_chat_action(message.chat.id, 'typing')
    bot.send_message(message.chat.id, '欢迎使用，发送想要的剧集标题，我会帮你搜索。'
                                      '建议使用<a href="http://www.zmz2019.com/">人人影视</a>标准译名',
                     parse_mode='html')


@bot.message_handler(commands=['help'])
def send_help(message):
    bot.send_chat_action(message.chat.id, 'typing')
    bot.send_message(message.chat.id, '''机器人无法使用或者报错？
    @BennyThink 或者<a href='https://github.com/BennyThink/YYeTsBot/issues'>Github issues</a>''',
                     parse_mode='html')


@bot.message_handler(commands=['credits'])
def send_credits(message):
    bot.send_chat_action(message.chat.id, 'typing')
    bot.send_message(message.chat.id, '''感谢字幕组的无私奉献！本机器人资源来源:\n
    <a href="http://www.zmz2019.com/">人人影视</a>
    <a href="http://oabt005.com/home.html">磁力下载站</a>
    <a href="http://www.zhuixinfan.com/main.php ">追新番</a>
    <a href="http://www.zimuxia.cn/">FIX字幕侠</a>
    ''', parse_mode='html')


@bot.message_handler()
def send_link(message):
    bot.send_chat_action(message.chat.id, 'record_video')
    name = message.text
    logging.info('Receiving message about %s from user %s(%s)' % (name, message.chat.username,
                                                                  message.chat.id))
    # get html content
    contents, req_url, req_text = get_html(name)
    # contents, req_url, req_text = [],'url','html'
    # get download link
    bot.send_chat_action(message.chat.id, 'upload_video')
    list_r, dict_r = [], {}
    for content in contents:
        r1, r2 = parser(content)
        list_r.extend(r1)
        dict_r = dict(dict_r, **r2)
    if not dict_r:
        markup = types.InlineKeyboardMarkup()
        bot.send_chat_action(message.chat.id, 'find_location')
        bot.send_message(message.chat.id, "没有找到你想要的信息🤪\n莫非你是想调戏我哦😏")
        bot.send_chat_action(message.chat.id, 'typing')

        btn = types.InlineKeyboardButton("快来修复啦", callback_data="fix")
        markup.add(btn)
        bot.send_chat_action(message.chat.id, 'upload_document')
        bot.send_message(message.chat.id, f"《{name}》😭😭😭\n机器人不好用了？点下面的按钮叫 @BennyThink 来修！",
                         reply_markup=markup)
        e = f""" 报告者：@{message.chat.username}({message.chat.id})
                问题发生时间：{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(message.date))}
                请求内容：{name} 
                请求URL：{req_url}\n\n
                返回内容：{req_text}
            """
        save_dump(e)
        return

    # saved dict_r
    bunch_upsert(dict_r)
    size = 20
    for i in range(0, len(list_r), size):
        logging.info("I'm sending you links now😉")
        markup = types.InlineKeyboardMarkup()
        part = list_r[i:i + 20]
        for item in part:
            btn = types.InlineKeyboardButton(item['name'], callback_data=item['id'])
            markup.add(btn)

        bot.send_chat_action(message.chat.id, 'upload_document')
        bot.send_message(message.chat.id, "点击按钮获取下载链接", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data != 'fix')
def movie_handle(call):
    bot.send_chat_action(call.message.chat.id, 'typing')
    dict_r = get(call.data)
    if not dict_r:
        bot.send_message(call.message.chat.id, '我失忆惹，请在聊天框内重新发送你想要的影视名称')
    bot.answer_callback_query(call.id, '文件大小为%s' % dict_r['size'])
    bot.send_message(call.message.chat.id, dict_r['ed2k'] if dict_r['ed2k'] else '哎呀，没有ed2k链接')
    bot.send_message(call.message.chat.id, dict_r['magnet'] if dict_r['magnet'] else '哎呀，没有magnet链接')


@bot.callback_query_handler(func=lambda call: call.data == 'fix')
def report_error(call):
    bot.send_chat_action(call.message.chat.id, 'typing')
    bot.send_message(MAINTAINER, '人人影视机器人似乎出现了一些问题🤔🤔🤔……')
    debug = open(os.path.join(os.path.dirname(__file__), 'data', 'error.txt'), 'r', encoding='u8')
    bot.send_document(MAINTAINER, debug)


if __name__ == '__main__':
    logging.info('YYeTs bot is running...')
    bot.polling()
