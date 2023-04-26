#!/usr/bin/env python3
# coding: utf-8
from http import HTTPStatus
from pathlib import Path

from tornado import gen, web
from tornado.concurrent import run_on_executor

from handlers.base import BaseHandler

filename = Path(__file__).name.split(".")[0]


class UserHandler(BaseHandler):
    filename = filename

    def set_login(self, username):
        self.set_secure_cookie("username", username, 365)

    @run_on_executor()
    def login(self):
        data = self.json
        username = data["username"]
        password = data["password"]
        captcha = data.get("captcha")
        captcha_id = data.get("captcha_id", "")
        ip = self.get_real_ip()
        browser = self.request.headers["user-agent"]

        response = self.instance.login_user(username, password, captcha, captcha_id, ip, browser)
        if response["status_code"] in (HTTPStatus.CREATED, HTTPStatus.OK):
            self.set_login(username)
        else:
            self.set_status(response["status_code"])

        return response

    @run_on_executor()
    def update_info(self):
        result = self.instance.update_user_info(self.current_user, self.json)
        self.set_status(result.get("status_code", HTTPStatus.IM_A_TEAPOT))
        return result

    @run_on_executor()
    def get_user_info(self) -> dict:
        username = self.get_current_user()
        if username:
            data = self.instance.get_user_info(username)
        else:
            # self.set_status(HTTPStatus.UNAUTHORIZED)
            self.clear_cookie("username")
            data = {"message": "Please try to login"}
        return data

    @gen.coroutine
    def post(self):
        resp = yield self.login()
        self.write(resp)

    @gen.coroutine
    def get(self):
        resp = yield self.get_user_info()
        self.write(resp)

        # everytime we receive a GET request to this api, we'll update last_date and last_ip
        username = self.get_current_user()
        if username:
            now_ip = self.get_real_ip()
            self.instance.update_user_last(username, now_ip)

    @gen.coroutine
    @web.authenticated
    def patch(self):
        resp = yield self.update_info()
        self.write(resp)


class UserAvatarHandler(BaseHandler):
    filename = filename

    @run_on_executor()
    def update_avatar(self):
        username = self.get_current_user()
        if not username:
            self.set_status(HTTPStatus.UNAUTHORIZED)
            self.clear_cookie("username")
            return {"message": "Please try to login"}

        file = self.request.files["image"][0]["body"]
        if len(file) > 10 * 1024 * 1024:
            self.set_status(HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return {"message": "图片大小不可以超过10MB"}
        return self.instance.add_avatar(username, file)

    @run_on_executor()
    def get_avatar(self, username):
        user_hash = self.get_query_argument("hash", None)
        data = self.instance.get_avatar(username, user_hash)
        if data["image"]:
            self.set_header("Content-Type", data["content_type"])
            return data["image"]
        self.set_status(HTTPStatus.NOT_FOUND)
        return b""

    @gen.coroutine
    def post(self, _):
        resp = yield self.update_avatar()
        self.write(resp)

    @gen.coroutine
    def get(self, username):
        resp = yield self.get_avatar(username)
        self.write(resp)

    @gen.coroutine
    def head(self, username):
        resp = yield self.get_avatar(username)
        self.write(resp)


class LikeHandler(BaseHandler):
    filename = filename

    @run_on_executor()
    def like_data(self):
        username = self.get_current_user()
        return {"LIKE": self.instance.get_user_like(username)}

    @gen.coroutine
    @web.authenticated
    def get(self):
        resp = yield self.like_data()
        self.write(resp)

    @run_on_executor()
    def add_remove_fav(self):
        data = self.json
        resource_id = int(data["resource_id"])
        username = self.get_current_user()
        if username:
            response = self.instance.add_remove_fav(resource_id, username)
            self.set_status(response["status_code"])
        else:
            response = {"message": "请先登录"}
            self.set_status(HTTPStatus.UNAUTHORIZED)

        return response["message"]

    @gen.coroutine
    @web.authenticated
    def patch(self):
        resp = yield self.add_remove_fav()
        self.write(resp)


class UserEmailHandler(BaseHandler):
    filename = filename

    @run_on_executor()
    def verify_email(self):
        result = self.instance.verify_email(self.get_current_user(), self.json["code"])
        self.set_status(result.get("status_code"))
        return result

    @gen.coroutine
    @web.authenticated
    def post(self):
        resp = yield self.verify_email()
        self.write(resp)
