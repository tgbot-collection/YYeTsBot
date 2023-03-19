#!/usr/bin/env python3
# coding: utf-8
import logging
import os
import pathlib
import time
from hashlib import sha1
from http import HTTPStatus
from pathlib import Path

from tornado import gen, web
from tornado.concurrent import run_on_executor

from common.utils import ts_date
from databases.base import Redis
from handlers.base import BaseHandler

filename = Path(__file__).name.split(".")[0]


class AnnouncementHandler(BaseHandler):
    filename = filename

    @run_on_executor()
    def get_announcement(self):
        size = int(self.get_argument("size", "5"))
        page = int(self.get_argument("page", "1"))
        return self.instance.get_announcement(page, size)

    @run_on_executor()
    def add_announcement(self):
        username = self.get_current_user()
        if not self.instance.is_admin(username):
            self.set_status(HTTPStatus.FORBIDDEN)
            return {"message": "只有管理员可以设置公告"}

        payload = self.json
        content = payload["content"]
        real_ip = self.get_real_ip()
        browser = self.request.headers["user-agent"]

        self.instance.add_announcement(username, content, real_ip, browser)
        self.set_status(HTTPStatus.CREATED)
        return {"message": "添加成功"}

    @gen.coroutine
    def get(self):
        resp = yield self.get_announcement()
        self.write(resp)

    @gen.coroutine
    @web.authenticated
    def post(self):
        resp = yield self.add_announcement()
        self.write(resp)


class DBDumpHandler(BaseHandler):
    @staticmethod
    def sizeof_fmt(num: int, suffix="B"):
        for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, "Yi", suffix)

    @staticmethod
    def checksum(file_path) -> str:
        sha = sha1()
        try:
            with open(file_path, "rb") as f:
                sha.update(f.read())
                checksum = sha.hexdigest()
        except Exception as e:
            checksum = str(e)

        return checksum

    @run_on_executor()
    @Redis.cache(3600)
    def get_hash(self):
        file_list = [
            "templates/dump/yyets_mongo.gz",
            "templates/dump/yyets_mysql.zip",
            "templates/dump/yyets_sqlite.zip",
        ]
        result = {}
        for fp in file_list:
            checksum = self.checksum(fp)
            creation = ts_date(os.stat(fp).st_ctime)
            size = self.sizeof_fmt(os.stat(fp).st_size)
            result[Path(fp).name] = {
                "checksum": checksum,
                "date": creation,
                "size": size,
            }

        return result

    @gen.coroutine
    def get(self):
        resp = yield self.get_hash()
        self.write(resp)


class CategoryHandler(BaseHandler):
    filename = filename

    @run_on_executor()
    def get_data(self):
        self.json = {k: self.get_argument(k) for k in self.request.arguments}
        self.json["size"] = int(self.json.get("size", 15))
        self.json["page"] = int(self.json.get("page", 1))
        self.json["douban"] = self.json.get("douban", False)
        return self.instance.get_category(self.json)

    @gen.coroutine
    def get(self):
        resp = yield self.get_data()
        self.write(resp)


class CaptchaHandler(BaseHandler):
    filename = filename

    @run_on_executor()
    def verify_captcha(self):
        data = self.json
        captcha_id = data.get("id", None)
        userinput = data.get("captcha", None)
        if captcha_id is None or userinput is None:
            self.set_status(HTTPStatus.BAD_REQUEST)
            return "Please supply id or captcha parameter."
        returned = self.instance.verify_code(userinput, captcha_id)
        status_code = returned.get("status")
        if not status_code:
            self.set_status(HTTPStatus.FORBIDDEN)
        return returned

    @run_on_executor()
    def captcha(self):
        request_id = self.get_argument("id", None)
        if request_id is None:
            self.set_status(HTTPStatus.BAD_REQUEST)
            return "Please supply id parameter."

        return self.instance.get_captcha(request_id)

    @gen.coroutine
    def get(self):
        resp = yield self.captcha()
        self.write(resp)

    @gen.coroutine
    def post(self):
        resp = yield self.verify_captcha()
        self.write(resp)


class BlacklistHandler(BaseHandler):
    filename = filename

    @run_on_executor()
    def get_black_list(self):
        return self.instance.get_black_list()

    @gen.coroutine
    def get(self):
        resp = yield self.get_black_list()
        self.write(resp)


class SpamProcessHandler(BaseHandler):
    filename = filename

    def process(self, method):
        obj_id = self.json.get("obj_id")
        token = self.json.get("token")
        ua = self.request.headers["user-agent"]
        ip = self.get_real_ip()
        logging.info("Authentication %s(%s) for spam API now...", ua, ip)
        if token == os.getenv("TOKEN"):
            return getattr(self.instance, method)(obj_id)
        else:
            self.set_status(HTTPStatus.FORBIDDEN)
            return {
                "status": False,
                "message": "This token is not allowed to access this API",
            }

    @gen.coroutine
    def post(self):
        self.write(self.process("restore_spam"))

    @gen.coroutine
    def delete(self):
        self.write(self.process("ban_spam"))
