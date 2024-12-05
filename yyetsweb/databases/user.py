#!/usr/bin/env python3
# coding: utf-8
import os
import random
import re
from hashlib import md5, sha256
from http import HTTPStatus

import filetype
import pymongo
import requests
from passlib.handlers.pbkdf2 import pbkdf2_sha256

from common.utils import send_mail, ts_date
from databases.base import Mongo, Redis


class Like(Mongo):
    projection = {"_id": False, "data.info": True}

    def get_user_like(self, username: str) -> list:
        like_list = self.db["users"].find_one({"username": username}).get("like", [])
        data = (
            self.db["yyets"]
            .find({"data.info.id": {"$in": like_list}}, self.projection)
            .sort("data.info.views", pymongo.DESCENDING)
        )
        return list(data)

    def add_remove_fav(self, resource_id: int, username: str) -> dict:
        returned = {"status_code": 0, "message": ""}
        like_list: list = self.db["users"].find_one({"username": username}).get("like", [])
        if resource_id in like_list:
            returned["status_code"] = HTTPStatus.OK
            returned["message"] = "已取消收藏"
            like_list.remove(resource_id)
        else:
            returned["status_code"] = HTTPStatus.CREATED
            returned["message"] = "已添加收藏"
            like_list.append(resource_id)

        value = dict(like=like_list)
        self.db["users"].update_one({"username": username}, {"$set": value})
        return returned


class User(Mongo, Redis):
    def login_user(
        self,
        username: str,
        password: str,
        captcha: str,
        captcha_id: str,
        ip: str,
        browser: str,
    ) -> dict:
        # verify captcha in the first place.
        correct_captcha = self.r.get(captcha_id)
        if correct_captcha is None:
            return {
                "status_code": HTTPStatus.BAD_REQUEST,
                "message": "验证码已过期",
                "status": False,
            }
        elif correct_captcha.lower() == captcha.lower():
            self.r.expire(captcha_id, 0)
        else:
            return {
                "status_code": HTTPStatus.FORBIDDEN,
                "message": "验证码错误",
                "status": False,
            }
        # check user account is locked.

        data = self.db["users"].find_one({"username": username}) or {}
        if data.get("status", {}).get("disable"):
            return {
                "status_code": HTTPStatus.FORBIDDEN,
                "status": False,
                "message": data.get("status", {}).get("reason"),
            }

        returned_value = {"status_code": 0, "message": ""}

        if data:
            stored_password = data["password"]
            if pbkdf2_sha256.verify(password, stored_password):
                returned_value["status_code"] = HTTPStatus.OK
            else:
                returned_value["status_code"] = HTTPStatus.FORBIDDEN
                returned_value["message"] = "用户名或密码错误"

        else:
            if os.getenv("DISABLE_REGISTER"):
                return {"status_code": HTTPStatus.BAD_REQUEST, "message": "本站已经暂停注册"}
            # register
            hash_value = pbkdf2_sha256.hash(password)
            try:
                self.db["users"].insert_one(
                    dict(
                        username=username,
                        password=hash_value,
                        date=ts_date(),
                        ip=ip,
                        browser=browser,
                        hash=sha256(username.encode("u8")).hexdigest(),
                    )
                )
                returned_value["status_code"] = HTTPStatus.CREATED
            except Exception as e:
                returned_value["status_code"] = HTTPStatus.INTERNAL_SERVER_ERROR
                returned_value["message"] = str(e)

        returned_value["username"] = data.get("username")
        returned_value["group"] = data.get("group", ["user"])
        return returned_value

    def get_user_info(self, username: str) -> dict:
        projection = {"_id": False, "password": False}
        data = self.db["users"].find_one({"username": username}, projection)
        data.update(group=data.get("group", ["user"]))
        data["hasAvatar"] = bool(data.pop("avatar", None))
        return data

    def update_user_last(self, username: str, now_ip: str) -> None:
        self.db["users"].update_one(
            {"username": username},
            {"$set": {"lastDate": (ts_date()), "lastIP": now_ip}},
        )

    def update_user_info(self, username: str, data: dict) -> dict:
        valid_fields = ["email"]
        valid_data = {}
        for field in valid_fields:
            if data.get(field):
                valid_data[field] = data[field]

        email_regex = r"@gmail\.com|@outlook\.com|@qq\.com|@163\.com"
        if valid_data.get("email") and not re.findall(email_regex, valid_data.get("email"), re.IGNORECASE):
            return {
                "status_code": HTTPStatus.BAD_REQUEST,
                "status": False,
                "message": "不支持的邮箱",
            }
        elif valid_data.get("email"):
            # rate limit
            user_email = valid_data.get("email")
            timeout_key = f"timeout-{username}"
            if self.r.get(timeout_key):
                return {
                    "status_code": HTTPStatus.TOO_MANY_REQUESTS,
                    "status": False,
                    "message": f"验证次数过多，请于{redis.ttl(timeout_key)}秒后尝试",
                }

            verify_code = random.randint(10000, 99999)
            valid_data["email"] = {"verified": False, "address": user_email}
            # send email confirm
            subject = "[人人影视下载分享站] 请验证你的邮箱"
            text = (
                f"请输入如下验证码完成你的邮箱认证。验证码有效期为24小时。<br>"
                f"如果您未有此请求，请忽略此邮件。<br><br>验证码： {verify_code}"
            )
            context = {"username": username, "text": text}
            send_mail(user_email, subject, context)
            # 发送成功才设置缓存
            self.r.set(timeout_key, username, ex=1800)
            self.r.hset(user_email, mapping={"code": verify_code, "wrong": 0})
            self.r.expire(user_email, 24 * 3600)

        self.db["users"].update_one({"username": username}, {"$set": valid_data})
        return {
            "status_code": HTTPStatus.CREATED,
            "status": True,
            "message": "邮件已经成功发送",
        }


class UserAvatar(User, Mongo):
    def add_avatar(self, username, avatar):
        self.db["users"].update_one({"username": username}, {"$set": {"avatar": avatar}})

        return {"status_code": HTTPStatus.CREATED, "message": "头像上传成功"}

    def get_avatar(self, username, user_hash=None):
        if user_hash:
            user = self.db["users"].find_one({"hash": user_hash})
        else:
            user = self.db["users"].find_one({"username": username})
        if user:
            img = user.get("avatar", b"")
            mime = filetype.guess_mime(img)
            return {"image": img, "content_type": mime}
        elif "@" in username:
            # fallback to gravatar
            url = f"https://gravatar.webp.se/avatar/{md5(username.encode('u8')).hexdigest()}"
            img = requests.get(url).content
            mime = filetype.guess_mime(img)
            return {"image": img, "content_type": mime}
        else:
            return {"image": None, "content_type": None}


class UserEmail(Mongo, Redis):
    def verify_email(self, username, code):
        email = self.db["users"].find_one({"username": username})["email"]["address"]
        verify_data = self.r.hgetall(email)
        wrong_count = int(verify_data["wrong"])
        MAX = 10
        if wrong_count >= MAX:
            self.db["users"].update_one(
                {"username": username},
                {"$set": {"status": {"disable": True, "reason": "verify email crack"}}},
            )
            return {
                "status": False,
                "status_code": HTTPStatus.FORBIDDEN,
                "message": "账户已被封锁",
            }
        correct_code = verify_data["code"]

        if correct_code == code:
            self.r.expire(email, 0)
            self.r.expire(f"timeout-{email}", 0)
            self.db["users"].update_one({"username": username}, {"$set": {"email.verified": True}})
            return {
                "status": True,
                "status_code": HTTPStatus.CREATED,
                "message": "邮箱已经验证成功",
            }
        else:
            self.r.hset(email, "wrong", wrong_count + 1)
            return {
                "status": False,
                "status_code": HTTPStatus.FORBIDDEN,
                "message": f"验证码不正确。你还可以尝试 {MAX - wrong_count} 次",
            }
