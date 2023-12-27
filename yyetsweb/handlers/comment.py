#!/usr/bin/env python3
# coding: utf-8
from http import HTTPStatus
from pathlib import Path

from tornado import gen, web
from tornado.concurrent import run_on_executor

from common.utils import hide_phone
from handlers.base import BaseHandler

filename = Path(__file__).name.split(".")[0]


class CommentHandler(BaseHandler):
    filename = filename

    @run_on_executor()
    def get_comment(self):
        query_id = self.get_argument("resource_id", "0")
        resource_id = int(query_id) if query_id.isdigit() else 0

        size = int(self.get_argument("size", "5"))
        page = int(self.get_argument("page", "1"))
        inner_size = int(self.get_argument("inner_size", "3"))
        inner_page = int(self.get_argument("inner_page", "1"))
        comment_id = self.get_argument("comment_id", None)
        sort = self.get_argument("sort", "newest")

        if not resource_id:
            self.set_status(HTTPStatus.BAD_REQUEST)
            return {"status": False, "message": "请提供resource id"}
        comment_data = self.instance.get_comment(
            resource_id,
            page,
            size,
            sort=sort,
            inner_size=inner_size,
            inner_page=inner_page,
            comment_id=comment_id,
        )
        hide_phone((comment_data["data"]))
        return comment_data

    @run_on_executor()
    def add_comment(self):
        payload = self.json
        captcha = payload["captcha"]
        captcha_id = payload["id"]
        content = payload["content"]
        resource_id = payload["resource_id"]
        comment_id = payload.get("comment_id")

        real_ip = self.get_real_ip()
        username = self.get_current_user()
        browser = self.request.headers["user-agent"]

        result = self.instance.add_comment(
            captcha,
            captcha_id,
            content,
            resource_id,
            real_ip,
            username,
            browser,
            comment_id,
        )
        self.set_status(result["status_code"])
        return result

    @run_on_executor()
    def delete_comment(self):
        # need resource_id & id
        # payload = {"id":  "obj_id"}
        payload = self.json
        username = self.get_current_user()
        comment_id = payload["comment_id"]

        if self.instance.is_admin(username):
            result = self.instance.delete_comment(comment_id)
            self.set_status(result["status_code"])
            return result
        else:
            self.set_status(HTTPStatus.UNAUTHORIZED)
            return {"count": 0, "message": "You're unauthorized to delete comment."}

    @gen.coroutine
    def get(self):
        resp = yield self.get_comment()
        self.write(resp)

    @gen.coroutine
    @web.authenticated
    def post(self):
        resp = yield self.add_comment()
        self.write(resp)

    @gen.coroutine
    @web.authenticated
    def delete(self):
        resp = yield self.delete_comment()
        self.write(resp)


class CommentReactionHandler(BaseHandler):
    filename = filename

    @run_on_executor()
    def comment_reaction(self):
        self.json.update(method=self.request.method)
        username = self.get_current_user()
        result = self.instance.react_comment(username, self.json)
        self.set_status(result.get("status_code"))
        return result

    @gen.coroutine
    @web.authenticated
    def post(self):
        resp = yield self.comment_reaction()
        self.write(resp)

    @gen.coroutine
    @web.authenticated
    def delete(self):
        resp = yield self.comment_reaction()
        self.write(resp)


class CommentChildHandler(CommentHandler):
    filename = filename

    @run_on_executor()
    def get_comment(self):
        parent_id = self.get_argument("parent_id", "0")
        size = int(self.get_argument("size", "3"))
        page = int(self.get_argument("page", "1"))

        if not parent_id:
            self.set_status(HTTPStatus.BAD_REQUEST)
            return {"status": False, "message": "请提供 parent_id"}
        comment_data = self.instance.get_comment(parent_id, page, size)
        hide_phone((comment_data["data"]))
        return comment_data

    @gen.coroutine
    def get(self):
        resp = yield self.get_comment()
        self.write(resp)


class CommentNewestHandler(CommentHandler):
    filename = filename

    @run_on_executor()
    def get_comment(self):
        size = int(self.get_argument("size", "5"))
        page = int(self.get_argument("page", "1"))

        comment_data = self.instance.get_comment(page, size)
        hide_phone((comment_data["data"]))
        return comment_data

    @gen.coroutine
    def get(self):
        resp = yield self.get_comment()
        self.write(resp)


class CommentSearchHandler(CommentHandler):
    filename = filename

    @run_on_executor()
    def search_comment(self):
        size = int(self.get_argument("size", "5"))
        page = int(self.get_argument("page", "1"))
        keyword = self.get_argument("keyword", "")
        comment_data = self.instance.get_comment(page, size, keyword)
        hide_phone((comment_data["data"]))
        return comment_data

    @gen.coroutine
    def get(self):
        resp = yield self.search_comment()
        self.write(resp)


class NotificationHandler(BaseHandler):
    filename = filename

    @run_on_executor()
    def get_notification(self):
        username = self.get_current_user()
        size = int(self.get_argument("size", "5"))
        page = int(self.get_argument("page", "1"))

        return self.instance.get_notification(username, page, size)

    @run_on_executor()
    def update_notification(self):
        username = self.get_current_user()
        verb = self.json["verb"]
        comment_id = self.json["comment_id"]
        if verb not in ["read", "unread"]:
            self.set_status(HTTPStatus.BAD_REQUEST)
            return {"status": False, "message": "verb: read or unread"}
        self.set_status(HTTPStatus.CREATED)
        return self.instance.update_notification(username, verb, comment_id)

    @gen.coroutine
    @web.authenticated
    def get(self):
        resp = yield self.get_notification()
        self.write(resp)

    @gen.coroutine
    @web.authenticated
    def patch(self):
        resp = yield self.update_notification()
        self.write(resp)
