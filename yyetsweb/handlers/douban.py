#!/usr/bin/env python3
# coding: utf-8
from http import HTTPStatus
from pathlib import Path

import filetype
from tornado import gen
from tornado.concurrent import run_on_executor

from handlers.base import BaseHandler

filename = Path(__file__).name.split(".")[0]


class DoubanHandler(BaseHandler):
    filename = filename

    @run_on_executor()
    def douban_data(self):
        rid = self.get_query_argument("resource_id")
        data = self.instance.get_douban_data(int(rid))
        data.pop("posterData", None)
        if not data:
            self.set_status(HTTPStatus.NOT_FOUND)
        return data

    def get_image(self) -> bytes:
        rid = self.get_query_argument("resource_id")
        return self.instance.get_douban_image(int(rid))

    @gen.coroutine
    def get(self):
        _type = self.get_query_argument("type", None)
        if _type == "image":
            data = self.get_image()
            self.set_header("content-type", filetype.guess_mime(data))
            self.write(data)
        else:
            resp = yield self.douban_data()
            self.write(resp)


class DoubanReportHandler(BaseHandler):
    class_name = "DoubanReportResource"

    @run_on_executor()
    def get_error(self):
        return self.instance.get_error()

    @run_on_executor()
    def report_error(self):
        data = self.json
        user_captcha = data["captcha_id"]
        captcha_id = data["id"]
        content = data["content"]
        resource_id = data["resource_id"]
        returned = self.instance.report_error(user_captcha, captcha_id, content, resource_id)
        status_code = returned.get("status_code", HTTPStatus.CREATED)
        self.set_status(status_code)
        return self.instance.report_error(user_captcha, captcha_id, content, resource_id)

    @gen.coroutine
    def post(self):
        resp = yield self.report_error()
        self.write(resp)

    @gen.coroutine
    def get(self):
        resp = yield self.get_error()
        self.write(resp)
