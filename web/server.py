#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - server.py
# 2/5/21 21:02
#

__author__ = "Benny <benny.think@gmail.com>"

import json
import socket
from platform import uname
import os
import contextlib
from http import HTTPStatus
from concurrent.futures import ThreadPoolExecutor
from tornado import web, ioloop, httpserver, gen, options
from tornado.log import enable_pretty_logging
import pymongo
from tornado.concurrent import run_on_executor

enable_pretty_logging()
client = pymongo.MongoClient()
db = client["zimuzu"]


class BaseHandler(web.RequestHandler):
    def data_received(self, chunk):
        pass


class IndexHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        with open("index.html") as f:
            html = f.read()
        self.write(html)


class ResourceHandler(BaseHandler):
    executor = ThreadPoolExecutor(50)

    @run_on_executor()
    def get_resource_data(self):
        param = self.get_query_argument("id")
        with contextlib.suppress(ValueError):
            param = int(param)
        data = db["yyets"].find_one_and_update(
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
        data = db["yyets"].find({
            "$or": [
                {"data.info.cnname": {'$regex': f'.*{param}.*'}},
                {"data.info.enname": {'$regex': f'.*{param}.*'}},
                {"data.info.aliasname": {'$regex': f'.*{param}.*'}},
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
        top_type = self.get_query_argument("type", "all")
        projection = {'_id': False,
                      'data.info': True,
                      }
        if top_type == "all":
            data = db["yyets"].find({}, projection).sort("data.info.views", pymongo.DESCENDING).limit(10)
        else:
            data = []
        return dict(data=list(data))

    @gen.coroutine
    def get(self):
        resp = yield self.get_top_resource()
        self.write(resp)


class MetricsHandler(BaseHandler):
    executor = ThreadPoolExecutor(50)

    @run_on_executor()
    def set_metrics(self):
        metrics_name = self.get_query_argument("type", "access")
        db['metrics'].find_one_and_update(
            {'type': metrics_name}, {'$inc': {'count': 1}}
        )
        self.set_status(HTTPStatus.CREATED)
        return {}

    @run_on_executor()
    def get_metrics(self):
        metrics_name = self.get_query_argument("type", "access")
        return db['metrics'].find_one({'type': metrics_name}, {'_id': False})

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
    settings = {
        "cookie_secret": "5Li05DtnQewDZq1mDVB3HAAhFqUu2vD2USnqezkeu+M=",
        "xsrf_cookies": False,
        "autoreload": True,
        # 'template_path': '.',
    }

    application = web.Application(handlers)

    @staticmethod
    def run_server(port, host, **kwargs):
        tornado_server = httpserver.HTTPServer(RunServer.application, **kwargs)
        tornado_server.bind(port, host)
        tornado_server.start()

        try:
            print('Server is running on http://{}:{}'.format("127.0.0.1", port))
            ioloop.IOLoop.instance().current().start()
        except KeyboardInterrupt:
            ioloop.IOLoop.instance().stop()
            print('"Ctrl+C" received, exiting.\n')


if __name__ == "__main__":
    options.define("p", default=8888, help="running port", type=int)
    options.define("h", default='127.0.0.1', help="listen address", type=str)
    options.parse_command_line()
    p = options.options.p
    h = options.options.h
    RunServer.run_server(port=p, host=h)
