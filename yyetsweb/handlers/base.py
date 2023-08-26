#!/usr/bin/env python3
# coding: utf-8
import contextlib
import importlib
import json
import logging
import pathlib
from concurrent.futures import ThreadPoolExecutor
from http import HTTPStatus
from pathlib import Path

from tornado import gen, web
from tornado.concurrent import run_on_executor

from databases.base import redis_client
from handlers import cf

index = pathlib.Path(__file__).parent.parent.joinpath("templates", "index.html").as_posix()
filename = Path(__file__).name.split(".")[0]


class BaseHandler(web.RequestHandler):
    key = "user_blacklist"
    filename = filename

    executor = ThreadPoolExecutor(200)

    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.json = {}
        with contextlib.suppress(ValueError):
            self.json: dict = json.loads(self.request.body)
        class_name = self.__class__.__name__.split("Handler")[0]
        module = importlib.import_module(f"databases.{self.filename}")

        self.instance = getattr(module, class_name, lambda: 1)()
        self.r = redis_client

    def add_tauri(self):
        origin = self.request.headers.get("origin", "")
        allow_origins = ["tauri://localhost", "https://tauri.localhost"]
        if origin in allow_origins:
            self.set_header("Access-Control-Allow-Origin", origin)

    def prepare(self):
        self.add_tauri()
        if self.check_request():
            self.set_status(HTTPStatus.FORBIDDEN)
            self.finish()

    def data_received(self, chunk):
        pass

    def check_request(self):
        ban = self.__ip_check()
        user = self.__user_check()
        result = ban or user
        if result:
            self.ban()
        return result

    def get_real_ip(self):
        x_real = self.request.headers.get("X-Real-IP")
        remote_ip = self.request.remote_ip
        logging.debug("X-Real-IP:%s, Remote-IP:%s", x_real, remote_ip)
        return x_real or remote_ip

    def ban(self):
        ip = self.get_real_ip()
        self.r.incr(ip)
        count = int(self.r.get(ip))
        # ban rule: (count-10)*600
        if count <= 10:
            ex = 120
        else:
            ex = (count - 10) * 600
        if count >= 30:
            cf.ban_new_ip(ip)
        self.r.set(ip, count, ex)
        user = self.get_current_user()
        if user:
            self.r.hincrby(self.key, user)

    def get_current_user(self) -> str:
        username = self.get_secure_cookie("username") or b""
        return username.decode("u8")

    def __user_check(self):
        count = self.r.hget(self.key, self.get_current_user()) or 0
        count = int(count)
        if count >= 20:
            return True

    def __ip_check(self):
        d = self.r.get(self.get_real_ip()) or 0
        if int(d) >= 10:
            return True

    def write_error(self, status_code, **kwargs):
        if status_code in [
            HTTPStatus.FORBIDDEN,
            HTTPStatus.UNAUTHORIZED,
            HTTPStatus.NOT_FOUND,
            HTTPStatus.INTERNAL_SERVER_ERROR,
        ]:
            self.write(str(kwargs.get("exc_info")))


class IndexHandler(BaseHandler):
    @run_on_executor()
    def send_index(self):
        with open(index, encoding="u8") as f:
            html = f.read()
        return html

    @gen.coroutine
    def get(self):
        resp = yield self.send_index()
        self.write(resp)


class NotFoundHandler(BaseHandler):
    def get(self):
        # for react app
        self.render(index)
