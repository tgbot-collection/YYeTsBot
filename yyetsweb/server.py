#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - server.py
# 2/5/21 21:02
#

__author__ = "Benny <benny.think@gmail.com>"

import logging
import os
import pathlib
import threading
from zoneinfo import ZoneInfo

import tornado.autoreload
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from tornado import httpserver, ioloop, options, web
from tornado.log import enable_pretty_logging

from common.dump_db import entry_dump
from common.sync import YYSub, sync_douban
from common.utils import Cloudflare, setup_logger
from databases.base import SearchEngine
from databases.other import Other
from handlers.base import IndexHandler, NotFoundHandler
from handlers.comment import (
    CommentChildHandler,
    CommentHandler,
    CommentNewestHandler,
    CommentReactionHandler,
    CommentSearchHandler,
    NotificationHandler,
)
from handlers.douban import DoubanHandler, DoubanReportHandler
from handlers.grafana import (
    GrafanaIndexHandler,
    GrafanaQueryHandler,
    GrafanaSearchHandler,
    MetricsHandler,
)
from handlers.oauth import (
    FacebookAuth2LoginHandler,
    GitHubOAuth2LoginHandler,
    GoogleOAuth2LoginHandler,
    MSOAuth2LoginHandler,
    TwitterOAuth2LoginHandler,
)
from handlers.other import (
    AnnouncementHandler,
    BlacklistHandler,
    CaptchaHandler,
    CategoryHandler,
    DBDumpHandler,
    SpamProcessHandler,
)
from handlers.resources import (
    AdsenseStatusHandler,
    NameHandler,
    ResourceHandler,
    ResourceLatestHandler,
    SubtitleDownloadHandler,
    TopHandler,
)
from handlers.user import LikeHandler, UserAvatarHandler, UserEmailHandler, UserHandler

enable_pretty_logging()
setup_logger()

if os.getenv("debug"):
    logging.getLogger().setLevel(logging.DEBUG)


class RunServer:
    static_path = pathlib.Path(__file__).parent.joinpath("templates")
    handlers = [
        (r"/", IndexHandler),
        (r"/api/resource", ResourceHandler),
        (r"/api/download", SubtitleDownloadHandler),
        (r"/api/resource/latest", ResourceLatestHandler),
        (r"/api/top", TopHandler),
        (r"/api/like", LikeHandler),
        (r"/api/user", UserHandler),
        (r"/api/user/avatar/?(.*)", UserAvatarHandler),
        (r"/api/user/email", UserEmailHandler),
        (r"/api/name", NameHandler),
        (r"/api/adsense", AdsenseStatusHandler),
        (r"/api/comment", CommentHandler),
        (r"/api/comment/search", CommentSearchHandler),
        (r"/api/comment/reaction", CommentReactionHandler),
        (r"/api/comment/child", CommentChildHandler),
        (r"/api/comment/newest", CommentNewestHandler),
        (r"/api/captcha", CaptchaHandler),
        (r"/api/metrics", MetricsHandler),
        (r"/api/grafana/", GrafanaIndexHandler),
        (r"/api/grafana/search", GrafanaSearchHandler),
        (r"/api/grafana/query", GrafanaQueryHandler),
        (r"/api/blacklist", BlacklistHandler),
        (r"/api/db_dump", DBDumpHandler),
        (r"/api/announcement", AnnouncementHandler),
        (r"/api/douban", DoubanHandler),
        (r"/api/douban/report", DoubanReportHandler),
        (r"/api/notification", NotificationHandler),
        (r"/api/category", CategoryHandler),
        (r"/api/admin/spam", SpamProcessHandler),
        (r"/auth/github", GitHubOAuth2LoginHandler),
        (r"/auth/google", GoogleOAuth2LoginHandler),
        (r"/auth/twitter", TwitterOAuth2LoginHandler),
        (r"/auth/microsoft", MSOAuth2LoginHandler),
        (r"/auth/facebook", FacebookAuth2LoginHandler),
        (
            r"/(.*\.html|.*\.js|.*\.css|.*\.png|.*\.jpg|.*\.ico|.*\.gif|.*\.woff2|.*\.gz|.*\.zip|"
            r".*\.svg|.*\.json|.*\.txt)",
            web.StaticFileHandler,
            {"path": static_path},
        ),
    ]
    settings = {
        "cookie_secret": os.getenv("cookie_secret", "eo2kcgpKwXj8Q3PKYj6nIL1J4j3b58DX"),
        "default_handler_class": NotFoundHandler,
        "login_url": "/login",
        "google_oauth": {
            "key": os.getenv("GOOGLE_CLIENT_ID"),
            "secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        },
        "github_oauth": {
            "key": os.getenv("GITHUB_CLIENT_ID"),
            "secret": os.getenv("GITHUB_CLIENT_SECRET"),
        },
        "ms_oauth": {
            "key": os.getenv("MS_CLIENT_ID"),
            "secret": os.getenv("MS_CLIENT_SECRET"),
        },
        "fb_oauth": {
            "key": os.getenv("FB_CLIENT_ID"),
            "secret": os.getenv("FB_CLIENT_SECRET"),
        },
        "twitter_consumer_key": os.getenv("TWITTER_CONSUMER_KEY"),
        "twitter_consumer_secret": os.getenv("TWITTER_CONSUMER_SECRET"),
    }
    application = web.Application(handlers, **settings)

    @staticmethod
    def run_server(port, host):
        tornado_server = httpserver.HTTPServer(RunServer.application, xheaders=True)
        tornado_server.bind(port, host)
        if os.getenv("PYTHON_DEV"):
            tornado_server.start(1)
            tornado.autoreload.start()
        else:
            tornado_server.start(0)

        try:
            print("Server is running on http://{}:{}".format(host, port))
            ioloop.IOLoop.instance().current().start()
        except KeyboardInterrupt:
            ioloop.IOLoop.instance().stop()
            print('"Ctrl+C" received, exiting.\n')


if __name__ == "__main__":
    timez = ZoneInfo("Asia/Shanghai")
    scheduler = BackgroundScheduler(timezone=timez)
    scheduler.add_job(Other().reset_top, trigger=CronTrigger.from_crontab("0 0 1 * *"))
    scheduler.add_job(sync_douban, trigger=CronTrigger.from_crontab("1 1 1 * *"))
    scheduler.add_job(entry_dump, trigger=CronTrigger.from_crontab("2 2 1 * *"))
    scheduler.add_job(Other().import_ban_user, "interval", seconds=300)
    scheduler.add_job(Other().fill_user_hash, "interval", seconds=60)
    scheduler.add_job(Cloudflare().clear_fw, trigger=CronTrigger.from_crontab("0 0 */3 * *"))
    scheduler.add_job(YYSub().run, trigger=CronTrigger.from_crontab("0 1 * * *"))

    scheduler.start()
    logging.info("Dumping database and ingesting data for Meilisearh...")
    if not os.getenv("PYTHON_DEV"):
        threading.Thread(target=entry_dump).start()
    # meilisearch tasks
    if os.getenv("MEILISEARCH"):
        logging.info("%s Searching with Meilisearch. %s", "#" * 10, "#" * 10)
        engine = SearchEngine()
        threading.Thread(target=engine.run_import).start()
        threading.Thread(target=engine.monitor_yyets).start()
        threading.Thread(target=engine.monitor_douban).start()
        threading.Thread(target=engine.monitor_comment).start()

    options.define("p", default=8888, help="running port", type=int)
    options.define("h", default="127.0.0.1", help="listen address", type=str)
    options.parse_command_line()
    p = options.options.p
    h = options.options.h
    banner = """
    ▌ ▌ ▌ ▌     ▀▛▘
    ▝▞  ▝▞  ▞▀▖  ▌  ▞▀▘
     ▌   ▌  ▛▀   ▌  ▝▀▖
     ▘   ▘  ▝▀▘  ▘  ▀▀ 
                        
     Lazarus came back from the dead. By @BennyThink
                """
    print(banner)
    RunServer.run_server(port=p, host=h)
