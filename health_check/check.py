#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - check.py
# 1/22/21 16:36
#

__author__ = "Benny <benny.think@gmail.com>"

import logging
import os
import subprocess

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telethon import TelegramClient, events

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(filename)s [%(levelname)s]: %(message)s')
logging.getLogger('apscheduler.executors.default').propagate = False
api_id = int(os.environ.get("API_ID") or "")
api_hash = os.environ.get("API_HASH") or ""
bot_name = os.environ.get("BOT_NAME") or "yyets_bot"
compose_file = os.environ.get("COMPOSE") or "/Users/benny/PycharmProjects/BotsRunner/docker-compose.yml"
client = TelegramClient('client-hc', api_id, api_hash,
                        device_model="Benny-health-check", system_version="89", app_version="1.0.0")
check_status = []


@client.on(events.NewMessage(incoming=True, pattern='(?i).*欢迎使用，直接发送想要的剧集标题给我就可以了.*', from_users=bot_name))
async def my_event_handler(event):
    logging.info("Okay it's working %s", event)
    check_status.clear()


async def send_health_check():
    if check_status:
        # restart it
        await restart_bot()
    else:
        await client.send_message(bot_name, '/start')
        check_status.append("check")


async def restart_bot():
    logging.warning("Bot seems to be down. Restarting now....")
    cmd = f"docker-compose -f {compose_file} restart yyets"
    output = subprocess.check_output(cmd.split())
    logging.warning(output)


if __name__ == '__main__':
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_health_check, 'interval', seconds=300)
    scheduler.start()
    # send_health_check()
    client.start()
    client.run_until_disconnected()
