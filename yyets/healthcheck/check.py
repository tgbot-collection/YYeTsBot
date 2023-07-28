#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - check.py
# 1/22/21 16:36
#

__author__ = "Benny <benny.think@gmail.com>"

import logging
import os

import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telethon import TelegramClient, events

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(filename)s [%(levelname)s]: %(message)s")
logging.getLogger("apscheduler.executors.default").propagate = False
api_id = int(os.environ.get("API_ID") or "3")
api_hash = os.environ.get("API_HASH") or "4"
bot_name = os.environ.get("BOT_NAME") or "yyets_bot"
bot_token = os.environ.get("BOT_token") or "123"

client = TelegramClient(
    "client-hc", api_id, api_hash, device_model="Benny-health-check", system_version="89", app_version="1.0.0"
)
check_status = []


@client.on(events.NewMessage(incoming=True, pattern="(?i).*欢迎使用，直接发送想要的剧集标题给我就可以了.*", from_users=bot_name))
async def my_event_handler(event):
    logging.info("Okay it's working %s", event)
    check_status.clear()


async def send_health_check():
    if check_status:
        # restart it
        await bot_warning()
    else:
        await client.send_message(bot_name, "/start")
        check_status.append("check")


async def bot_warning():
    logging.warning("Bot seems to be down. Restarting now....")
    message = "Bot is down!!!"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id=260260121&text={message}"
    resp = requests.get(url).json()
    logging.warning(resp)


async def website_check():
    home = "https://yyets.click/"
    top = "https://yyets.click/api/top"
    message = ""
    try:
        resp1 = requests.get(home)
        resp2 = requests.get(top)
    except Exception as e:
        message += f"Website is down. Requests error:{e}\n"
        resp1 = resp2 = ""

    if getattr(resp1, "status_code", 0) != 200:
        content = getattr(resp1, "content", None)
        message += f"Website home is down!!! {content}\n"
    if getattr(resp2, "status_code", 0) != 200:
        content = getattr(resp1, "content", None)
        message += f"Website top is down!!! {content}\n"
    if message:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id=260260121&text={message}"
        resp = requests.get(url).json()
        logging.error(resp)
        logging.error(message)
    else:
        logging.info("It's working home: %s bytes; top: %s bytes", len(resp1.content), len(resp2.content))


if __name__ == "__main__":
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_health_check, "interval", seconds=300)
    scheduler.add_job(website_check, "interval", seconds=60)
    scheduler.start()
    client.start()
    client.run_until_disconnected()
