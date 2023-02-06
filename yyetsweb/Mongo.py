#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - mongodb.py
# 6/16/21 21:18
#

__author__ = "Benny <benny.think@gmail.com>"

import base64
import contextlib
import json
import logging
import os
import pathlib
import random
import re
import sys
import time
from datetime import date, timedelta
from http import HTTPStatus
from urllib.parse import unquote

import pymongo
import requests
from bs4 import BeautifulSoup
from bson.objectid import ObjectId
from passlib.handlers.pbkdf2 import pbkdf2_sha256
from retry import retry
from tqdm import tqdm

from database import (AnnouncementResource, BlacklistResource, CaptchaResource,
                      CategoryResource, CommentChildResource,
                      CommentNewestResource, CommentReactionResource,
                      CommentResource, DoubanReportResource, DoubanResource,
                      GrafanaQueryResource, LikeResource, MetricsResource,
                      NameResource, NotificationResource, OtherResource, Redis,
                      ResourceLatestResource, ResourceResource, TopResource,
                      UserEmailResource, UserResource)
from utils import Cloudflare, check_spam, send_mail, ts_date

lib_path = pathlib.Path(__file__).parent.parent.joinpath("yyetsbot").resolve().as_posix()
sys.path.append(lib_path)
from fansub import BD2020, XL720, NewzmzOnline, ZhuixinfanOnline, ZimuxiaOnline

logging.info("Loading fansub...%s", (BD2020, XL720, NewzmzOnline, ZhuixinfanOnline, ZimuxiaOnline))

mongo_host = os.getenv("mongo") or "localhost"
DOUBAN_SEARCH = "https://www.douban.com/search?cat=1002&q={}"
DOUBAN_DETAIL = "https://movie.douban.com/subject/{}/"
cf = Cloudflare()


class Mongo:
    def __init__(self):
        self.client = pymongo.MongoClient(host=mongo_host, connect=False,
                                          connectTimeoutMS=5000, serverSelectionTimeoutMS=5000)
        self.db = self.client["zimuzu"]

    def __del__(self):
        self.client.close()

    def is_admin(self, username: str) -> bool:
        data = self.db["users"].find_one({"username": username, "group": {"$in": ["admin"]}})
        if data:
            return True

    def is_user_blocked(self, username: str) -> str:
        r = self.db["users"].find_one({"username": username, "status.disable": True})
        if r:
            return r["status"]["reason"]

    def is_old_user(self, username: str) -> bool:
        return bool(self.db["users"].find_one({"username": username, "oldUser": True}))


class FakeMongoResource:
    pass


class OtherMongoResource(OtherResource, Mongo):
    def reset_top(self):
        # before resetting, save top data to history
        json_data = requests.get("http://127.0.0.1:8888/api/top").json()
        last_month = time.strftime("%Y-%m", time.localtime(time.time() - 3600 * 24))
        json_data["date"] = last_month
        json_data["type"] = "top"
        self.db["history"].insert_one(json_data)
        # save all the views data to history
        projection = {'_id': False, 'data.info.views': True, 'data.info.id': True}
        data = self.db['yyets'].find({}, projection).sort("data.info.views", pymongo.DESCENDING)
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
        r = Redis().r
        r.delete("user_blacklist")
        logging.info("Importing ban users to redis...%s", usernames)
        for username in [u["username"] for u in usernames]:
            r.hset("user_blacklist", username, 100)
        r.close()


class AnnouncementMongoResource(AnnouncementResource, Mongo):
    def get_announcement(self, page: int, size: int) -> dict:
        condition = {}
        count = self.db["announcement"].count_documents(condition)
        data = self.db["announcement"].find(condition, projection={"_id": True, "ip": False}) \
            .sort("_id", pymongo.DESCENDING).limit(size).skip((page - 1) * size)
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


class BlacklistMongoResource(BlacklistResource):
    def get_black_list(self):
        keys = self.r.keys("*")
        result = {}

        for key in keys:
            count = self.r.get(key)
            ttl = self.r.ttl(key)
            if ttl != -1:
                result[key] = dict(count=count, ttl=ttl)
        return result


class CommentMongoResource(CommentResource, Mongo):
    def __init__(self):
        super().__init__()
        self.inner_page = 1
        self.inner_size = 5
        self.projection = {"ip": False, "parent_id": False}

    @staticmethod
    def convert_objectid(data):
        # change _id to id, remove _id
        for item in data:
            item["id"] = str(item["_id"])
            item.pop("_id")
            for child in item.get("children", []):
                with contextlib.suppress(Exception):
                    child["id"] = str(child["_id"])
                    child.pop("_id")

    def find_children(self, parent_data):
        for item in parent_data:
            children_ids = item.get("children", [])
            condition = {"_id": {"$in": children_ids}, "deleted_at": {"$exists": False}, "type": "child"}
            children_count = self.db["comment"].count_documents(condition)
            children_data = self.db["comment"].find(condition, self.projection) \
                .sort("_id", pymongo.DESCENDING).limit(self.inner_size).skip((self.inner_page - 1) * self.inner_size)
            children_data = list(children_data)
            self.get_user_group(children_data)
            self.add_reactions(children_data)

            item["children"] = []
            if children_data:
                item["children"].extend(children_data)
                item["childrenCount"] = children_count
            else:
                item["childrenCount"] = 0

    def get_user_group(self, data):
        for comment in data:
            username = comment["username"]
            user = self.db["users"].find_one({"username": username}) or {}
            group = user.get("group", ["user"])
            comment["group"] = group

    def add_reactions(self, data):
        for comment in data:
            cid = comment.get("id") or comment.get("_id")
            cid = str(cid)
            reactions = self.db["reactions"].find_one({"comment_id": cid},
                                                      projection={"_id": False, "comment_id": False}) or {}
            for verb, users in reactions.items():
                if users:
                    comment.setdefault("reactions", []).append({"verb": verb, "users": users})

    def get_comment(self, resource_id: int, page: int, size: int, **kwargs) -> dict:
        self.inner_page = kwargs.get("inner_page", 1)
        self.inner_size = kwargs.get("inner_size", 5)
        comment_id = kwargs.get("comment_id")

        condition = {"resource_id": resource_id, "deleted_at": {"$exists": False}, "type": {"$ne": "child"}}
        if comment_id:
            condition.update(_id=ObjectId(comment_id))

        count = self.db["comment"].count_documents(condition)
        data = self.db["comment"].find(condition, self.projection) \
            .sort("_id", pymongo.DESCENDING).limit(size).skip((page - 1) * size)
        data = list(data)
        self.find_children(data)
        self.convert_objectid(data)
        self.get_user_group(data)
        self.add_reactions(data)

        return {
            "data": data,
            "count": count,
            "resource_id": resource_id
        }

    def add_comment(self, captcha: str, captcha_id: int, content: str, resource_id: int,
                    ip: str, username: str, browser: str, parent_comment_id=None) -> dict:
        user_data = self.db["users"].find_one({"username": username})
        # old user is allowed to comment without verification
        if not self.is_old_user(username) and user_data.get("email", {}).get("verified", False) is False:
            return {"status_code": HTTPStatus.TEMPORARY_REDIRECT,
                    "message": "你需要验证邮箱才能评论，请到个人中心进行验证"}
        returned = {"status_code": 0, "message": ""}
        # check if this user is blocked
        reason = self.is_user_blocked(username)
        if reason:
            return {"status_code": HTTPStatus.FORBIDDEN, "message": reason}
        if check_spam(ip, browser, username, content) != 0:
            document = {
                "username": username,
                "ip": ip,
                "date": ts_date(),
                "browser": browser,
                "content": content,
                "resource_id": resource_id
            }
            inserted_id = self.db["spam"].insert_one(document).inserted_id
            document["_id"] = str(inserted_id)
            SpamProcessMongoResource.request_approval(document)
            return {"status_code": HTTPStatus.FORBIDDEN, "message": f"possible spam, reference id: {inserted_id}"}

        user_group = user_data.get("group", [])
        if not user_group:
            # admin don't have to verify code
            verify_result = CaptchaResource().verify_code(captcha, captcha_id)
            if os.getenv("PYTHON_DEV"):
                pass
            elif not verify_result["status"]:
                returned["status_code"] = HTTPStatus.BAD_REQUEST
                returned["message"] = verify_result["message"]
                return returned

        exists = self.db["yyets"].find_one({"data.info.id": resource_id})
        if not exists:
            returned["status_code"] = HTTPStatus.NOT_FOUND
            returned["message"] = "资源不存在"
            return returned

        if parent_comment_id:
            exists = self.db["comment"].find_one({"_id": ObjectId(parent_comment_id)})
            if not exists:
                returned["status_code"] = HTTPStatus.NOT_FOUND
                returned["message"] = "评论不存在"
                return returned

        basic_comment = {
            "username": username,
            "ip": ip,
            "date": ts_date(),
            "browser": browser,
            "content": content,
            "resource_id": resource_id
        }
        if parent_comment_id is None:
            basic_comment["type"] = "parent"
        else:
            basic_comment["type"] = "child"
        # 无论什么评论，都要插入一个新的document
        inserted_id: str = self.db["comment"].insert_one(basic_comment).inserted_id

        if parent_comment_id is not None:
            # 对父评论的子评论，需要给父评论加children id
            self.db["comment"].find_one_and_update({"_id": ObjectId(parent_comment_id)},
                                                   {"$push": {"children": inserted_id}}
                                                   )
            self.db["comment"].find_one_and_update({"_id": ObjectId(inserted_id)},
                                                   {"$set": {"parent_id": ObjectId(parent_comment_id)}}
                                                   )
        returned["status_code"] = HTTPStatus.CREATED
        returned["message"] = "评论成功"

        # notification
        if parent_comment_id:
            # find username

            self.db["notification"].find_one_and_update(
                {"username": exists["username"]},
                {"$push": {"unread": inserted_id}},
                upsert=True
            )
            # send email
            parent_comment = self.db["comment"].find_one({"_id": ObjectId(parent_comment_id)})
            if resource_id == 233:
                link = f"https://yyets.dmesg.app/discuss#{parent_comment_id}"
            else:
                link = f"https://yyets.dmesg.app/resource?id={resource_id}#{parent_comment_id}"
            user_info = self.db["users"].find_one({"username": parent_comment["username"], "email.verified": True})
            if user_info:
                subject = "[人人影视下载分享站] 你的评论有了新的回复"
                pt_content = content.split("</reply>")[-1]
                text = f"你的评论 {parent_comment['content']} 有了新的回复：<br>{pt_content}" \
                       f"<br>你可以<a href='{link}'>点此链接</a>查看<br><br>请勿回复此邮件"
                context = {
                    "username": username,
                    "text": text
                }
                send_mail(user_info["email"]["address"], subject, context)
        return returned

    def delete_comment(self, comment_id):
        current_time = ts_date()
        count = self.db["comment"].update_one({"_id": ObjectId(comment_id), "deleted_at": {"$exists": False}},
                                              {"$set": {"deleted_at": current_time}}).modified_count
        # 找到子评论，全部标记删除
        parent_data = self.db["comment"].find_one({"_id": ObjectId(comment_id)})
        if parent_data:
            child_ids = parent_data.get("children", [])
        else:
            child_ids = []
        count += self.db["comment"].update_many({"_id": {"$in": child_ids}, "deleted_at": {"$exists": False}},
                                                {"$set": {"deleted_at": current_time}}).modified_count

        returned = {"status_code": 0, "message": "", "count": -1}
        if count == 0:
            returned["status_code"] = HTTPStatus.NOT_FOUND
            returned["count"] = 0
        else:
            returned["status_code"] = HTTPStatus.OK
            returned["count"] = count

        return returned


class CommentReactionMongoResource(CommentReactionResource, Mongo):

    def react_comment(self, username, data):
        # {"comment_id":"da23","😊":["user1","user2"]}
        comment_id = data["comment_id"]
        verb = data["verb"]
        method = data["method"]
        if not self.db["comment"].find_one({"_id": ObjectId(comment_id)}):
            return {"status": False, "message": "Where is your comments?", "status_code": HTTPStatus.NOT_FOUND}

        if method == "POST":
            self.db["reactions"].update_one({"comment_id": comment_id},
                                            {
                                                "$addToSet": {verb: username}
                                            },
                                            upsert=True
                                            )
            code = HTTPStatus.CREATED
        elif method == "DELETE":
            self.db["reactions"].update_one({"comment_id": comment_id},
                                            {
                                                "$pull": {verb: username}
                                            }
                                            )
            code = HTTPStatus.ACCEPTED
        else:
            code = HTTPStatus.BAD_REQUEST
        return {"status": True, "message": "success",
                "status_code": code}


class CommentChildMongoResource(CommentChildResource, CommentMongoResource, Mongo):
    def __init__(self):
        super().__init__()
        self.page = 1
        self.size = 5
        self.projection = {"ip": False, "parent_id": False}

    def get_comment(self, parent_id: str, page: int, size: int) -> dict:
        condition = {"parent_id": ObjectId(parent_id), "deleted_at": {"$exists": False}, "type": "child"}

        count = self.db["comment"].count_documents(condition)
        data = self.db["comment"].find(condition, self.projection) \
            .sort("_id", pymongo.DESCENDING).limit(size).skip((page - 1) * size)
        data = list(data)
        self.convert_objectid(data)
        self.get_user_group(data)
        return {
            "data": data,
            "count": count,
        }


class CommentNewestMongoResource(CommentNewestResource, CommentMongoResource, Mongo):
    def __init__(self):
        super().__init__()
        self.page = 1
        self.size = 5
        self.projection = {"ip": False, "parent_id": False, "children": False}
        self.condition: "dict" = {"deleted_at": {"$exists": False}}

    def get_comment(self, page: int, size: int, keyword="") -> dict:
        # ID，时间，用户名，用户组，资源名，资源id
        count = self.db["comment"].count_documents(self.condition)
        data = self.db["comment"].find(self.condition, self.projection) \
            .sort("_id", pymongo.DESCENDING).limit(size).skip((page - 1) * size)
        data = list(data)
        self.convert_objectid(data)
        self.get_user_group(data)
        self.extra_info(data)
        return {
            "data": data,
            "count": count,
        }

    def extra_info(self, data):
        for i in data:
            resource_id = i.get("resource_id", 233)
            res = self.db["yyets"].find_one({"data.info.id": resource_id})
            if res:
                i["cnname"] = res["data"]["info"]["cnname"]


class CommentSearchMongoResource(CommentNewestMongoResource):

    def get_comment(self, page: int, size: int, keyword="") -> dict:
        self.projection.pop("children")
        self.condition.update(content={'$regex': f'.*{keyword}.*', "$options": "i"})
        data = list(self.db["comment"].find(self.condition, self.projection).
                    sort("_id", pymongo.DESCENDING).
                    limit(size).skip((page - 1) * size))
        self.convert_objectid(data)
        self.get_user_group(data)
        self.extra_info(data)
        self.fill_children(data)
        # final step - remove children
        for i in data:
            i.pop("children", None)
        return {
            "data": data,
        }

    def fill_children(self, data):
        for item in data:
            child_id: "list" = item.get("children", [])
            children = list(self.db["comment"].find(
                {"_id": {"$in": child_id}}, self.projection).sort("_id", pymongo.DESCENDING))
            self.convert_objectid(children)
            self.get_user_group(children)
            self.extra_info(children)
            data.extend(children)


class GrafanaQueryMongoResource(GrafanaQueryResource, Mongo):
    def get_grafana_data(self, date_series) -> str:
        condition = {"date": {"$in": date_series}}
        projection = {"_id": False}
        return self.db["metrics"].find(condition, projection)


class MetricsMongoResource(MetricsResource, Mongo):
    def set_metrics(self, metrics_type: str):
        today = time.strftime("%Y-%m-%d", time.localtime())
        self.db['metrics'].update_one(
            {'date': today}, {'$inc': {metrics_type: 1}},
            upsert=True
        )

    def get_metrics(self, from_date: str, to_date: str) -> dict:
        start_int = [int(i) for i in from_date.split("-")]
        end_int = [int(i) for i in to_date.split("-")]
        sdate = date(*start_int)  # start date
        edate = date(*end_int)  # end date
        date_range = [str(sdate + timedelta(days=x)) for x in range((edate - sdate).days + 1)]
        condition = {"date": {"$in": date_range}}
        result = self.db['metrics'].find(condition, {'_id': False}).sort("date", pymongo.DESCENDING)

        return dict(metrics=list(result))


class NameMongoResource(NameResource, Mongo):

    def get_names(self, is_readable: [str, bool]) -> dict:
        if is_readable:
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
            query_cursor = self.db["yyets"].aggregate(aggregation)
        else:
            projection = {'_id': False,
                          'data.info.cnname': True,
                          'data.info.enname': True,
                          'data.info.aliasname': True,
                          'data.info.channel_cn': True,

                          }
            query_cursor = self.db["yyets"].find({}, projection)

        data = []
        for i in query_cursor:
            data.extend(i.values())

        return dict(data=data)


class ResourceMongoResource(ResourceResource, Mongo):
    redis = Redis().r

    def fansub_search(self, class_name: str, kw: str):
        class_ = globals().get(class_name)
        result = class_().search_preview(kw)
        result.pop("class")
        if result:
            return list(result.values())
        else:
            return []

    def get_resource_data(self, resource_id: int, username: str) -> dict:
        data: "dict" = self.db["yyets"].find_one_and_update(
            {"data.info.id": resource_id},
            {'$inc': {'data.info.views': 1}},
            {'_id': False})
        if not data:
            return {}
        if username:
            user_like_data = self.db["users"].find_one({"username": username})
            if user_like_data and resource_id in user_like_data.get("like", []):
                data["is_like"] = True
            else:
                data["is_like"] = False
        return data

    def search_resource(self, keyword: str) -> dict:
        order = os.getenv("ORDER") or 'YYeTsOffline,ZimuxiaOnline,NewzmzOnline,ZhuixinfanOnline,XL720,BD2020'.split(",")
        order.pop(0)
        zimuzu_data = []
        returned = {}

        projection = {'_id': False,
                      'data.info': True,
                      }

        resource_data = self.db["yyets"].find({
            "$or": [
                {"data.info.cnname": {'$regex': f'.*{keyword}.*', "$options": "i"}},
                {"data.info.enname": {'$regex': f'.*{keyword}.*', "$options": "i"}},
                {"data.info.aliasname": {'$regex': f'.*{keyword}.*', "$options": "i"}},
            ]},
            projection
        )

        for item in resource_data:
            item["data"]["info"]["origin"] = "yyets"
            zimuzu_data.append(item["data"]["info"])

        # get comment
        r = CommentSearchMongoResource().get_comment(1, 2 ** 10, keyword)
        c_search = []
        for c in r.get("data", []):
            comment_rid = c["resource_id"]
            d = self.db["yyets"].find_one({"data.info.id": comment_rid}, projection={"data.info": True})
            if d:
                c_search.append(
                    {
                        "username": c["username"],
                        "date": c["date"],
                        "comment": c["content"],
                        "commentID": c["id"],
                        "resourceID": comment_rid,
                        "resourceName": d["data"]["info"]["cnname"],
                        "origin": "comment"
                    }
                )

        if zimuzu_data:
            returned = dict(data=zimuzu_data)
            returned["extra"] = []
        else:
            # only returned when no data found
            extra = []
            with contextlib.suppress(requests.exceptions.RequestException):
                for name in order:
                    extra = self.fansub_search(name, keyword)
                    if extra:
                        break

            returned["data"] = []
            returned["extra"] = extra
        # comment data will always be returned
        returned["comment"] = c_search
        return returned

    def patch_resource(self, new_data: dict):
        rid = new_data["resource_id"]
        new_data.pop("resource_id")
        old_data = self.db["yyets"].find_one(
            {"data.info.id": rid},
        )
        new_data["season_cn"] = self.convert_season(new_data["season_num"])
        # 1. totally empty resource:
        if len(old_data["data"]["list"]) == 0:
            new_data["season_cn"] = self.convert_season(new_data["season_num"])
            old_data["data"]["list"].append(new_data)
        else:
            for season in old_data["data"]["list"]:
                if new_data["season_num"] in [season["season_num"], int(season["season_num"])]:
                    user_format = new_data["formats"][0]
                    for u in new_data["items"][user_format]:
                        season["items"][user_format].append(u)

        self.db["yyets"].find_one_and_replace(
            {"data.info.id": rid},
            old_data
        )

    def add_resource(self, new_data: dict):
        rid = self.get_appropriate_id()
        new_data["data"]["info"]["id"] = rid
        self.db["yyets"].insert_one(new_data)
        return {"status": True, "message": "success", "id": rid}

    def delete_resource(self, data: dict):
        rid = data["resource_id"]
        meta = data.get("meta")
        if meta:
            db_data = self.db["yyets"].find_one({"data.info.id": rid})
            for season in db_data["data"]["list"]:
                for episode in season["items"].values():
                    for v in episode:
                        if v["episode"] == meta["episode"] and v["name"] == meta["name"] and \
                                v["size"] == meta["size"] and v["dateline"] == meta["dateline"]:
                            episode.remove(v)
            # replace it
            self.db["yyets"].find_one_and_replace({"data.info.id": rid}, db_data)

        else:
            self.db["yyets"].delete_one({"data.info.id": rid})

    def get_appropriate_id(self):
        col = self.db["yyets"]
        random_id = random.randint(50000, 80000)
        data = col.find_one({"data.info.id": random_id}, projection={"_id": True})
        if data:
            return self.get_appropriate_id()
        else:
            return random_id

    @staticmethod
    def convert_season(number: [int, str]):
        pass
        if number in (0, "0"):
            return "正片"
        else:
            return f"第{number}季"


class TopMongoResource(TopResource, Mongo):
    projection = {'_id': False, 'data.info': True}

    def get_most(self) -> list:
        projection = {"_id": False, "like": True}
        data = self.db['users'].find({}, projection)
        most_like = {}
        for item in data:
            for _id in item.get("like", []):
                most_like[_id] = most_like.get(_id, 0) + 1
        most = sorted(most_like, key=most_like.get)
        most.reverse()
        most_like_data = self.db["yyets"].find({"data.info.id": {"$in": most}}, self.projection).limit(15)
        return list(most_like_data)

    def get_top_resource(self) -> dict:
        area_dict = dict(ALL={"$regex": ".*"}, US="美国", JP="日本", KR="韩国", UK="英国")
        all_data = {"ALL": "全部"}
        for abbr, area in area_dict.items():
            data = self.db["yyets"].find({"data.info.area": area, "data.info.id": {"$ne": 233}}, self.projection). \
                sort("data.info.views", pymongo.DESCENDING).limit(15)
            all_data[abbr] = list(data)

        all_data["class"] = area_dict
        return all_data


class LikeMongoResource(LikeResource, Mongo):
    projection = {'_id': False, 'data.info': True}

    def get_user_like(self, username: str) -> list:
        like_list = self.db["users"].find_one({"username": username}).get("like", [])
        data = self.db["yyets"].find({"data.info.id": {"$in": like_list}}, self.projection) \
            .sort("data.info.views", pymongo.DESCENDING)
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
        self.db["users"].update_one({"username": username}, {'$set': value})
        return returned


class UserMongoResource(UserResource, Mongo):
    def login_user(self, username: str, password: str, captcha: str, captcha_id: str, ip: str, browser: str) -> dict:
        # verify captcha in the first place.
        redis = Redis().r
        correct_captcha = redis.get(captcha_id)
        if correct_captcha is None:
            return {"status_code": HTTPStatus.BAD_REQUEST, "message": "验证码已过期", "status": False}
        elif correct_captcha.lower() == captcha.lower():
            redis.expire(captcha_id, 0)
        else:
            return {"status_code": HTTPStatus.FORBIDDEN, "message": "验证码错误", "status": False}
        # check user account is locked.

        data = self.db["users"].find_one({"username": username}) or {}
        if data.get("status", {}).get("disable"):
            return {"status_code": HTTPStatus.FORBIDDEN,
                    "status": False,
                    "message": data.get("status", {}).get("reason")}

        returned_value = {"status_code": 0, "message": ""}

        if data:
            # try to login
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
                self.db["users"].insert_one(dict(username=username, password=hash_value,
                                                 date=ts_date(), ip=ip, browser=browser)
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
        return data

    def update_user_last(self, username: str, now_ip: str) -> None:
        self.db["users"].update_one({"username": username},
                                    {"$set": {"lastDate": (ts_date()), "lastIP": now_ip}}
                                    )

    def update_user_info(self, username: str, data: dict) -> dict:
        redis = Redis().r
        valid_fields = ["email"]
        valid_data = {}
        for field in valid_fields:
            if data.get(field):
                valid_data[field] = data[field]

        email_regex = r"@gmail\.com|@outlook\.com|@qq\.com|@163\.com"
        if valid_data.get("email") and not re.findall(email_regex, valid_data.get("email"), re.IGNORECASE):
            return {"status_code": HTTPStatus.BAD_REQUEST, "status": False, "message": "不支持的邮箱"}
        elif valid_data.get("email"):
            # rate limit
            user_email = valid_data.get("email")
            timeout_key = f"timeout-{username}"
            if redis.get(timeout_key):
                return {"status_code": HTTPStatus.TOO_MANY_REQUESTS,
                        "status": False,
                        "message": f"验证次数过多，请于{redis.ttl(timeout_key)}秒后尝试"}

            verify_code = random.randint(10000, 99999)
            valid_data["email"] = {"verified": False, "address": user_email}
            # send email confirm
            subject = "[人人影视下载分享站] 请验证你的邮箱"
            text = f"请输入如下验证码完成你的邮箱认证。验证码有效期为24小时。<br>" \
                   f"如果您未有此请求，请忽略此邮件。<br><br>验证码： {verify_code}"
            context = {
                "username": username,
                "text": text
            }
            send_mail(user_email, subject, context)
            # 发送成功才设置缓存
            redis.set(timeout_key, username, ex=1800)
            redis.hset(user_email, mapping={"code": verify_code, "wrong": 0})
            redis.expire(user_email, 24 * 3600)

        self.db["users"].update_one(
            {"username": username},
            {"$set": valid_data}
        )
        return {"status_code": HTTPStatus.CREATED, "status": True, "message": "邮件已经成功发送"}


class DoubanMongoResource(DoubanResource, Mongo):

    def get_douban_data(self, rid: int) -> dict:
        with contextlib.suppress(Exception):
            return self.find_douban(rid)
        return {"posterData": None}

    def get_douban_image(self, rid: int) -> bytes:
        db_data = self.get_douban_data(rid)
        return db_data["posterData"]

    @retry(IndexError, tries=3, delay=5)
    def find_douban(self, resource_id: int):
        session = requests.Session()
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
        session.headers.update({"User-Agent": ua})

        douban_col = self.db["douban"]
        yyets_col = self.db["yyets"]
        data = douban_col.find_one({"resourceId": resource_id}, {"_id": False, "raw": False})
        if data:
            logging.info("Existing data for %s", resource_id)
            return data

        # data not found, craw from douban
        projection = {"data.info.cnname": True, "data.info.enname": True, "data.info.aliasname": True}
        names = yyets_col.find_one({"data.info.id": resource_id}, projection=projection)
        if names is None:
            return {}
        cname = names["data"]["info"]["cnname"]
        logging.info("cnname for douban is %s", cname)

        search_html = session.get(DOUBAN_SEARCH.format(cname)).text
        logging.info("Analysis search html...length %s", len(search_html))
        soup = BeautifulSoup(search_html, 'html.parser')
        douban_item = soup.find_all("div", class_="content")

        fwd_link = unquote(douban_item[0].a["href"])
        douban_id = re.findall(r"https://movie\.douban\.com/subject/(\d*)/.*", fwd_link)[0]
        final_data = self.get_craw_data(cname, douban_id, resource_id, search_html, session)
        douban_col.insert_one(final_data.copy())
        final_data.pop("raw")
        return final_data

    @staticmethod
    def get_craw_data(cname, douban_id, resource_id, search_html, session):
        detail_link = DOUBAN_DETAIL.format(douban_id)
        detail_html = session.get(detail_link).text
        logging.info("Analysis detail html...%s", detail_link)
        soup = BeautifulSoup(detail_html, 'html.parser')

        directors = [i.text for i in (soup.find_all("a", rel="v:directedBy"))]
        release_date = poster_image_link = rating = year_text = intro = writers = episode_count = episode_duration = ""
        with contextlib.suppress(IndexError):
            episode_duration = soup.find_all("span", property="v:runtime")[0].text
        for i in soup.find_all("span", class_="pl"):
            if i.text == "编剧":
                writers = re.sub(r"\s", "", list(i.next_siblings)[1].text).split("/")
            if i.text == "集数:":
                episode_count = str(i.nextSibling)
            if i.text == "单集片长:" and not episode_duration:
                episode_duration = str(i.nextSibling)
        actors = [i.text for i in soup.find_all("a", rel="v:starring")]
        genre = [i.text for i in soup.find_all("span", property="v:genre")]

        with contextlib.suppress(IndexError):
            release_date = soup.find_all("span", property="v:initialReleaseDate")[0].text
        with contextlib.suppress(IndexError):
            poster_image_link = soup.find_all("div", id="mainpic")[0].a.img["src"]
        with contextlib.suppress(IndexError):
            rating = soup.find_all("strong", class_="ll rating_num")[0].text
        with contextlib.suppress(IndexError):
            year_text = re.sub(r"[()]", "", soup.find_all("span", class_="year")[0].text)
        with contextlib.suppress(IndexError):
            intro = re.sub(r"\s", "", soup.find_all("span", property="v:summary")[0].text)

        final_data = {
            "name": cname,
            "raw": {
                "search_url": DOUBAN_SEARCH.format(cname),
                "detail_url": detail_link,
                "search_html": search_html,
                "detail_html": detail_html
            },
            "doubanId": int(douban_id),
            "doubanLink": detail_link,
            "posterLink": poster_image_link,
            "posterData": session.get(poster_image_link).content,
            "resourceId": resource_id,
            "rating": rating,
            "actors": actors,
            "directors": directors,
            "genre": genre,
            "releaseDate": release_date,
            "episodeCount": episode_count,
            "episodeDuration": episode_duration,
            "writers": writers,
            "year": year_text,
            "introduction": intro
        }
        return final_data


class DoubanReportMongoResource(DoubanReportResource, Mongo):
    def get_error(self) -> dict:
        return dict(data=list(self.db["douban_error"].find(projection={"_id": False})))

    def report_error(self, captcha: str, captcha_id: int, content: str, resource_id: int) -> dict:
        returned = {"status_code": 0, "message": ""}
        verify_result = CaptchaResource().verify_code(captcha, captcha_id)
        if not verify_result["status"]:
            returned["status_code"] = HTTPStatus.BAD_REQUEST
            returned["message"] = verify_result["message"]
            return returned

        count = self.db["douban_error"].update_one(
            {"resource_id": resource_id},
            {"$push": {"content": content}}, upsert=True).matched_count
        return dict(count=count)


class NotificationMongoResource(NotificationResource, Mongo):
    def get_notification(self, username, page, size):
        # .sort("_id", pymongo.DESCENDING).limit(size).skip((page - 1) * size)
        notify = self.db["notification"].find_one({"username": username}, projection={"_id": False})
        if not notify:
            return {
                "username": username,
                "unread_item": [],
                "read_item": [],
                "unread_count": 0,
                "read_count": 0
            }

        # size is shared
        unread = notify.get("unread", [])
        id_list = []
        for item in unread[(page - 1) * size:size * page]:
            id_list.append(item)
        notify["unread_item"] = self.get_content(id_list)

        size = size - len(unread)
        read = notify.get("read", [])
        id_list = []
        for item in read[(page - 1) * size:size * page]:
            id_list.append(item)
        notify["read_item"] = self.get_content(id_list)

        notify.pop("unread", None)
        notify.pop("read", None)
        notify["unread_count"] = len(unread)
        notify["read_count"] = len(read)
        return notify

    def get_content(self, id_list):
        comments = self.db["comment"].find({"_id": {"$in": id_list}},
                                           projection={"ip": False, "parent_id": False}
                                           ).sort("_id", pymongo.DESCENDING)
        comments = list(comments)
        for comment in comments:
            comment["id"] = str(comment["_id"])
            comment.pop("_id")
            reply_to_id = re.findall(r'"(.*)"', comment["content"])[0]
            rtc = self.db["comment"].find_one({"_id": ObjectId(reply_to_id)},
                                              projection={"content": True, "_id": False})
            comment["reply_to_content"] = rtc["content"]

        return comments

    def update_notification(self, username, verb, comment_id):
        if verb == "read":
            v1, v2 = "read", "unread"
        else:
            v1, v2 = "unread", "read"
        self.db["notification"].find_one_and_update(
            {"username": username},
            {
                "$push": {v1: ObjectId(comment_id)},
                "$pull": {v2: ObjectId(comment_id)}
            }
        )

        return {}


class UserEmailMongoResource(UserEmailResource, Mongo):
    def verify_email(self, username, code):
        r = Redis().r
        email = self.db["users"].find_one({"username": username})["email"]["address"]
        verify_data = r.hgetall(email)
        wrong_count = int(verify_data["wrong"])
        MAX = 10
        if wrong_count >= MAX:
            self.db["users"].update_one({"username": username},
                                        {"$set": {"status": {"disable": True, "reason": "verify email crack"}}}
                                        )
            return {"status": False, "status_code": HTTPStatus.FORBIDDEN, "message": "账户已被封锁"}
        correct_code = verify_data["code"]

        if correct_code == code:
            r.expire(email, 0)
            r.expire(f"timeout-{email}", 0)
            self.db["users"].update_one({"username": username},
                                        {"$set": {"email.verified": True}}
                                        )
            return {"status": True, "status_code": HTTPStatus.CREATED, "message": "邮箱已经验证成功"}
        else:
            r.hset(email, "wrong", wrong_count + 1)
            return {"status": False,
                    "status_code": HTTPStatus.FORBIDDEN,
                    "message": f"验证码不正确。你还可以尝试 {MAX - wrong_count} 次"}


class CategoryMongoResource(CategoryResource, Mongo):
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
                douban_data = self.db["douban"].find_one({"resourceId": item["data"]["info"]["id"]},
                                                         projection=projection)
                if douban_data:
                    douban_data["posterData"] = base64.b64encode(douban_data["posterData"]).decode("u8")
                    item["data"]["info"]["douban"] = douban_data
                else:
                    item["data"]["info"]["douban"] = {}
            f.append(item["data"]["info"])
        return dict(data=f, count=count)


class ResourceLatestMongoResource(ResourceLatestResource, Mongo):
    @staticmethod
    def get_latest_resource() -> dict:
        redis = Redis().r
        key = "latest-resource"
        latest = redis.get(key)
        if latest:
            logging.info("Cache hit for latest resource")
            latest = json.loads(latest)
            latest["data"] = latest["data"][:100]
        else:
            logging.warning("Cache miss for latest resource")
            latest = ResourceLatestMongoResource().query_db()
            redis.set(key, json.dumps(latest, ensure_ascii=False))
        return latest

    def query_db(self) -> dict:
        col = self.db["yyets"]
        projection = {"_id": False, "status": False, "info": False}
        episode_data = {}
        for res in tqdm(col.find(projection=projection), total=col.count_documents({})):
            for season in res["data"].get("list", []):
                for item in season["items"].values():
                    for single in item:
                        ts = single["dateline"]
                        res_name = res["data"]["info"]["cnname"]
                        name = "{}-{}".format(res_name, single["name"])
                        size = single["size"]
                        episode_data[name] = {"timestamp": ts, "size": size, "resource_id": res["data"]["info"]["id"],
                                              "res_name": res_name, "date": ts_date(int(ts))}

        sorted_res: list = sorted(episode_data.items(), key=lambda x: x[1]["timestamp"], reverse=True)
        limited_res = dict(sorted_res[:100])
        ok = []
        for k, v in limited_res.items():
            t = {"name": k}
            t.update(v)
            ok.append(t)
        return dict(data=ok)

    def refresh_latest_resource(self):
        redis = Redis().r
        logging.info("Getting new resources...")
        latest = self.query_db()
        redis.set("latest-resource", json.dumps(latest, ensure_ascii=False))
        logging.info("latest-resource data refreshed.")


class SpamProcessMongoResource(Mongo):

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
                        {
                            "text": "approve",
                            "callback_data": f"approve{obj_id}"
                        },
                        {
                            "text": "ban",
                            "callback_data": f"ban{obj_id}"
                        }
                    ]
                ]
            }
        }
        api = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(api, json=data).json()
        logging.info("Telegram response: %s", resp)
