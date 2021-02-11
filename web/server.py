#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - server.py
# 2/5/21 21:02
#

__author__ = "Benny <benny.think@gmail.com>"

import os
import contextlib
import logging
import json

import redis
import pymongo
from http import HTTPStatus
from concurrent.futures import ThreadPoolExecutor
from tornado import web, ioloop, httpserver, gen, options
from tornado.log import enable_pretty_logging
from tornado import escape
from tornado.concurrent import run_on_executor
from apscheduler.schedulers.background import BackgroundScheduler

from crypto import decrypt

enable_pretty_logging()

mongo_host = os.getenv("mongo") or "localhost"
if os.getenv("debug"):
    logging.basicConfig(level=logging.DEBUG)


class Mongo:
    def __init__(self):
        self.client = pymongo.MongoClient(host=mongo_host, connect=False)
        self.db = self.client["zimuzu"]

    def __del__(self):
        self.client.close()


class Redis:
    def __init__(self):
        self.r = redis.StrictRedis(host="redis", decode_responses=True, db=2)

    def __del__(self):
        self.r.close()


class BaseHandler(web.RequestHandler):
    mongo = Mongo()

    def data_received(self, chunk):
        pass


class AntiCrawler:

    def __init__(self, instance):
        self.tornado = instance
        self.redis = Redis()

    def execute(self) -> bool:

        header_result = self.header_check()
        ban_check = self.ban_check()
        if header_result or ban_check:
            return True

    def header_check(self):
        cypher_text = self.tornado.request.headers.get("ne1", "")
        referer = self.tornado.request.headers.get("Referer")
        param = self.tornado.get_query_argument("id")
        uri = self.tornado.request.uri
        logging.info("Verifying: Referer:[%s] ct:[%s], uri:[%s], id:[%s]", referer, cypher_text, uri, param)

        if (referer is None) or (param not in referer):
            return True

        try:
            passphrase = param
            result = decrypt(cypher_text, passphrase).decode('u8')
        except Exception:
            logging.error("Decrypt failed")
            result = ""

        if result != self.tornado.request.uri:
            return True

    def ban_check(self):
        con = self.redis
        ip = self.get_real_ip()
        str_count = con.r.get(ip)
        if str_count and int(str_count) > 10:
            return True

    def imprisonment(self, ip):
        con = self.redis
        # don't use incr - we need to set expire time
        if con.r.exists(ip):
            count_str = con.r.get(ip)
            count = int(count_str)
            count += 1
        else:
            count = 1
        # ban rule: (count-10)*600
        if count > 10:
            ex = (count - 10) * 3600
        else:
            ex = None
        con.r.set(ip, count, ex)

    def get_real_ip(self):
        x_real = self.tornado.request.headers.get("X-Real-IP")
        remote_ip = self.tornado.request.remote_ip
        logging.debug("X-Real-IP:%s, Remote-IP:%s", x_real, remote_ip)
        return x_real or remote_ip


class IndexHandler(BaseHandler):
    executor = ThreadPoolExecutor(100)

    @run_on_executor()
    def send_index(self):
        with open("index.html") as f:
            html = f.read()
        return html

    @gen.coroutine
    def get(self):
        resp = yield self.send_index()
        self.write(resp)


class ResourceHandler(BaseHandler):
    executor = ThreadPoolExecutor(100)

    @run_on_executor()
    def get_resource_data(self):
        forbidden = False
        banner = AntiCrawler(self)
        if banner.execute():
            logging.warning("%s@%s make you happy:-(", self.request.headers.get("user-agent"),
                            self.request.headers.get("X-Real-IP")
                            )
            data = {}
            forbidden = True
        else:
            param = self.get_query_argument("id")
            with contextlib.suppress(ValueError):
                param = int(param)
            data = self.mongo.db["yyets"].find_one_and_update(
                {"data.info.id": param},
                {'$inc': {'data.info.views': 1}},
                {'_id': False})

        if data:
            MetricsHandler.add("resource")
            forbidden = False
        else:
            # not found, dangerous
            ip = banner.get_real_ip()
            banner.imprisonment(ip)
            self.set_status(404)
            data = {}

        if forbidden:
            self.set_status(HTTPStatus.FORBIDDEN)

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
        MetricsHandler.add("search")
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
    executor = ThreadPoolExecutor(100)

    @run_on_executor()
    def get_top_resource(self):
        projection = {'_id': False,
                      'data.info': True,
                      }

        area_dict = dict(ALL={"$regex": ".*"}, US="美国", JP="日本", KR="韩国", UK="英国")
        all_data = {}
        for abbr, area in area_dict.items():
            data = self.mongo.db["yyets"].find({"data.info.area": area}, projection).sort("data.info.views",
                                                                                          pymongo.DESCENDING).limit(10)
            all_data[abbr] = list(data)

        area_dict["ALL"] = "全部"
        all_data["class"] = area_dict
        return all_data

    @gen.coroutine
    def get(self):
        resp = yield self.get_top_resource()
        self.write(resp)


class NameHandler(BaseHandler):
    executor = ThreadPoolExecutor(100)

    @staticmethod
    def json_encode(value):
        return json.dumps(value, ensure_ascii=False)

    @run_on_executor()
    def get_names(self):
        escape.json_encode = self.json_encode

        if self.get_query_argument("human", None):
            aggregation = [
                {
                    "$project": {
                        "name": {
                            "$concat": [
                                "$data.info.area",
                                "$data.info.channel_cn",
                                ": ",
                                "$data.info.cnname",
                                " ",
                                "$data.info.enname",
                                " ",
                                "$data.info.aliasname"
                            ]
                        },
                        "_id": False
                    }
                }
            ]
            query_cursor = self.mongo.db["yyets"].aggregate(aggregation)
        else:
            projection = {'_id': False,
                          'data.info.cnname': True,
                          'data.info.enname': True,
                          'data.info.aliasname': True,
                          'data.info.channel_cn': True,

                          }
            query_cursor = self.mongo.db["yyets"].find({}, projection)

        data = []
        for i in query_cursor:
            data.extend(i.values())
        return dict(data=data)

    @gen.coroutine
    def get(self):
        resp = yield self.get_names()
        self.write(resp)


class MetricsHandler(BaseHandler):
    executor = ThreadPoolExecutor(100)

    @classmethod
    def add(cls, type_name):
        cls.mongo.db['metrics'].update_one(
            {'type': type_name}, {'$inc': {'count': 1}},
            upsert=True
        )

    @run_on_executor()
    def set_metrics(self):
        self.add("access")
        self.add("today")
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


class BlacklistHandler(BaseHandler):
    executor = ThreadPoolExecutor(100)

    @run_on_executor()
    def get_black_list(self):
        r = Redis().r

        keys = r.keys("*")
        result = {}

        for key in keys:
            count = r.get(key)
            ttl = r.ttl(key)
            if ttl != -1:
                result[key] = dict(count=count, ttl=ttl)
        return result

    @gen.coroutine
    def get(self):
        resp = yield self.get_black_list()
        self.write(resp)


class RunServer:
    root_path = os.path.dirname(__file__)
    static_path = os.path.join(root_path, '')
    handlers = [
        (r'/api/resource', ResourceHandler),
        (r'/api/top', TopHandler),
        (r'/api/name', NameHandler),
        (r'/api/metrics', MetricsHandler),
        (r'/api/blacklist', BlacklistHandler),
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
    query = {"$or": [{"type": "today"}, {"type": "resource"}, {"type": "search"}]}
    m.db["metrics"].delete_many(query)


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
