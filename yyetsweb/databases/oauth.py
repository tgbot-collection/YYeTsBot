#!/usr/bin/env python3
# coding: utf-8
from hashlib import sha256

from common.utils import ts_date
from databases.base import Mongo


class OAuthRegister(Mongo):
    def add_user(self, username, ip, browser, uid, source: "str"):
        uid = str(uid)
        # username = "Benny"
        user = self.db["users"].find_one({"uid": uid, "source": source})
        if user and user.get("password"):
            # 直接注册的用户
            return {"status": "fail", "message": "第三方登录失败，用户名已存在"}
        elif user:
            # 已存在的oauth用户
            return {"status": "success", "message": "欢迎回来，即将跳转首页", "username": username}
        else:
            # 第一次oauth登录，假定一定会成功
            # TODO GitHub可以改用户名的，但是uid不会变，也许需要加unique index
            self.db["users"].insert_one(
                {
                    "username": username,
                    "date": ts_date(),
                    "ip": ip,
                    "browser": browser,
                    "oldUser": True,
                    "source": source,
                    "uid": uid,
                    "hash": sha256(username.encode("u8")).hexdigest(),
                }
            )
            return {
                "status": "success",
                "message": "第三方登录成功，即将跳转首页",
                "username": username,
            }


class GitHubOAuth2Login(OAuthRegister):
    pass


class MSOAuth2Login(OAuthRegister):
    pass


class GoogleOAuth2Login(OAuthRegister):
    pass


class TwitterOAuth2Login(OAuthRegister):
    pass


class FacebookAuth2Login(OAuthRegister):
    pass
