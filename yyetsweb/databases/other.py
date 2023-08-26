#!/usr/bin/env python3
# coding: utf-8
import base64
import json
import logging
import os
import random
import re
import string
import time
from hashlib import sha256

import pymongo
import requests
from bson import ObjectId
from captcha.image import ImageCaptcha

from common.utils import Cloudflare, ts_date
from databases.base import Mongo, Redis

cf = Cloudflare()

captcha_ex = 60 * 10
predefined_str = re.sub(r"[1l0oOI]", "", string.ascii_letters + string.digits)


class Announcement(Mongo):
    def get_announcement(self, page: int, size: int) -> dict:
        condition = {}
        count = self.db["announcement"].count_documents(condition)
        data = (
            self.db["announcement"]
            .find(condition, projection={"_id": True, "ip": False})
            .sort("_id", pymongo.DESCENDING)
            .limit(size)
            .skip((page - 1) * size)
        )
        data = list(data)
        for i in data:
            i["id"] = str(i["_id"])
            i.pop("_id")
        return {
            "data": data,
            "count": count,
        }

    def add_announcement(self, username, content, ip, browser):
        construct = {
            "username": username,
            "ip": ip,
            "date": ts_date(),
            "browser": browser,
            "content": content,
        }
        self.db["announcement"].insert_one(construct)


class Blacklist(Redis):
    def get_black_list(self):
        keys = self.r.keys("*")
        result = {}

        for key in keys:
            count = self.r.get(key)
            ttl = self.r.ttl(key)
            if ttl != -1:
                result[key] = dict(count=count, ttl=ttl)
        return result


class Category(Mongo):
    def get_category(self, query: dict):
        page, size, douban = query["page"], query["size"], query["douban"]
        query.pop("page")
        query.pop("size")
        query.pop("douban")
        query_dict = {}
        for key, value in query.items():
            query_dict[f"data.info.{key}"] = value
        logging.info("Query dict %s", query_dict)
        projection = {"_id": False, "data.list": False}
        data = self.db["yyets"].find(query_dict, projection=projection).limit(size).skip((page - 1) * size)
        count = self.db["yyets"].count_documents(query_dict)
        f = []
        for item in data:
            if douban:
                douban_data = self.db["douban"].find_one(
                    {"resourceId": item["data"]["info"]["id"]}, projection=projection
                )
                if douban_data:
                    douban_data["posterData"] = base64.b64encode(douban_data["posterData"]).decode("u8")
                    item["data"]["info"]["douban"] = douban_data
                else:
                    item["data"]["info"]["douban"] = {}
            f.append(item["data"]["info"])
        return dict(data=f, count=count)


class SpamProcess(Mongo):
    def ban_spam(self, obj_id: "str"):
        obj_id = ObjectId(obj_id)
        logging.info("Deleting spam %s", obj_id)
        spam = self.db["spam"].find_one({"_id": obj_id})
        username = spam["username"]
        self.db["spam"].delete_many({"username": username})
        # self.db["comment"].delete_many({"username": username})
        cf.ban_new_ip(spam["ip"])
        return {"status": True}

    def restore_spam(self, obj_id: "str"):
        obj_id = ObjectId(obj_id)
        spam = self.db["spam"].find_one({"_id": obj_id}, projection={"_id": False})
        logging.info("Restoring spam %s", spam)
        self.db["comment"].insert_one(spam)
        self.db["spam"].delete_one({"_id": obj_id})
        return {"status": True}

    @staticmethod
    def request_approval(document: "dict"):
        token = os.getenv("TOKEN")
        owner = os.getenv("OWNER")
        obj_id = document["_id"]
        data = {
            "text": json.dumps(document, ensure_ascii=False, indent=4),
            "chat_id": owner,
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {"text": "approve", "callback_data": f"approve{obj_id}"},
                        {"text": "ban", "callback_data": f"ban{obj_id}"},
                    ]
                ]
            },
        }
        api = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(api, json=data).json()
        logging.info("Telegram response: %s", resp)


class Other(Mongo, Redis):
    def reset_top(self):
        # before resetting, save top data to history
        json_data = requests.get("http://127.0.0.1:8888/api/top").json()
        last_month = time.strftime("%Y-%m", time.localtime(time.time() - 3600 * 24))
        json_data["date"] = last_month
        json_data["type"] = "top"
        self.db["history"].insert_one(json_data)
        # save all the views data to history
        projection = {"_id": False, "data.info.views": True, "data.info.id": True}
        data = self.db["yyets"].find({}, projection).sort("data.info.views", pymongo.DESCENDING)
        result = {"date": last_month, "type": "detail"}
        for datum in data:
            rid = str(datum["data"]["info"]["id"])
            views = datum["data"]["info"]["views"]
            result[rid] = views
        self.db["history"].insert_one(result)
        # reset
        self.db["yyets"].update_many({}, {"$set": {"data.info.views": 0}})

    def import_ban_user(self):
        usernames = self.db["users"].find({"status.disable": True}, projection={"username": True})
        self.r.delete("user_blacklist")
        logging.info("Importing ban users to redis...%s", usernames)
        for username in [u["username"] for u in usernames]:
            self.r.hset("user_blacklist", username, 100)

    def fill_user_hash(self):
        users = self.db["users"].find({"hash": {"$exists": False}}, projection={"username": True})
        # do it old school
        for user in users:
            logging.info("Filling hash for %s", user)
            username = user["username"]
            hash_value = sha256(username.encode("u8")).hexdigest()
            self.db["users"].update_one({"username": username}, {"$set": {"hash": hash_value}})


class Captcha(Redis):
    def get_captcha(self, captcha_id):
        chars = "".join([random.choice(predefined_str) for _ in range(4)])
        image = ImageCaptcha()
        data = image.generate(chars)
        self.r.set(captcha_id, chars, ex=captcha_ex)
        return f"data:image/png;base64,{base64.b64encode(data.getvalue()).decode('ascii')}"

    def verify_code(self, user_input, captcha_id) -> dict:
        correct_code = self.r.get(captcha_id)
        if not correct_code:
            return {"status": False, "message": "验证码已过期"}
        if user_input.lower() == correct_code.lower():
            self.r.delete(correct_code)
            return {"status": True, "message": "验证通过"}
        else:
            return {"status": False, "message": "验证码错误"}
