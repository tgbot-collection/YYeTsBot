#!/usr/bin/env python3
# coding: utf-8
import os
import uuid
from http import HTTPStatus
from pathlib import Path

from tornado import gen, web
from tornado.concurrent import run_on_executor

from handlers.base import BaseHandler

filename = Path(__file__).name.split(".")[0]


class ResourceHandler(BaseHandler):
    filename = filename

    @run_on_executor()
    def get_resource_data(self):
        resource_id = int(self.get_query_argument("id"))
        username = self.get_current_user()
        if str(resource_id) in os.getenv("HIDDEN_RESOURCE", "").split(","):
            self.set_status(HTTPStatus.NOT_FOUND)
            return {"status": 0, "info": "资源已隐藏"}
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

    # patch and post are available to every login user
    # these are rare operations, so no gen.coroutine and run_on_executor
    @web.authenticated
    def patch(self):
        if self.instance.is_admin(self.get_current_user()):
            # may consider add admin restrictions
            pass
        for item in self.json["items"].values():
            for i in item:
                i["creator"] = self.get_current_user()
                i["itemid"] = uuid.uuid4().hex
        self.instance.patch_resource(self.json)
        self.set_status(HTTPStatus.CREATED)
        self.write({})

    @web.authenticated
    def post(self):
        self.json["data"]["list"] = []
        self.json["data"]["info"]["creator"] = self.get_current_user()
        self.set_status(HTTPStatus.CREATED)
        resp = self.instance.add_resource(self.json)
        self.write(resp)

    @web.authenticated
    def delete(self):
        if not self.instance.is_admin(self.get_current_user()):
            self.set_status(HTTPStatus.FORBIDDEN)
            self.write({"status": False, "message": "admin only"})
            return
        self.instance.delete_resource(self.json)
        self.set_status(HTTPStatus.ACCEPTED)
        self.write({})


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
