#!/usr/bin/env python3
# coding: utf-8
import os
from http import HTTPStatus
from pathlib import Path

from tornado import gen
from tornado.concurrent import run_on_executor

from handlers.base import BaseHandler

filename = Path(__file__).name.split(".")[0]


class SubtitleDownloadHandler(BaseHandler):
    filename = filename

    @run_on_executor()
    def find_and_download(self):
        file = self.json.get("file")
        _id = self.json.get("id")
        self.set_header("x-filename", Path(file).name)
        p = Path(__file__).parent.parent.joinpath("subtitle_data", file)
        self.set_header("Content-Type", "application/bin")
        try:
            data = p.read_bytes()
            self.instance.add_download(_id)
            return data
        except FileNotFoundError:
            self.set_status(HTTPStatus.NOT_FOUND)
            return b""

    @gen.coroutine
    def post(self):
        resp = yield self.find_and_download()
        self.write(resp)


class ResourceHandler(BaseHandler):
    filename = filename

    @run_on_executor()
    def get_resource_data(self):
        query = self.get_query_argument("id", None)
        resource_id = int(query) if query.isdigit() else 0
        username = self.get_current_user()
        data = self.instance.get_resource_data(resource_id, username)
        if not data:
            self.ban()
            self.set_status(HTTPStatus.NOT_FOUND)
            data = {}

        return data

    @run_on_executor()
    def search_resource(self):
        kw = self.get_query_argument("keyword").lower()
        search_type = self.get_query_argument("type", "default")
        self.set_header("search-engine", "Meilisearch" if os.getenv("MEILISEARCH") else "MongoDB")
        return self.instance.search_resource(kw, search_type)

    @gen.coroutine
    def get(self):
        if self.get_query_argument("id", None):
            resp = yield self.get_resource_data()
        elif self.get_query_argument("keyword", None):
            resp = yield self.search_resource()
        else:
            resp = "error"
        self.write(resp)


class ResourceLatestHandler(BaseHandler):
    filename = filename

    @run_on_executor()
    def get_latest(self):
        size = int(self.get_query_argument("size", "100"))
        result = self.instance.get_latest_resource()
        result["data"] = result["data"][:size]
        return result

    @gen.coroutine
    def get(self):
        resp = yield self.get_latest()
        self.write(resp)


class TopHandler(BaseHandler):
    filename = filename

    def get_user_like(self) -> list:
        username = self.get_current_user()
        return self.instance.get_user_like(username)

    def get_most(self) -> list:
        return self.instance.get_most()

    @run_on_executor()
    def get_top_resource(self):
        return self.instance.get_top_resource()

    @gen.coroutine
    def get(self):
        resp = yield self.get_top_resource()
        self.write(resp)


class NameHandler(BaseHandler):
    filename = filename

    @run_on_executor()
    def get_names(self):
        is_readable = self.get_query_argument("human", None)
        return self.instance.get_names(is_readable)

    @gen.coroutine
    def get(self):
        resp = yield self.get_names()
        self.write(resp)


class AdsenseStatusHandler(BaseHandler):
    @run_on_executor()
    def get_adsense_status(self):
        return {"data": os.getenv("HIDE_ADSENSE", "").split(",")}

    @gen.coroutine
    def get(self):
        resp = yield self.get_adsense_status()
        self.write(resp)
