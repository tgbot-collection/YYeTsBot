#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - base_db.py
# 6/16/21 20:31
#

__author__ = "Benny <benny.think@gmail.com>"

import base64
import json
import logging
import os
import random
import re
import string
import sys

import fakeredis
import redis
from captcha.image import ImageCaptcha

captcha_ex = 60 * 10
predefined_str = re.sub(r"[1l0oOI]", "", string.ascii_letters + string.digits)


class Redis:
    def __init__(self):
        if getattr(sys, '_MEIPASS', None):
            logging.info("%s Disable redis for standalone exe! %s", "#" * 10, "#" * 10)
            self.r = fakeredis.FakeStrictRedis()
        else:
            self.r = redis.StrictRedis(host=os.getenv("redis") or "localhost", decode_responses=True)

    def __del__(self):
        self.r.close()

    @classmethod
    def cache(cls, timeout: int):
        def func(fun):
            def inner(*args, **kwargs):
                func_name = fun.__name__
                cache_value = cls().r.get(func_name)
                if cache_value:
                    logging.info('Retrieving %s data from redis', func_name)
                    return json.loads(cache_value)
                else:
                    logging.info('Cache expired. Executing %s', func_name)
                    res = fun(*args, **kwargs)
                    cls().r.set(func_name, json.dumps(res), ex=timeout)
                    return res

            return inner

        return func


class OtherResource():
    def reset_top(self):
        pass


class UserResource:
    def login_user(self, username: str, password: str, captcha: str, captcha_id: str, ip: str, browser: str) -> dict:
        pass

    def get_user_info(self, username: str) -> dict:
        pass

    def update_user_last(self, username: str, now_ip: str) -> None:
        pass

    def update_user_info(self, username: str, data: dict) -> dict:
        pass


class TopResource:

    def get_most(self) -> list:
        pass

    def get_top_resource(self) -> dict:
        pass


class LikeResource:
    def get_user_like(self, username: str) -> list:
        pass

    def add_remove_fav(self, resource_id: int, username: str) -> str:
        pass


class NameResource:
    def get_names(self, is_readable: [str, bool]) -> dict:
        pass


class CommentResource:
    def get_comment(self, resource_id: int, page: int, size: int, **kwargs) -> dict:
        pass

    def add_comment(self, captcha: str, captcha_id: int, content: str, resource_id: int, ip: str,
                    username: str, browser: str, comment_id=None) -> dict:
        pass

    def delete_comment(self, comment_id: str):
        pass


class CommentReactionResource:

    def react_comment(self, username, data):
        pass


class CommentChildResource:
    def get_comment(self, parent_id: str, page: int, size: int) -> dict:
        pass


class CommentNewestResource:
    def get_comment(self, page: int, size: int, keyword=None) -> dict:
        pass


class CaptchaResource:
    redis = Redis()

    def get_captcha(self, captcha_id):
        chars = "".join([random.choice(predefined_str) for _ in range(4)])
        image = ImageCaptcha()
        data = image.generate(chars)
        self.redis.r.set(captcha_id, chars, ex=captcha_ex)
        return f"data:image/png;base64,{base64.b64encode(data.getvalue()).decode('ascii')}"

    def verify_code(self, user_input, captcha_id) -> dict:
        correct_code = self.redis.r.get(captcha_id)
        if not correct_code:
            return {"status": False, "message": "验证码已过期"}
        if user_input.lower() == correct_code.lower():
            self.redis.r.delete(correct_code)
            return {"status": True, "message": "验证通过"}
        else:
            return {"status": False, "message": "验证码错误"}


class MetricsResource:
    def set_metrics(self, metrics_type: str):
        pass

    def get_metrics(self, from_date: str, to_date: str) -> dict:
        pass


class ResourceResource:
    def get_resource_data(self, resource_id: int, username: str) -> dict:
        pass

    def search_resource(self, keyword: str) -> dict:
        pass

    def patch_resource(self, data: dict):
        pass

    def add_resource(self, data: dict):
        pass

    def delete_resource(self, data: dict):
        pass


class GrafanaQueryResource:
    def get_grafana_data(self, date_series) -> str:
        pass


class BlacklistResource(Redis):
    def get_black_list(self):
        pass


class AnnouncementResource:
    def get_announcement(self, page: int, size: int) -> dict:
        pass

    def add_announcement(self, username, content, ip, browser):
        pass


class DoubanResource:

    def get_douban_data(self, rid: int) -> dict:
        pass

    def get_douban_image(self, rid: int) -> bytes:
        pass


class DoubanReportResource:

    def report_error(self, captcha: str, captcha_id: int, content: str, resource_id: int) -> dict:
        pass

    def get_error(self) -> dict:
        pass


class NotificationResource:

    def get_notification(self, username, page, size):
        pass

    def update_notification(self, username, verb, comment_id):
        pass


class UserEmailResource:

    def verify_email(self, username, code):
        pass


class CategoryResource:

    def get_category(self, query: dict):
        pass


class ResourceLatestResource:
    @staticmethod
    def get_latest_resource() -> dict:
        pass
