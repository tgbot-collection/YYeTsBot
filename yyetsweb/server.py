#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - server.py
# 2/5/21 21:02
#

__author__ = "Benny <benny.think@gmail.com>"

import logging
import os
import pathlib
import platform
import threading

import pytz
import tornado.autoreload
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from tornado import httpserver, ioloop, options, web
from tornado.log import enable_pretty_logging

import dump_db
from Mongo import OtherMongoResource, ResourceLatestMongoResource
from handler import (AnnouncementHandler, BlacklistHandler, CaptchaHandler,
                     CategoryHandler, CommentChildHandler, CommentHandler,
                     CommentNewestHandler, CommentReactionHandler,
                     DBDumpHandler, DoubanHandler, DoubanReportHandler,
                     GrafanaIndexHandler, GrafanaQueryHandler,
                     GrafanaSearchHandler, IndexHandler, LikeHandler,
                     MetricsHandler, NameHandler, NotFoundHandler,
                     NotificationHandler, ResourceHandler,
                     ResourceLatestHandler, SpamProcessHandler, TopHandler,
                     UserEmailHandler, UserHandler)
from migration.douban_sync import sync_douban
from utils import Cloudflare

enable_pretty_logging()
cf = Cloudflare()
if os.getenv("debug"):
    logging.basicConfig(level=logging.DEBUG)


class RunServer:
    static_path = pathlib.Path(__file__).parent.joinpath('templates')
    handlers = [
        (r'/', IndexHandler),
        (r'/api/resource', ResourceHandler),
        (r'/api/resource/latest', ResourceLatestHandler),
        (r'/api/top', TopHandler),
        (r'/api/like', LikeHandler),
        (r'/api/user', UserHandler),
        (r'/api/user/email', UserEmailHandler),
        (r'/api/name', NameHandler),
        (r'/api/comment', CommentHandler),
        (r'/api/comment/reaction', CommentReactionHandler),
        (r'/api/comment/child', CommentChildHandler),
        (r'/api/comment/newest', CommentNewestHandler),
        (r'/api/captcha', CaptchaHandler),
        (r'/api/metrics', MetricsHandler),
        (r'/api/grafana/', GrafanaIndexHandler),
        (r'/api/grafana/search', GrafanaSearchHandler),
        (r'/api/grafana/query', GrafanaQueryHandler),
        (r'/api/blacklist', BlacklistHandler),
        (r'/api/db_dump', DBDumpHandler),
        (r'/api/announcement', AnnouncementHandler),
        (r'/api/douban', DoubanHandler),
        (r'/api/douban/report', DoubanReportHandler),
        (r'/api/notification', NotificationHandler),
        (r'/api/category', CategoryHandler),
        (r'/api/admin/spam', SpamProcessHandler),

        (r'/(.*\.html|.*\.js|.*\.css|.*\.png|.*\.jpg|.*\.ico|.*\.gif|.*\.woff2|.*\.gz|.*\.zip|'
         r'.*\.svg|.*\.json|.*\.txt)',
         web.StaticFileHandler,
         {'path': static_path}),
    ]
    settings = {
        "cookie_secret": os.getenv("cookie_secret", "eo2kcgpKwXj8Q3PKYj6nIL1J4j3b58DX"),
        "default_handler_class": NotFoundHandler,
        "login_url": "/login",
    }
    application = web.Application(handlers, **settings)

    @staticmethod
    def run_server(port, host):
        tornado_server = httpserver.HTTPServer(RunServer.application, xheaders=True)
        tornado_server.bind(port, host)
        if platform.uname().system in ("Windows", "Darwin"):
            tornado_server.start(1)
            tornado.autoreload.start()
        else:
            tornado_server.start(0)

        try:
            print('Server is running on http://{}:{}'.format(host, port))
            ioloop.IOLoop.instance().current().start()
        except KeyboardInterrupt:
            ioloop.IOLoop.instance().stop()
            print('"Ctrl+C" received, exiting.\n')


if __name__ == "__main__":
    timez = pytz.timezone('Asia/Shanghai')
    scheduler = BackgroundScheduler(timezone=timez)
    scheduler.add_job(OtherMongoResource().reset_top, trigger=CronTrigger.from_crontab("0 0 1 * *"))
    scheduler.add_job(sync_douban, trigger=CronTrigger.from_crontab("1 1 1 * *"))
    scheduler.add_job(dump_db.entry_dump, trigger=CronTrigger.from_crontab("2 2 1 * *"))
    scheduler.add_job(ResourceLatestMongoResource().refresh_latest_resource, 'interval', hours=1)
    scheduler.add_job(OtherMongoResource().import_ban_user, 'interval', seconds=300)
    scheduler.add_job(cf.clear_fw, trigger=CronTrigger.from_crontab("0 0 */5 * *"))
    scheduler.start()
    logging.info("Triggering dump database now...")
    if not os.getenv("PYTHON_DEV"):
        threading.Thread(target=dump_db.entry_dump).start()

    options.define("p", default=8888, help="running port", type=int)
    options.define("h", default='127.0.0.1', help="listen address", type=str)
    options.parse_command_line()
    p = options.options.p
    h = options.options.h
    banner = """
    ▌ ▌ ▌ ▌     ▀▛▘
    ▝▞  ▝▞  ▞▀▖  ▌  ▞▀▘
     ▌   ▌  ▛▀   ▌  ▝▀▖
     ▘   ▘  ▝▀▘  ▘  ▀▀ 
                        
     Lazarus came back from the dead. By @Bennythink
                """
    print(banner)
    RunServer.run_server(port=p, host=h)
