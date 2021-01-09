# coding: utf-8
# YYeTsBot - bot.py
# 2019/8/15 18:27

__author__ = 'Benny <benny.think@gmail.com>'

import io
import time
import re
import os
import logging

from urllib.parse import quote_plus

import telebot
from telebot import types, apihelper
from tgbot_ping import get_runtime

from html_request import get_search_html, analyse_search_html, get_detail_page
from utils import save_dump, upsert, get
from config import PROXY, TOKEN, SEARCH_URL, MAINTAINER

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(filename)s [%(levelname)s]: %(message)s')
if PROXY:
    apihelper.proxy = {'https': PROXY}

bot = telebot.TeleBot(os.environ.get('TOKEN') or TOKEN)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_chat_action(message.chat.id, 'typing')
    bot.send_message(message.chat.id, '欢迎使用，发送想要的剧集标题，我会帮你搜索。'
                                      '建议使用<a href="http://www.zmz2019.com/">人人影视</a> 标准译名',
                     parse_mode='html')


@bot.message_handler(commands=['help'])
def send_help(message):
    bot.send_chat_action(message.chat.id, 'typing')
    bot.send_message(message.chat.id, '''机器人无法使用或者报错？你可以使用如下方式寻求使用帮助和报告错误：\n
    1. @BennyThink
    2. <a href='https://github.com/BennyThink/YYeTsBot/issues'>Github issues</a>
    3. <a href='https://t.me/mikuri520'>Telegram Channel</a>''', parse_mode='html', disable_web_page_preview=True)


@bot.message_handler(commands=['ping'])
def send_ping(message):
    bot.send_chat_action(message.chat.id, 'typing')
    info = get_runtime("botsrunner_yyets_1")
    bot.send_message(message.chat.id, info, parse_mode='markdown')


@bot.message_handler(commands=['credits'])
def send_credits(message):
    bot.send_chat_action(message.chat.id, 'typing')
    bot.send_message(message.chat.id, '''感谢字幕组的无私奉献！本机器人资源来源:\n
    <a href="http://www.zmz2019.com/">人人影视</a>
    <a href="http://oabt005.com/home.html">磁力下载站</a>
    <a href="http://www.zhuixinfan.com/main.php">追新番</a>
    ''', parse_mode='html')


def download_to_io(photo):
    logging.info("Initializing bytes io...")
    mem = io.BytesIO()
    file_id = photo[-1].file_id
    logging.info("Downloading photos...")
    file_info = bot.get_file(file_id)
    content = bot.download_file(file_info.file_path)
    mem.write(content)
    logging.info("Downloading complete.")
    return mem


def send_my_response(message):
    bot.send_chat_action(message.chat.id, 'record_video_note')
    # I may also send picture
    photo = message.photo
    uid = message.reply_to_message.caption
    text = f"主人说：{message.text or message.caption or '啥也没说😯'}"
    if photo:
        bot.send_chat_action(message.chat.id, 'typing')
        logging.info("Photo received from maintainer")
        mem = download_to_io(photo)
        mem.name = f'{uid}.jpg'
        bot.send_photo(uid, mem.getvalue(), caption=text)
    else:
        bot.send_message(uid, text)

    bot.reply_to(message, "回复已经发送给这位用户")


@bot.message_handler(content_types=["photo", "text"])
def send_search(message):
    if message.reply_to_message and \
            message.reply_to_message.document.file_name == 'error.txt' and str(message.chat.id) == MAINTAINER:
        send_my_response(message)
        return
    bot.send_chat_action(message.chat.id, 'record_video')

    name = message.text
    if name is None:
        with open('assets/warning.webp', 'rb') as sti:
            bot.send_message(message.chat.id, "不要调戏我！我会报警的")
            bot.send_sticker(message.chat.id, sti)
        return

    logging.info('Receiving message about %s from user %s(%s)', name, message.chat.username,
                 message.chat.id)
    html = get_search_html(name)
    result = analyse_search_html(html)

    markup = types.InlineKeyboardMarkup()
    for url, detail in result.items():
        btn = types.InlineKeyboardButton(detail['name'], callback_data=url)
        markup.add(btn)

    if result:
        bot.send_message(message.chat.id, "呐，💐🌷🌹选一个呀！", reply_markup=markup)
    else:
        bot.send_chat_action(message.chat.id, 'typing')

        encoded = quote_plus(name)
        bot.send_message(message.chat.id, f"没有找到你想要的信息🤪\n莫非你是想调戏我哦😏\n\n"
                                          f"你先看看这个链接有没有结果。 {SEARCH_URL.format(kw=encoded)} "
                                          "如果有的话，那报错给我吧", reply_markup=markup, disable_web_page_preview=True)
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton("快来修复啦", callback_data="fix")
        markup.add(btn)
        bot.send_chat_action(message.chat.id, 'upload_document')
        bot.send_message(message.chat.id, f"《{name}》😭😭😭\n机器人不好用了？点下面的按钮叫 @BennyThink 来修！",
                         reply_markup=markup)
        content = f""" 报告者：@{message.chat.username}({message.chat.id})
                        问题发生时间：{time.strftime("%Y-%m-%data %H:%M:%S", time.localtime(message.date))}
                        请求内容：{name} 
                        请求URL：{SEARCH_URL.format(kw=encoded)}\n\n
                        返回内容：{html}
                    """
        save_dump(content)


@bot.callback_query_handler(func=lambda call: 'resource' in call.data)
def choose_link(call):
    bot.send_chat_action(call.message.chat.id, 'typing')
    resource_url = call.data
    link = get_detail_page(resource_url)
    upsert(call.id, link)
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("分享页面", callback_data="share%s" % call.id)
    btn2 = types.InlineKeyboardButton("继续点按钮", callback_data="select%s" % call.id)
    markup.add(btn1, btn2)
    bot.send_message(call.message.chat.id, "想要分享页面，还是继续点击按钮", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: re.findall(r"share(\d*)", call.data))
def share_page(call):
    bot.send_chat_action(call.message.chat.id, 'typing')
    cid = re.findall(r"share(\d*)", call.data)[0]
    result = get(cid)
    bot.send_message(call.message.chat.id, result['share'])


@bot.callback_query_handler(func=lambda call: re.findall(r"select(\d*)", call.data))
def select_episode(call):
    bot.send_chat_action(call.message.chat.id, 'typing')
    cid = re.findall(r"select(\d*)", call.data)[0]
    result = get(cid)
    markup = types.InlineKeyboardMarkup()

    if not result['rss']:
        btn = types.InlineKeyboardButton("点击打开分享网站", url=result['share'])
        markup.add(btn)
        bot.send_message(call.message.chat.id, "哎呀呀，这是个电影，恐怕没得选吧！", reply_markup=markup)
    else:
        for guid, detail in result['rss'].items():
            btn = types.InlineKeyboardButton(detail['title'], callback_data=f"cid{cid}guid{guid}")
            markup.add(btn)
        bot.send_message(call.message.chat.id, "选一集吧！", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: re.findall(r"cid(\d*)guid(.*)", call.data))
def send_link(call):
    bot.send_chat_action(call.message.chat.id, 'typing')
    data = re.findall(r"cid(\d*)guid(.*)", call.data)[0]
    cid, guid = data[0], data[1]
    links = get(cid)['rss'][guid]
    ed2k, magnet, pan = "`{}`".format(links['ed2k']), "`{}`".format(links['magnet']), "`{}`".format(links['pan'])
    bot.send_message(call.message.chat.id, f"{links['title']}的下载资源如下")
    if ed2k != "``":
        bot.send_message(call.message.chat.id, ed2k, parse_mode='markdown')
    if magnet != "``":
        bot.send_message(call.message.chat.id, magnet, parse_mode='markdown')
    if pan != "``":
        bot.send_message(call.message.chat.id, pan, parse_mode='markdown')


@bot.callback_query_handler(func=lambda call: call.data == 'fix')
def report_error(call):
    logging.error("Reporting error to maintainer.")
    bot.send_chat_action(call.message.chat.id, 'typing')
    bot.send_message(MAINTAINER, '人人影视机器人似乎出现了一些问题🤔🤔🤔……')
    debug = open(os.path.join(os.path.dirname(__file__), 'data', 'error.txt'), 'r', encoding='u8')
    bot.send_document(MAINTAINER, debug, caption=str(call.message.chat.id))
    bot.answer_callback_query(call.id, 'Debug信息已经发送给维护者，请耐心等待修复~', show_alert=True)
    # bot.edit_message_text("好了，信息发过去了，坐等回复吧！", call.message.chat.id, call.message.message_id)


if __name__ == '__main__':
    logging.info('YYeTs bot is running...')
    bot.polling(none_stop=True, )
