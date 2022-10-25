# coding: utf-8
# YYeTsBot - bot.py
# 2019/8/15 18:27

__author__ = 'Benny <benny.think@gmail.com>'

import io
import json
import logging
import os
import re
import tempfile
import time
from urllib.parse import quote_plus

import requests
import telebot
import zhconv
from apscheduler.schedulers.background import BackgroundScheduler
from telebot import apihelper, types
from tgbot_ping import get_runtime

import fansub
from config import (DOMAIN, FANSUB_ORDER, MAINTAINER, PROXY, REPORT, TOKEN,
                    YYETS_SEARCH_URL)
from utils import (get_error_dump, redis_announcement, reset_request,
                   save_error_dump, show_usage, today_request)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(filename)s [%(levelname)s]: %(message)s')
if PROXY:
    apihelper.proxy = {'https': PROXY}

bot = telebot.TeleBot(TOKEN, num_threads=100)
angry_count = 0


@bot.message_handler(commands=['start'], chat_types=['private'])
def send_welcome(message):
    bot.send_chat_action(message.chat.id, 'typing')
    bot.send_message(message.chat.id, '欢迎使用，直接发送想要的剧集标题给我就可以了，不需要其他关键字，我会帮你搜索。\n\n'
                                      '仅私聊使用，群组功能已禁用。'
                                      f'目前搜索优先级 {FANSUB_ORDER}\n '
                                      f'另外，可以尝试使用一下 https://yyets.dmesg.app/ 哦！',
                     parse_mode='html', disable_web_page_preview=True)


@bot.message_handler(commands=['help'], chat_types=['private'])
def send_help(message):
    bot.send_chat_action(message.chat.id, 'typing')
    bot.send_message(message.chat.id, '''机器人无法使用或者报错？从 /ping 里可以看到运行状态以及最新信息。
    同时，你可以使用如下方式寻求使用帮助和报告错误：\n
    1. @BennyThink
    2. <a href='https://github.com/BennyThink/YYeTsBot/issues'>Github issues</a>
    3. <a href='https://t.me/mikuri520'>Telegram Channel</a>''', parse_mode='html', disable_web_page_preview=True)


@bot.message_handler(commands=['ping'], chat_types=['private'])
def send_ping(message):
    logging.info("Pong!")
    bot.send_chat_action(message.chat.id, 'typing')

    info = get_runtime("botsrunner_yyets_1")

    usage = ""
    if str(message.chat.id) == MAINTAINER:
        usage = show_usage()
    announcement = redis_announcement() or ""
    if announcement:
        announcement = f"\n\n*公告：{announcement}*\n\n"
    bot.send_message(message.chat.id, f"{info}\n\n{usage}\n{announcement}",
                     parse_mode='markdown')


@bot.message_handler(commands=['settings'], chat_types=['private'])
def settings(message):
    is_admin = str(message.chat.id) == MAINTAINER
    # 普通用户只可以查看，不可以设置。
    # 管理员可以查看可以设置
    if message.text != "/settings" and not is_admin:
        bot.send_message(message.chat.id, "此功能只允许管理员使用。请使用 /ping 和 /settings 查看相关信息")
        return

    # 删除公告，设置新公告
    if message.text != "/settings":
        date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        text = message.text.replace("/settings", f"{date}\t")
        logging.info("New announcement %s", text)
        redis_announcement(text, "set")
        setattr(message, "text", "/settings")
        settings(message)
        return

    announcement = redis_announcement()
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("删除公告", callback_data="announcement")
    if is_admin and announcement:
        markup.add(btn1)

    bot.send_message(message.chat.id, f"目前公告：\n\n {announcement or '暂无公告'}", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: re.findall(r"announcement(\S*)", call.data))
def delete_announcement(call):
    bot.send_chat_action(call.message.chat.id, 'typing')
    redis_announcement(op="del")

    bot.edit_message_text(f"目前公告：\n\n {redis_announcement() or '暂无公告'}",
                          call.message.chat.id,
                          call.message.message_id)


@bot.message_handler(commands=['credits'], chat_types=['private'])
def send_credits(message):
    bot.send_chat_action(message.chat.id, 'typing')
    bot.send_message(message.chat.id, '''感谢字幕组的无私奉献！本机器人资源来源:\n
    <a href="http://www.zmz2019.com/">人人影视</a>
    <a href="http://cili001.com/">磁力下载站</a>
    <a href="http://www.zhuixinfan.com/main.php">追新番</a>
    <a href="https://www.zimuxia.cn/">FIX 字幕侠</a>
    ''', parse_mode='html', disable_web_page_preview=True)


for sub_name in dir(fansub):
    if sub_name.endswith("_offline") or sub_name.endswith("_online"):
        @bot.message_handler(commands=[sub_name], chat_types=['private'])
        def varies_fansub(message):
            bot.send_chat_action(message.chat.id, 'typing')
            # /YYeTsOffline 逃避可耻 /YYeTsOffline
            tv_name: str = re.findall(r"/.*line\s*(\S*)", message.text)[0]
            class_name: str = re.findall(r"/(.*line)", message.text)[0]
            class_ = getattr(fansub, class_name)

            if not tv_name:
                bot.send_message(message.chat.id,
                                 f"{class_.__name__}: 请附加你要搜索的剧集名称，如 `/{class_name} 逃避可耻`",
                                 parse_mode='markdown')
                return

            else:
                setattr(message, "text", tv_name)
            base_send_search(message, class_())


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
        r = bot.send_photo(uid, mem.getvalue(), caption=text)
    else:
        r = bot.send_message(uid, text)

    logging.info("Reply has been sent to %s with message id %s", uid, r.message_id)
    bot.reply_to(message, "回复已经发送给这位用户")
    fw = bot.forward_message(message.chat.id, uid, r.message_id)
    time.sleep(3)
    bot.delete_message(message.chat.id, fw.message_id)
    logging.info("Forward has been deleted.")


@bot.message_handler(content_types=["photo", "text"], chat_types=['private'])
def send_search(message):
    if str(message.chat.id) == os.getenv("SPECIAL_ID") and message.text == "❤️":
        bot.reply_to(message, "❤️")
    # normal ordered search
    if message.text in ("Voice Chat started", "Voice Chat ended"):
        logging.warning("This is really funny %s", message.text)
        return
    base_send_search(message)


@bot.message_handler(content_types=["document"], chat_types=['private'])
def ban_user(message):
    if str(message.chat.id) != MAINTAINER:
        return

    mem = io.BytesIO()
    file_id = message.document.file_id
    file_info = bot.get_file(file_id)
    content = bot.download_file(file_info.file_path)
    mem.write(content)
    user_list = mem.getvalue().decode("u8").split("\n")
    yy = fansub.YYeTsOffline()
    client = yy.mongo
    user_col = client["zimuzu"]["users"]
    comment_col = client["zimuzu"]["comment"]
    text = ""
    for line in user_list:
        user, reason = line.split(maxsplit=1)
        ban = {"disable": True, "reason": reason}
        user_col.update_one({"username": user}, {"$set": {"status": ban}})
        comment_col.delete_many({"username": user})
        status = f"{user} 已经被禁言，原因：{reason}\n"
        logging.info("Banning %s", status)
        text += status
    bot.reply_to(message, text)
    mem.close()


def base_send_search(message, instance=None):
    if instance is None:
        fan = fansub.FansubEntrance()
    else:
        fan = instance
    bot.send_chat_action(message.chat.id, 'typing')

    today_request("total")
    if message.reply_to_message and message.reply_to_message.document and \
            message.reply_to_message.document.file_name.startswith("error") and str(message.chat.id) == MAINTAINER:
        today_request("answer")
        send_my_response(message)
        return

    name = zhconv.convert(message.text, "zh-hans")
    logging.info('Receiving message: %s from user %s(%s)', name, message.chat.username, message.chat.id)
    if name is None:
        today_request("invalid")
        with open('warning.webp', 'rb') as sti:
            bot.send_message(message.chat.id, "不要调戏我！我会报警的")
            bot.send_sticker(message.chat.id, sti)
        return

    result = fan.search_preview(name)

    markup = types.InlineKeyboardMarkup()

    source = result.get("class")
    result.pop("class")
    count, MAX, warning = 0, 20, ""
    for url_hash, detail in result.items():
        if count > MAX:
            warning = f"*结果太多啦，目前只显示前{MAX}个。关键词再精准一下吧！*\n\n"
            break
        btn = types.InlineKeyboardButton(detail["name"], callback_data="choose%s" % url_hash)
        markup.add(btn)
        count += 1

    if result:
        logging.info("🎉 Resource match.")
        today_request("success")
        bot.reply_to(message, f"{warning}呐🌹，一共%d个结果，选一个呀！来源：%s" % (len(result), source),
                     reply_markup=markup, parse_mode="markdown")
    else:
        logging.warning("⚠️️ Resource not found")
        today_request("fail")
        bot.send_chat_action(message.chat.id, 'typing')

        encoded = quote_plus(name)
        bot.reply_to(message, f"没有找到你想要的信息，是不是你打了错别字，或者搜索了一些国产影视剧。🤪\n"
                              f"还是你想调戏我哦🙅‍ 本小可爱拒绝被调戏️\n\n"
                              "⚠️如果确定要我背锅，那么请使用 /help 来提交错误", disable_web_page_preview=True)
        if REPORT:
            btn = types.InlineKeyboardButton("快来修复啦", callback_data="fix")
            markup.add(btn)
            bot.send_chat_action(message.chat.id, 'upload_document')
            bot.send_message(message.chat.id, f"《{name}》😭\n大部分情况下机器人是好用的，不要怀疑我的代码质量.\n"
                                              f"如果你真的确定是机器人出问题了，那么点下面的按钮叫 @BennyThink 来修！\n"
                                              f"⚠️报错前请三思，不要乱点，确保这锅应该甩给我。否则我会很生气的😡小心被拉黑哦",
                             reply_markup=markup)
            content = f""" 报告者：{message.chat.first_name}{message.chat.last_name or ""}@{message.chat.username or ""}({message.chat.id})
                            问题发生时间：{time.strftime("%Y-%m-%data %H:%M:%S", time.localtime(message.date))}
                            请求内容：{name} 
                            请求URL：{YYETS_SEARCH_URL.format(kw=encoded)}\n\n
                            
                        """
            save_error_dump(message.chat.id, content)


def magic_recycle(fan, call, url_hash):
    if fan.redis.exists(url_hash):
        return False
    else:
        logging.info("👏 Wonderful magic!")
        bot.answer_callback_query(call.id, "小可爱使用魔法回收了你的搜索结果，你再搜索一次试试看嘛🥺", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        return True


@bot.callback_query_handler(func=lambda call: re.findall(r"choose(\S*)", call.data))
def choose_link(call):
    fan = fansub.FansubEntrance()
    bot.send_chat_action(call.message.chat.id, 'typing')
    # call.data is url_hash, with sha1, http://www.rrys2020.com/resource/36588
    resource_url_hash = re.findall(r"choose(\S*)", call.data)[0]
    if magic_recycle(fan, call, resource_url_hash):
        return

    result = fan.search_result(resource_url_hash)
    with tempfile.NamedTemporaryFile(mode='wb+', prefix=result["cnname"].replace("/", " "), suffix=".txt") as tmp:
        bytes_data = json.dumps(result["all"], ensure_ascii=False, indent=4).encode('u8')
        tmp.write(bytes_data)
        tmp.flush()
        with open(tmp.name, "rb") as f:
            if result.get("type") == "resource":
                caption = "{}\n\n{}".format(result["cnname"], result["share"])
            else:
                caption = result["all"].replace(r"\n", "  ")
            bot.send_chat_action(call.message.chat.id, 'upload_document')
            bot.send_document(call.message.chat.id, f, caption=caption)


@bot.callback_query_handler(func=lambda call: re.findall(r"approve", call.data))
def approve_spam(call):
    obj_id = re.findall(r"approve(\S*)", call.data)[0]
    data = {
        "obj_id": obj_id,
        "token": TOKEN
    }
    requests.post(f"{DOMAIN}api/admin/spam", json=data)
    bot.answer_callback_query(call.id, 'Approved')
    bot.delete_message(call.message.chat.id, call.message.message_id)


@bot.callback_query_handler(func=lambda call: re.findall(r"ban", call.data))
def ban_spam(call):
    obj_id = re.findall(r"ban(\S*)", call.data)[0]
    data = {
        "obj_id": obj_id,
        "token": TOKEN
    }
    requests.delete(f"{DOMAIN}api/admin/spam", json=data)
    bot.answer_callback_query(call.id, 'Banned')
    bot.delete_message(call.message.chat.id, call.message.message_id)


@bot.callback_query_handler(func=lambda call: re.findall(r"unwelcome(\d*)", call.data))
def send_unwelcome(call):
    # this will come from me only
    logging.warning("I'm so unhappy!")
    message = call.message
    bot.send_chat_action(message.chat.id, 'typing')

    # angry_count = angry_count + 1
    global angry_count
    angry_count += 1
    uid = re.findall(r"unwelcome(\d*)", call.data)[0]

    if uid:
        text = "人人影视主要提供欧美日韩等海外资源，你的这个真没有🤷‍。\n" \
               "<b>麻烦你先从自己身上找原因</b>，我又不是你的专属客服。\n" \
               "不要再报告这种错误了🙄️，面倒な。😡"
        bot.send_message(uid, text, parse_mode="html")
        bot.reply_to(message, f"有生之日 生气次数：{angry_count}")


@bot.callback_query_handler(func=lambda call: call.data == 'fix')
def report_error(call):
    logging.error("Reporting error to maintainer.")
    bot.send_chat_action(call.message.chat.id, 'typing')
    error_content = get_error_dump(call.message.chat.id)
    if error_content == "":
        bot.answer_callback_query(call.id, '多次汇报重复的问题并不会加快处理速度。', show_alert=True)
        return

    text = f'人人影视机器人似乎出现了一些问题🤔🤔🤔……{error_content[0:300]}'

    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("unwelcome", callback_data=f"unwelcome{call.message.chat.id}")
    markup.add(btn)

    bot.send_message(MAINTAINER, text, disable_web_page_preview=True, reply_markup=markup)

    with tempfile.NamedTemporaryFile(mode='wb+', prefix=f"error_{call.message.chat.id}_", suffix=".txt") as tmp:
        tmp.write(error_content.encode('u8'))
        tmp.flush()

        with open(tmp.name, "rb") as f:
            bot.send_chat_action(call.message.chat.id, 'upload_document')
            bot.send_document(MAINTAINER, f, caption=str(call.message.chat.id))

    bot.answer_callback_query(call.id, 'Debug信息已经发送给维护者，请耐心等待回复~', show_alert=True)


if __name__ == '__main__':
    logging.info('YYeTs bot is running...')
    scheduler = BackgroundScheduler()
    scheduler.add_job(reset_request, 'cron', hour=0, minute=0)
    scheduler.start()
    bot.polling()
