#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - server.py
# 2/5/21 21:02
#

__author__ = "Benny <benny.think@gmail.com>"

import os
import contextlib
import logging
import json
import re
import time
import string
import random
import base64

from urllib import request
from datetime import date, timedelta
from http import HTTPStatus
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha1

import redis
import pymongo

from apscheduler.schedulers.background import BackgroundScheduler
from tornado import web, ioloop, httpserver, gen, options, escape
from tornado.log import enable_pretty_logging
from tornado.concurrent import run_on_executor
from passlib.hash import pbkdf2_sha256
from captcha.image import ImageCaptcha

enable_pretty_logging()

mongo_host = os.getenv("mongo") or "localhost"
if os.getenv("debug"):
    logging.basicConfig(level=logging.DEBUG)

escape.json_encode = lambda value: json.dumps(value, ensure_ascii=False)
predefined_str = re.sub(r"[1l0oOI]", "", string.ascii_letters + string.digits)


class Mongo:
    def __init__(self):
        self.client = pymongo.MongoClient(host=mongo_host, connect=False,
                                          connectTimeoutMS=5000, serverSelectionTimeoutMS=5000)
        self.db = self.client["zimuzu"]

    def __del__(self):
        self.client.close()


class Redis:
    def __init__(self):
        self.r = redis.StrictRedis(host="redis", decode_responses=True, db=2)

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


class BaseHandler(web.RequestHandler):
    mongo = Mongo()
    redis = Redis()
    executor = ThreadPoolExecutor(200)

    def write_error(self, status_code, **kwargs):
        if status_code in [HTTPStatus.FORBIDDEN,
                           HTTPStatus.INTERNAL_SERVER_ERROR,
                           HTTPStatus.UNAUTHORIZED,
                           HTTPStatus.NOT_FOUND]:
            self.write(str(kwargs.get('exc_info')))

    def data_received(self, chunk):
        pass

    def get_current_user(self):
        return self.get_secure_cookie("username")


class AntiCrawler:

    def __init__(self, instance):
        self.tornado = instance
        self.redis = Redis()

    def execute(self) -> bool:
        header_result = self.header_check()
        ban_check = self.ban_check()
        if header_result or ban_check:
            return True

    def header_check(self):
        referer = self.tornado.request.headers.get("Referer")
        resource_id = self.tornado.get_query_argument("id")
        uri = self.tornado.request.uri
        logging.info("Verifying: Referer:[%s] uri:[%s]", referer, uri)
        if referer is None:
            return True
        if resource_id not in uri:
            return True
        if resource_id not in referer:
            return True

    def ban_check(self):
        con = self.redis
        ip = self.get_real_ip()
        str_count = con.r.get(ip)
        if str_count and int(str_count) > 10:
            return True

    def imprisonment(self, ip):
        con = self.redis
        # don't use incr - we need to set expire time
        if con.r.exists(ip):
            count_str = con.r.get(ip)
            count = int(count_str)
            count += 1
        else:
            count = 1
        # ban rule: (count-10)*600
        if count > 10:
            ex = (count - 10) * 3600
        else:
            ex = None
        con.r.set(ip, count, ex)

    def get_real_ip(self):
        x_real = self.tornado.request.headers.get("X-Real-IP")
        remote_ip = self.tornado.request.remote_ip
        logging.debug("X-Real-IP:%s, Remote-IP:%s", x_real, remote_ip)
        return x_real or remote_ip


class IndexHandler(BaseHandler):

    @run_on_executor()
    def send_index(self):
        with open("index.html") as f:
            html = f.read()
        return html

    @gen.coroutine
    def get(self):
        resp = yield self.send_index()
        self.write(resp)


class UserHandler(BaseHandler):

    def set_login(self, username):
        self.set_secure_cookie("username", username, 365)

    @run_on_executor()
    def login_user(self):
        data = json.loads(self.request.body)
        username = data["username"]
        password = data["password"]
        data = self.mongo.db["users"].find_one({"username": username})
        returned_value = ""
        if data:
            # try to login
            stored_password = data["password"]
            if pbkdf2_sha256.verify(password, stored_password):
                self.set_status(HTTPStatus.OK)
                self.set_login(username)
            else:
                self.set_status(HTTPStatus.FORBIDDEN)
                returned_value = "用户名或密码错误"
        else:
            hash_value = pbkdf2_sha256.hash(password)
            try:
                self.mongo.db["users"].insert_one(dict(username=username, password=hash_value,
                                                       date=time.asctime(),
                                                       ip=(AntiCrawler(self).get_real_ip()),
                                                       browser=self.request.headers['user-agent']
                                                       )
                                                  )
                self.set_login(username)
                self.set_status(HTTPStatus.CREATED)
            except Exception as e:
                self.set_status(HTTPStatus.INTERNAL_SERVER_ERROR)
                returned_value = str(e)

        return returned_value

    @run_on_executor()
    def add_remove_fav(self):
        data = json.loads(self.request.body)
        resource_id = int(data["resource_id"])
        username = self.get_secure_cookie("username")
        if username:
            username = username.decode('u8')
            like_list: list = self.mongo.db["users"].find_one({"username": username}).get("like", [])
            if resource_id in like_list:
                returned_value = "已取消收藏"
                like_list.remove(resource_id)
            else:
                self.set_status(HTTPStatus.CREATED)
                like_list.append(resource_id)
                returned_value = "已添加收藏"

            value = dict(like=like_list)
            self.mongo.db["users"].update_one({"username": username}, {'$set': value})
        else:
            returned_value = "请先登录"
            self.set_status(HTTPStatus.UNAUTHORIZED)

        return returned_value

    @run_on_executor()
    def get_user_info(self) -> dict:
        username = self.get_current_user()
        projection = {"_id": False, "password": False}
        if username:
            username = username.decode("u8")
            data = self.mongo.db["users"].find_one({"username": username}, projection)
        else:
            self.set_status(HTTPStatus.UNAUTHORIZED)
            data = {}
        return data

    @gen.coroutine
    def post(self):
        resp = yield self.login_user()
        self.write(resp)

    @gen.coroutine
    def patch(self):
        resp = yield self.add_remove_fav()
        self.write(resp)

    @gen.coroutine
    def get(self):
        resp = yield self.get_user_info()
        # everytime we receive a GET request to this api, we'll update last_date and last_ip
        self.write(resp)
        self.update_user_last()

    def update_user_last(self):
        username = self.get_current_user()
        if username:
            now_time = DBDumpHandler.ts_date(None)
            now_ip = AntiCrawler(self).get_real_ip()
            username = username.decode("u8")
            self.mongo.db["users"].update_one({"username": username},
                                              {"$set": {"last_date": now_time, "last_ip": now_ip}}
                                              )


class ResourceHandler(BaseHandler):

    @run_on_executor()
    def get_resource_data(self):
        forbidden = False
        param = 0
        banner = AntiCrawler(self)
        if banner.execute():
            logging.warning("%s@%s make you happy:-(", self.request.headers.get("user-agent"),
                            self.request.headers.get("X-Real-IP")
                            )
            data = {}
            forbidden = True
        else:
            param = self.get_query_argument("id")
            with contextlib.suppress(ValueError):
                param = int(param)
            data = self.mongo.db["yyets"].find_one_and_update(
                {"data.info.id": param},
                {'$inc': {'data.info.views': 1}},
                {'_id': False})

        if data:
            forbidden = False
        else:
            # not found, dangerous
            ip = banner.get_real_ip()
            banner.imprisonment(ip)
            self.set_status(HTTPStatus.NOT_FOUND)
            data = {}

        if forbidden:
            self.set_status(HTTPStatus.FORBIDDEN)
        # is fav?
        username = self.get_secure_cookie("username")
        if not forbidden and username:
            username = username.decode('u8')
            user_like_data = self.mongo.db["users"].find_one({"username": username})
            if user_like_data and param in user_like_data.get("like", []):
                data["is_like"] = True
            else:
                data["is_like"] = False
        return data

    @run_on_executor()
    def search_resource(self):
        param = self.get_query_argument("keyword").lower()
        projection = {'_id': False,
                      'data.info': True,
                      }

        data = self.mongo.db["yyets"].find({
            "$or": [
                {"data.info.cnname": {'$regex': f'.*{param}.*', "$options": "-i"}},
                {"data.info.enname": {'$regex': f'.*{param}.*', "$options": "-i"}},
                {"data.info.aliasname": {'$regex': f'.*{param}.*', "$options": "-i"}},
            ]},
            projection
        )
        return dict(data=list(data))

    @gen.coroutine
    def get(self):
        if self.get_query_argument("id", None):
            resp = yield self.get_resource_data()
        elif self.get_query_argument("keyword", None):
            resp = yield self.search_resource()
        else:
            resp = "error"
        self.write(resp)


class TopHandler(BaseHandler):
    projection = {'_id': False, 'data.info': True}

    def get_user_like(self) -> list:
        username = self.get_secure_cookie("username")
        if username:
            like_list = self.mongo.db["users"].find_one({"username": username.decode('u8')}).get("like", [])

            data = self.mongo.db["yyets"].find({"data.info.id": {"$in": like_list}}, self.projection) \
                .sort("data.info.views", pymongo.DESCENDING)
            return list(data)
        return []

    def get_most(self):
        projection = {"_id": False, "like": True}
        data = self.mongo.db['users'].find({}, projection)
        most_like = {}
        for item in data:
            for _id in item.get("like", []):
                most_like[_id] = most_like.get(_id, 0) + 1
        most = sorted(most_like, key=most_like.get)
        most.reverse()
        most_like_data = self.mongo.db["yyets"].find({"data.info.id": {"$in": most}}, self.projection).limit(15)
        return list(most_like_data)

    @run_on_executor()
    def get_top_resource(self):

        area_dict = dict(ALL={"$regex": ".*"}, US="美国", JP="日本", KR="韩国", UK="英国")
        all_data = {}
        for abbr, area in area_dict.items():
            data = self.mongo.db["yyets"].find({"data.info.area": area}, self.projection). \
                sort("data.info.views", pymongo.DESCENDING).limit(15)
            all_data[abbr] = list(data)

        area_dict["ALL"] = "全部"

        all_data["class"] = area_dict
        return all_data

    @gen.coroutine
    def get(self):
        resp = yield self.get_top_resource()
        self.write(resp)


class UserLikeHandler(TopHandler):

    @run_on_executor()
    def get_top_resource(self):
        return {"LIKE": self.get_user_like()}

    @gen.coroutine
    def get(self):
        resp = yield self.get_top_resource()
        self.write(resp)


class NameHandler(BaseHandler):

    @run_on_executor()
    def get_names(self):

        if self.get_query_argument("human", None):
            aggregation = [
                {
                    "$project": {
                        "name": {
                            "$concat": [
                                "$data.info.area",
                                "$data.info.channel_cn",
                                ": ",
                                "$data.info.cnname",
                                " ",
                                "$data.info.enname",
                                " ",
                                "$data.info.aliasname"
                            ]
                        },
                        "_id": False
                    }
                }
            ]
            query_cursor = self.mongo.db["yyets"].aggregate(aggregation)
        else:
            projection = {'_id': False,
                          'data.info.cnname': True,
                          'data.info.enname': True,
                          'data.info.aliasname': True,
                          'data.info.channel_cn': True,

                          }
            query_cursor = self.mongo.db["yyets"].find({}, projection)

        data = []
        for i in query_cursor:
            data.extend(i.values())
        return dict(data=data)

    @gen.coroutine
    def get(self):
        resp = yield self.get_names()
        self.write(resp)


class CommentHandler(BaseHandler):

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
        if not resource_id:
            self.set_status(HTTPStatus.BAD_REQUEST)
            return {"status": False, "message": "请提供resource id"}

        condition = {"resource_id": resource_id, "deleted_at": {"$exists": False}}
        if resource_id == -1:
            condition.pop("resource_id")

        count = self.mongo.db["comment"].count_documents(condition)
        data = self.mongo.db["comment"].find(condition, projection={"_id": False, "ip": False}) \
            .sort("id", pymongo.DESCENDING).limit(size).skip((page - 1) * size)
        return {
            "data": self.hide_phone(list(data)),
            "count": count,
            "resource_id": resource_id
        }

    @run_on_executor()
    def add_comment(self):
        payload = json.loads(self.request.body)
        captcha = payload["captcha"]
        captcha_id = payload["id"]
        content = payload["content"]
        resource_id = payload["resource_id"]

        result = CaptchaHandler.verify_code(captcha_id, captcha)
        real_ip = AntiCrawler(self).get_real_ip()
        username = self.get_secure_cookie("username")
        exists = self.mongo.db["yyets"].find_one({"data.info.id": resource_id})

        if not result["status"]:
            self.set_status(HTTPStatus.BAD_REQUEST)
            return result
        if not exists:
            self.set_status(HTTPStatus.NOT_FOUND)
            return {"status": False, "message": "资源不存在"}
        if not username:
            self.set_status(HTTPStatus.UNAUTHORIZED)
            return {"status": False, "message": "请先登录再评论"}

        # one comment one document
        newest = self.mongo.db["comment"].find({"resource_id": resource_id}).sort("id", pymongo.DESCENDING)
        newest = list(newest)
        new_id = newest[0]["id"] + 1 if newest else 1

        construct = {
            "username": username.decode("u8"),
            "ip": real_ip,
            "date": time.asctime(),
            "browser": self.request.headers['user-agent'],
            "content": content,
            "id": new_id,
            "resource_id": resource_id
        }
        self.mongo.db["comment"].insert_one(construct)
        self.set_status(HTTPStatus.CREATED)
        return {"message": "评论成功"}

    def is_admin(self):
        username = self.get_current_user()
        if username:
            username = username.decode("u8")
            data = self.mongo.db["users"].find_one({"username": username, "group": {"$in": ["admin"]}})
            if data:
                return True

    @run_on_executor()
    def delete_comment(self):
        # need resource_id & id
        # payload = {"resource_id": 10004, "id": 2}
        payload = json.loads(self.request.body)
        keys = ["resource_id", "id"]
        for k in keys:
            if not payload.get(k):
                raise Exception(f"Need parameter {k}")

        if self.is_admin():
            current_time = DBDumpHandler.ts_date(None)
            count = self.mongo.db["comment"].update_one(payload, {"$set": {"deleted_at": current_time}}).modified_count
            return {"count": count, "message": "success"}
        else:
            self.set_status(HTTPStatus.UNAUTHORIZED)
            return {"count": 0, "message": "You're unauthorized to delete comment."}

    @gen.coroutine
    def get(self):
        resp = yield self.get_comment()
        self.write(resp)

    @gen.coroutine
    def post(self):
        resp = yield self.add_comment()
        self.write(resp)

    @gen.coroutine
    def delete(self):
        resp = yield self.delete_comment()
        self.write(resp)


class AnnouncementHandler(CommentHandler):

    @run_on_executor()
    def get_announcement(self):
        size = int(self.get_argument("size", "5"))
        page = int(self.get_argument("page", "1"))

        condition = {}
        count = self.mongo.db["announcement"].count_documents(condition)
        data = self.mongo.db["announcement"].find(condition, projection={"_id": False, "ip": False}) \
            .sort("_id", pymongo.DESCENDING).limit(size).skip((page - 1) * size)

        return {
            "data": list(data),
            "count": count,
        }

    @run_on_executor()
    def add_announcement(self):
        if not self.is_admin():
            self.set_status(HTTPStatus.FORBIDDEN)
            return {"message": "只有管理员可以设置公告"}

        payload = json.loads(self.request.body)
        content = payload["content"]
        username = self.get_current_user()
        real_ip = AntiCrawler(self).get_real_ip()

        construct = {
            "username": username.decode("u8"),
            "ip": real_ip,
            "date": DBDumpHandler.ts_date(None),
            "browser": self.request.headers['user-agent'],
            "content": content,
        }
        self.mongo.db["announcement"].insert_one(construct)
        self.set_status(HTTPStatus.CREATED)
        return {"message": "添加成功"}

    @gen.coroutine
    def get(self):
        resp = yield self.get_announcement()
        self.write(resp)

    @gen.coroutine
    def post(self):
        resp = yield self.add_announcement()
        self.write(resp)


class CaptchaHandler(BaseHandler):

    @run_on_executor()
    def get_captcha(self):
        request_id = self.get_argument("id", None)
        if request_id is None:
            self.set_status(HTTPStatus.BAD_REQUEST)
            return "Please supply id parameter."
        chars = "".join([random.choice(predefined_str) for _ in range(4)])
        image = ImageCaptcha()
        data = image.generate(chars)
        self.redis.r.set(request_id, chars, ex=60 * 10)
        return f"data:image/png;base64,{base64.b64encode(data.getvalue()).decode('ascii')}"

    @gen.coroutine
    def get(self):
        resp = yield self.get_captcha()
        self.write(resp)

    @classmethod
    def verify_code(cls, request_id, user_input):
        correct_code = cls.redis.r.get(request_id)
        if not correct_code:
            return {"status": False, "message": "验证码已过期"}
        if user_input.lower() == correct_code.lower():
            cls.redis.r.delete(correct_code)
            return {"status": True, "message": "验证通过"}
        else:
            return {"status": False, "message": "验证码错误"}


class MetricsHandler(BaseHandler):

    @run_on_executor()
    def set_metrics(self):
        payload = json.loads(self.request.body)
        metrics_type = payload["type"]
        today = time.strftime("%Y-%m-%d", time.localtime())
        self.mongo.db['metrics'].update_one(
            {'date': today}, {'$inc': {metrics_type: 1}},
            upsert=True
        )
        self.set_status(HTTPStatus.CREATED)
        return {}

    @run_on_executor()
    def get_metrics(self):
        # only return latest 7 days. with days parameter to generate different range
        from_date = self.get_query_argument("from", None)
        to_date = self.get_query_argument("to", None)
        if to_date is None:
            to_date = time.strftime("%Y-%m-%d", time.localtime())
        if from_date is None:
            from_date = time.strftime("%Y-%m-%d", time.localtime(time.time() - 3600 * 24 * 7))

        start_int = [int(i) for i in from_date.split("-")]
        end_int = [int(i) for i in to_date.split("-")]
        sdate = date(*start_int)  # start date
        edate = date(*end_int)  # end date
        date_range = [str(sdate + timedelta(days=x)) for x in range((edate - sdate).days + 1)]
        condition = {"date": {"$in": date_range}}
        result = self.mongo.db['metrics'].find(condition, {'_id': False}).sort("date", pymongo.DESCENDING)

        return dict(metrics=list(result))

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
        data = ["access", "search", "resource"]
        self.write(json.dumps(data))


class GrafanaQueryHandler(BaseHandler):
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
        payload = json.loads(self.request.body)
        start = payload["range"]["from"].split("T")[0]
        end = payload["range"]["to"].split("T")[0]
        date_series = self.generate_date_series(start, end)
        targets = [i["target"] for i in payload["targets"] if i["target"]]
        grafana_data = []
        for target in targets:
            data_points = []
            condition = {"date": {"$in": date_series}}
            projection = {"_id": False}
            result = self.mongo.db["metrics"].find(condition, projection)
            for i in result:
                datum = [i[target], self.time_str_int(i["date"]) * 1000]
                data_points.append(datum)
            temp = {
                "target": target,
                "datapoints": data_points
            }
            grafana_data.append(temp)
        self.write(json.dumps(grafana_data))


class BlacklistHandler(BaseHandler):

    @run_on_executor()
    def get_black_list(self):
        r = Redis().r

        keys = r.keys("*")
        result = {}

        for key in keys:
            count = r.get(key)
            ttl = r.ttl(key)
            if ttl != -1:
                result[key] = dict(count=count, ttl=ttl)
        return result

    @gen.coroutine
    def get(self):
        resp = yield self.get_black_list()
        self.write(resp)


class NotFoundHandler(BaseHandler):
    def get(self):  # for react app
        self.render("index.html")


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
        if iter(file_path):
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
        file_list = ["data/yyets_mongo.gz", "data/yyets_mysql.zip", "data/yyets_sqlite.zip"]
        result = {}
        data = self.file_info(file_list)
        for file, value in data.items():
            filename = os.path.basename(file)
            result[filename] = {
                "checksum": value[0],
                "date": value[1],
                "size": value[2],
            }

        return result

    @gen.coroutine
    def get(self):
        resp = yield self.get_hash()
        self.write(resp)


class RunServer:
    root_path = os.path.dirname(__file__)
    static_path = os.path.join(root_path, '')
    handlers = [
        (r'/api/resource', ResourceHandler),
        (r'/api/top', TopHandler),
        (r'/api/like', UserLikeHandler),
        (r'/api/user', UserHandler),
        (r'/api/name', NameHandler),
        (r'/api/comment', CommentHandler),
        (r'/api/captcha', CaptchaHandler),
        (r'/api/metrics', MetricsHandler),
        (r'/api/grafana/', GrafanaIndexHandler),
        (r'/api/grafana/search', GrafanaSearchHandler),
        (r'/api/grafana/query', GrafanaQueryHandler),
        (r'/api/blacklist', BlacklistHandler),
        (r'/api/db_dump', DBDumpHandler),
        (r'/api/announcement', AnnouncementHandler),
        (r'/', IndexHandler),
        (r'/(.*\.html|.*\.js|.*\.css|.*\.png|.*\.jpg|.*\.ico|.*\.gif|.*\.woff2|.*\.gz|.*\.zip|.*\.svg|.*\.json)',
         web.StaticFileHandler,
         {'path': static_path}),
    ]
    settings = {
        "cookie_secret": os.getenv("cookie_secret", "eo2kcgpKwXj8Q3PKYj6nIL1J4j3b58DX"),
        "default_handler_class": NotFoundHandler,
        "login_url": "/login",
    }
    application = web.Application(handlers, **settings)

    @staticmethod
    def run_server(port, host):
        tornado_server = httpserver.HTTPServer(RunServer.application, xheaders=True)
        tornado_server.bind(port, host)
        tornado_server.start(0)

        try:
            print('Server is running on http://{}:{}'.format(host, port))
            ioloop.IOLoop.instance().current().start()
        except KeyboardInterrupt:
            ioloop.IOLoop.instance().stop()
            print('"Ctrl+C" received, exiting.\n')


def reset_top():
    logging.info("resetting top...")
    m = Mongo()
    # before resetting, save top data to history
    r = request.urlopen("http://127.0.0.1:8888/api/top").read()
    json_data = json.loads(r.decode('utf-8'))
    # json_data = requests.get("http://127.0.0.1:8888/api/top").json()
    last_month = time.strftime("%Y-%m", time.localtime(time.time() - 3600 * 24))
    json_data["date"] = last_month
    json_data["type"] = "top"
    m.db["history"].insert_one(json_data)
    # save all the views data to history
    projection = {'_id': False, 'data.info.views': True, 'data.info.id': True}
    data = m.db['yyets'].find({}, projection).sort("data.info.views", pymongo.DESCENDING)
    result = {"date": last_month, "type": "detail"}
    for datum in data:
        rid = str(datum["data"]["info"]["id"])
        views = datum["data"]["info"]["views"]
        result[rid] = views
    m.db["history"].insert_one(result)
    # reset
    m.db["yyets"].update_many({}, {"$set": {"data.info.views": 0}})


if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(reset_top, 'cron', hour=0, minute=0, day=1)
    scheduler.start()
    options.define("p", default=8888, help="running port", type=int)
    options.define("h", default='127.0.0.1', help="listen address", type=str)
    options.parse_command_line()
    p = options.options.p
    h = options.options.h
    RunServer.run_server(port=p, host=h)
