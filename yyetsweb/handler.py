#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - handler.py
# 6/16/21 20:30
#

__author__ = "Benny <benny.think@gmail.com>"

import contextlib
import importlib
import json
import logging
import os
import pathlib
import re
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from hashlib import sha1
from http import HTTPStatus

import filetype
import zhconv
from tornado import escape, gen, web
from tornado.concurrent import run_on_executor

from database import CaptchaResource, Redis
from utils import Cloudflare

escape.json_encode = lambda value: json.dumps(value, ensure_ascii=False)
logging.basicConfig(level=logging.INFO)
cf = Cloudflare()
if getattr(sys, '_MEIPASS', None):
    adapter = "SQLite"
else:
    adapter = "Mongo"

logging.info("%s Running with %s. %s", "#" * 10, adapter, "#" * 10)

index = pathlib.Path(__file__).parent.joinpath("templates", "index.html").as_posix()


class SecurityHandler(web.RequestHandler):
    key = "user_blacklist"

    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.r = Redis().r

    def prepare(self):
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


class BaseHandler(SecurityHandler):
    executor = ThreadPoolExecutor(200)
    class_name = f"Fake{adapter}Resource"
    adapter_module = importlib.import_module(f"{adapter}")

    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.json = {}
        with contextlib.suppress(ValueError):
            self.json: dict = json.loads(self.request.body)
        self.instance = getattr(self.adapter_module, self.class_name)()

    def write_error(self, status_code, **kwargs):
        if status_code in [HTTPStatus.FORBIDDEN,
                           HTTPStatus.UNAUTHORIZED,
                           HTTPStatus.NOT_FOUND,
                           HTTPStatus.INTERNAL_SERVER_ERROR,
                           ]:
            self.write(str(kwargs.get('exc_info')))


class TopHandler(BaseHandler):
    class_name = f"Top{adapter}Resource"

    # from Mongo import TopMongoResource
    # instance = TopMongoResource()

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


class UserHandler(BaseHandler):
    class_name = f"User{adapter}Resource"

    # from Mongo import UserMongoResource
    # instance = UserMongoResource()

    def set_login(self, username):
        self.set_secure_cookie("username", username, 365)

    @run_on_executor()
    def login_user(self):
        data = self.json
        username = data["username"]
        password = data["password"]
        captcha = data.get("captcha")
        captcha_id = data.get("captcha_id", "")
        ip = self.get_real_ip()
        browser = self.request.headers['user-agent']

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
        resp = yield self.login_user()
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


class ResourceHandler(BaseHandler):
    class_name = f"Resource{adapter}Resource"

    # from Mongo import ResourceMongoResource
    # instance = ResourceMongoResource()

    @run_on_executor()
    def get_resource_data(self):

        resource_id = int(self.get_query_argument("id"))
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
        # convert any text to zh-hans
        kw = zhconv.convert(kw, "zh-hans")
        return self.instance.search_resource(kw)

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
    class_name = f"ResourceLatest{adapter}Resource"

    # from Mongo import ResourceLatestMongoResource
    # instance = ResourceLatestMongoResource()
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


#
# class ResourceLatestHandler(BaseHandler):
#     from concurrent.futures import ProcessPoolExecutor
#
#     class_name = f"ResourceLatest{adapter}Resource"
#     executor = ProcessPoolExecutor(200)
#
#     # from Mongo import ResourceLatestMongoResource
#     # instance = ResourceLatestMongoResource()
#
#     @gen.coroutine
#     def get(self):
#         # This returns a concurrent.futures.Future
#         fut = self.executor.submit(self.instance.get_latest_resource)
#         ret = yield fut
#         self.write(ret)


class LikeHandler(BaseHandler):
    class_name = f"Like{adapter}Resource"

    # from Mongo import LikeMongoResource
    # instance = UserLikeMongoResource()

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


class NameHandler(BaseHandler):
    class_name = f"Name{adapter}Resource"

    # from Mongo import NameMongoResource
    # instance = NameMongoResource()

    @run_on_executor()
    def get_names(self):
        is_readable = self.get_query_argument("human", None)
        return self.instance.get_names(is_readable)

    @gen.coroutine
    def get(self):
        resp = yield self.get_names()
        self.write(resp)


class CommentHandler(BaseHandler):
    class_name = f"Comment{adapter}Resource"

    # from Mongo import CommentMongoResource
    # instance = CommentMongoResource()

    @staticmethod
    def hide_phone(data: list):
        for item in data:
            if item["username"].isdigit() and len(item["username"]) == 11:
                item["username"] = re.sub(r"(\d{3})\d{4}(\d{4})", r"\g<1>****\g<2>", item["username"])
        return data

    @run_on_executor()
    def get_comment(self):
        resource_id = int(self.get_argument("resource_id", "0"))
        size = int(self.get_argument("size", "5"))
        page = int(self.get_argument("page", "1"))
        inner_size = int(self.get_argument("inner_size", "3"))
        inner_page = int(self.get_argument("inner_page", "1"))
        comment_id = self.get_argument("comment_id", None)

        if not resource_id:
            self.set_status(HTTPStatus.BAD_REQUEST)
            return {"status": False, "message": "请提供resource id"}
        comment_data = self.instance.get_comment(
            resource_id, page, size,
            inner_size=inner_size, inner_page=inner_page,
            comment_id=comment_id
        )
        self.hide_phone((comment_data["data"]))
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
        browser = self.request.headers['user-agent']

        result = self.instance.add_comment(captcha, captcha_id, content, resource_id, real_ip,
                                           username, browser, comment_id)
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
    class_name = f"CommentReaction{adapter}Resource"

    # from Mongo import CommentReactionMongoResource
    # instance = CommentReactionMongoResource()

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
    class_name = f"CommentChild{adapter}Resource"

    # from Mongo import CommentChildResource
    # instance = CommentChildResource()

    @run_on_executor()
    def get_comment(self):
        parent_id = self.get_argument("parent_id", "0")
        size = int(self.get_argument("size", "3"))
        page = int(self.get_argument("page", "1"))

        if not parent_id:
            self.set_status(HTTPStatus.BAD_REQUEST)
            return {"status": False, "message": "请提供 parent_id"}
        comment_data = self.instance.get_comment(parent_id, page, size)
        self.hide_phone((comment_data["data"]))
        return comment_data

    @gen.coroutine
    def get(self):
        resp = yield self.get_comment()
        self.write(resp)


class CommentNewestHandler(CommentHandler):
    class_name = f"CommentNewest{adapter}Resource"

    # from Mongo import CommentNewestResource
    # instance = CommentNewestResource()

    @run_on_executor()
    def get_comment(self):
        size = int(self.get_argument("size", "5"))
        page = int(self.get_argument("page", "1"))

        comment_data = self.instance.get_comment(page, size)
        self.hide_phone((comment_data["data"]))
        return comment_data

    @gen.coroutine
    def get(self):
        resp = yield self.get_comment()
        self.write(resp)


class CommentSearchHandler(CommentHandler):
    class_name = f"CommentSearch{adapter}Resource"

    # from Mongo import CommentNewestResource
    # instance = CommentNewestResource()

    @run_on_executor()
    def search_comment(self):
        size = int(self.get_argument("size", "5"))
        page = int(self.get_argument("page", "1"))
        keyword = self.get_argument("keyword", "")
        comment_data = self.instance.get_comment(page, size, keyword)
        self.hide_phone((comment_data["data"]))
        return comment_data

    @gen.coroutine
    def get(self):
        resp = yield self.search_comment()
        self.write(resp)


class AnnouncementHandler(BaseHandler):
    class_name = f"Announcement{adapter}Resource"

    # from Mongo import AnnouncementMongoResource
    # instance = AnnouncementMongoResource()

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
        browser = self.request.headers['user-agent']

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


class CaptchaHandler(BaseHandler, CaptchaResource):

    @run_on_executor()
    def verify_captcha(self):
        data = self.json
        captcha_id = data.get("id", None)
        userinput = data.get("captcha", None)
        if captcha_id is None or userinput is None:
            self.set_status(HTTPStatus.BAD_REQUEST)
            return "Please supply id or captcha parameter."
        returned = self.verify_code(userinput, captcha_id)
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

        return self.get_captcha(request_id)

    @gen.coroutine
    def get(self):
        resp = yield self.captcha()
        self.write(resp)

    @gen.coroutine
    def post(self):
        resp = yield self.verify_captcha()
        self.write(resp)


class MetricsHandler(BaseHandler):
    class_name = f"Metrics{adapter}Resource"

    # from Mongo import MetricsMongoResource
    # instance = MetricsMongoResource()

    @run_on_executor()
    def set_metrics(self):
        payload = self.json
        metrics_type = payload["type"]

        self.instance.set_metrics(metrics_type)
        self.set_status(HTTPStatus.CREATED)
        return {}

    @run_on_executor()
    def get_metrics(self):
        if not self.instance.is_admin(self.get_current_user()):
            self.set_status(HTTPStatus.NOT_FOUND)
            return ""

        # only return latest 7 days. with days parameter to generate different range
        from_date = self.get_query_argument("from", None)
        to_date = self.get_query_argument("to", None)
        if to_date is None:
            to_date = time.strftime("%Y-%m-%d", time.localtime())
        if from_date is None:
            from_date = time.strftime("%Y-%m-%d", time.localtime(time.time() - 3600 * 24 * 7))

        return self.instance.get_metrics(from_date, to_date)

    @gen.coroutine
    def get(self):
        resp = yield self.get_metrics()
        self.write(resp)

    @gen.coroutine
    def post(self):
        resp = yield self.set_metrics()
        self.write(resp)


class GrafanaIndexHandler(BaseHandler):

    def get(self):
        self.write({})


class GrafanaSearchHandler(BaseHandler):

    def post(self):
        data = ["resource", "top", "home", "search", "extra", "discuss", "multiDownload", "download", "user", "share",
                "me", "database", "help", "backOld", "favorite", "unFavorite", "comment"]
        self.write(json.dumps(data))


class GrafanaQueryHandler(BaseHandler):
    class_name = f"GrafanaQuery{adapter}Resource"

    # from Mongo import GrafanaQueryMongoResource
    # instance = GrafanaQueryMongoResource()

    @staticmethod
    def generate_date_series(start: str, end: str) -> list:
        start_int = [int(i) for i in start.split("-")]
        end_int = [int(i) for i in end.split("-")]
        sdate = date(*start_int)  # start date
        edate = date(*end_int)  # end date

        delta = edate - sdate  # as timedelta
        days = []
        for i in range(delta.days + 1):
            day = sdate + timedelta(days=i)
            days.append(day.strftime("%Y-%m-%d"))
        return days

    @staticmethod
    def time_str_int(text):
        return time.mktime(time.strptime(text, "%Y-%m-%d"))

    def post(self):
        payload = self.json
        start = payload["range"]["from"].split("T")[0]
        end = payload["range"]["to"].split("T")[0]
        date_series = self.generate_date_series(start, end)
        targets = [i["target"] for i in payload["targets"] if i["target"]]
        grafana_data = []
        for target in targets:
            data_points = []
            result = self.instance.get_grafana_data(date_series)
            i: dict
            for i in result:
                datum = [i[target], self.time_str_int(i["date"]) * 1000] if i.get(target) else []
                data_points.append(datum)
            temp = {
                "target": target,
                "datapoints": data_points
            }
            grafana_data.append(temp)
        self.write(json.dumps(grafana_data))


class BlacklistHandler(BaseHandler):
    class_name = f"Blacklist{adapter}Resource"

    # from Mongo import BlacklistMongoResource
    # instance = BlacklistMongoResource()

    @run_on_executor()
    def get_black_list(self):
        return self.instance.get_black_list()

    @gen.coroutine
    def get(self):
        resp = yield self.get_black_list()
        self.write(resp)


class NotFoundHandler(BaseHandler):
    def get(self):  # for react app
        # if self.request.uri not in ["/", "/home", "/discuss", "/login", "/404", "/search",
        #                             "/resource", "/me", "/database", "help", "/statistics"
        #                             ]:
        #     self.ban()
        self.render(index)


class DBDumpHandler(BaseHandler):

    @staticmethod
    def sizeof_fmt(num: int, suffix='B'):
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, 'Yi', suffix)

    @staticmethod
    def ts_date(ts):
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))

    def file_info(self, file_path) -> dict:
        result = {}
        for fp in file_path:
            try:
                checksum = self.checksum(fp)
                creation = self.ts_date(os.stat(fp).st_ctime)
                size = self.sizeof_fmt(os.stat(fp).st_size)
                result[fp] = [checksum, creation, size]
            except Exception as e:
                result[fp] = str(e), "", ""
        return result

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
            "templates/dump/yyets_sqlite.zip"
        ]
        result = {}
        data = self.file_info(file_list)
        for file, value in data.items():
            filename = pathlib.Path(file).name
            result[filename] = {
                "checksum": value[0],
                "date": value[1],
                "size": value[2],
            }
        print(result)
        return result

    @gen.coroutine
    def get(self):
        resp = yield self.get_hash()
        self.write(resp)


class DoubanHandler(BaseHandler):
    class_name = f"Douban{adapter}Resource"

    # from Mongo import DoubanMongoResource
    # instance = DoubanMongoResource()

    @run_on_executor()
    def douban_data(self):
        rid = self.get_query_argument("resource_id")
        data = self.instance.get_douban_data(int(rid))
        data.pop("posterData")
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
    class_name = f"DoubanReport{adapter}Resource"

    # from Mongo import DoubanReportMongoResource
    # instance = DoubanReportMongoResource()

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


class NotificationHandler(BaseHandler):
    class_name = f"Notification{adapter}Resource"

    # from Mongo import NotificationResource
    # instance = NotificationResource()

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


class UserEmailHandler(BaseHandler):
    class_name = f"UserEmail{adapter}Resource"

    # from Mongo import UserEmailResource
    # instance = UserEmailResource()

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


class CategoryHandler(BaseHandler):
    class_name = f"Category{adapter}Resource"

    # from Mongo import CategoryResource
    # instance = CategoryResource()

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


class SpamProcessHandler(BaseHandler):
    class_name = f"SpamProcess{adapter}Resource"

    # from Mongo import SpamProcessMongoResource
    # instance = SpamProcessMongoResource()

    def process(self, method):
        obj_id = self.json.get("obj_id")
        token = self.json.get("token")
        ua = self.request.headers['user-agent']
        ip = self.get_real_ip()
        logging.info("Authentication %s(%s) for spam API now...", ua, ip)
        if token == os.getenv("TOKEN"):
            return getattr(self.instance, method)(obj_id)
        else:
            self.set_status(HTTPStatus.FORBIDDEN)
            return {"status": False, "message": "This token is not allowed to access this API"}

    @gen.coroutine
    def post(self):
        self.write(self.process("restore_spam"))

    @gen.coroutine
    def delete(self):
        self.write(self.process("ban_spam"))
