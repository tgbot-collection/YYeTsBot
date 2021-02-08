#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - server.py
# 2/5/21 21:02
#

__author__ = "Benny <benny.think@gmail.com>"

import os
import contextlib
import logging

import pymongo
from http import HTTPStatus
from concurrent.futures import ThreadPoolExecutor
from tornado import web, ioloop, httpserver, gen, options
from tornado.log import enable_pretty_logging

from tornado.concurrent import run_on_executor
from apscheduler.schedulers.background import BackgroundScheduler

from crypto import decrypt

enable_pretty_logging()

mongo_host = os.getenv("mongo") or "localhost"


class Mongo:
    def __init__(self):
        self.client = pymongo.MongoClient(host=mongo_host, connect=False)
        self.db = self.client["zimuzu"]

    def __del__(self):
        self.client.close()


class BaseHandler(web.RequestHandler):
    mongo = Mongo()

    def data_received(self, chunk):
        pass


class IndexHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        with open("index.html") as f:
            html = f.read()
        self.write(html)


def anti_crawler(self) -> bool:
    cypertext = self.request.headers.get("ne1", "")
    referer = self.request.headers.get("Referer")
    param = self.get_query_argument("id")
    uri = self.request.uri
    logging.info("Verifying: Referer:[%s] ct:[%s], uri:[%s], id:[%s]", referer, cypertext, uri, param)

    if (referer is None) or (param not in referer):
        return True

    try:
        passphrase = param
        result = decrypt(cypertext, passphrase).decode('u8')
    except Exception:
        logging.error("Decrypt failed")
        result = ""

    if result != self.request.uri:
        return True


class ResourceHandler(BaseHandler):
    executor = ThreadPoolExecutor(50)

    @run_on_executor()
    def get_resource_data(self):
        if anti_crawler(self):
            # X-Real-IP
            logging.info("%s@%s make you happy:-(", self.request.headers.get("user-agent"),
                         self.request.headers.get("X-Real-IP")
                         )
            return {}
        param = self.get_query_argument("id")
        with contextlib.suppress(ValueError):
            param = int(param)
        data = self.mongo.db["yyets"].find_one_and_update(
            {"data.info.id": param},
            {'$inc': {'data.info.views': 1}},
            {'_id': False})
        return data

    @run_on_executor()
    def search_resource(self):
        param = self.get_query_argument("kw").lower()
        projection = {'_id': False,
                      'data.info': True,
                      }

        data = self.mongo.db["yyets"].find({
            "$or": [
                {"data.info.cnname": {'$regex': f'.*{param}.*', "$options": "-i"}},
                {"data.info.enname": {'$regex': f'.*{param}.*', "$options": "-i"}},
                {"data.info.aliasname": {'$regex': f'.*{param}.*', "$options": "-i"}},
            ]},
            projection
        )
        return dict(data=list(data))

    @gen.coroutine
    def get(self):
        if self.get_query_argument("id", None):
            resp = yield self.get_resource_data()
        elif self.get_query_argument("kw", None):
            resp = yield self.search_resource()
        else:
            resp = "error"
        self.write(resp)


class TopHandler(BaseHandler):
    executor = ThreadPoolExecutor(50)

    @run_on_executor()
    def get_top_resource(self):
        projection = {'_id': False,
                      'data.info': True,
                      }

        us = self.mongo.db["yyets"].find({"data.info.area": "美国"}, projection).sort("data.info.views",
                                                                                    pymongo.DESCENDING).limit(10)

        jp = self.mongo.db["yyets"].find({"data.info.area": "日本"}, projection).sort("data.info.views",
                                                                                    pymongo.DESCENDING).limit(10)
        us_data = list(us)
        jp_data = list(jp)
        us_data.extend(jp_data)
        return dict(data=us_data)

    @gen.coroutine
    def get(self):
        resp = yield self.get_top_resource()
        self.write(resp)


class MetricsHandler(BaseHandler):
    executor = ThreadPoolExecutor(50)

    @run_on_executor()
    def set_metrics(self):
        self.mongo.db['metrics'].update_one(
            {'type': "access"}, {'$inc': {'count': 1}},
            upsert=True
        )
        # today
        self.mongo.db['metrics'].update_one(
            {'type': "today"}, {'$inc': {'count': 1}},
            upsert=True
        )
        self.set_status(HTTPStatus.CREATED)
        return {}

    @run_on_executor()
    def get_metrics(self):
        result = self.mongo.db['metrics'].find({}, {'_id': False})
        return dict(metrics=list(result))

    @gen.coroutine
    def get(self):
        resp = yield self.get_metrics()
        self.write(resp)

    @gen.coroutine
    def post(self):
        resp = yield self.set_metrics()
        self.write(resp)


class RunServer:
    root_path = os.path.dirname(__file__)
    static_path = os.path.join(root_path, '')
    handlers = [
        (r'/api/resource', ResourceHandler),
        (r'/api/top', TopHandler),
        (r'/api/metrics', MetricsHandler),
        (r'/', IndexHandler),
        (r'/(.*\.html|.*\.js|.*\.css|.*\.png|.*\.jpg|.*\.ico|.*\.gif|.*\.woff2)', web.StaticFileHandler,
         {'path': static_path}),
    ]

    application = web.Application(handlers, xheaders=True)

    @staticmethod
    def run_server(port, host, **kwargs):
        tornado_server = httpserver.HTTPServer(RunServer.application, **kwargs)
        tornado_server.bind(port, host)
        tornado_server.start(0)

        try:
            print('Server is running on http://{}:{}'.format(host, port))
            ioloop.IOLoop.instance().current().start()
        except KeyboardInterrupt:
            ioloop.IOLoop.instance().stop()
            print('"Ctrl+C" received, exiting.\n')


def reset_day():
    m = Mongo()
    m.db["metrics"].delete_one({"type": "today"})


if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(reset_day, 'cron', hour=0, minute=0)
    scheduler.start()
    options.define("p", default=8888, help="running port", type=int)
    options.define("h", default='127.0.0.1', help="listen address", type=str)
    options.parse_command_line()
    p = options.options.p
    h = options.options.h
    RunServer.run_server(port=p, host=h)
