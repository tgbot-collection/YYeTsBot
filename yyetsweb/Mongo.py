#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - mongodb.py
# 6/16/21 21:18
#

__author__ = "Benny <benny.think@gmail.com>"

import contextlib

import pymongo
import os
import time
from http import HTTPStatus
from datetime import timedelta, date
from bson.objectid import ObjectId

import requests
from passlib.handlers.pbkdf2 import pbkdf2_sha256

from database import (AnnouncementResource, BlacklistResource, CommentResource, ResourceResource,
                      GrafanaQueryResource, MetricsResource, NameResource, OtherResource,
                      TopResource, UserLikeResource, UserResource, CaptchaResource, Redis, CommentChildResource)
from utils import ts_date
from fansub import ZhuixinfanOnline, ZimuxiaOnline, NewzmzOnline, CK180Online

mongo_host = os.getenv("mongo") or "localhost"


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


class AnnouncementMongoResource(AnnouncementResource, Mongo):
    def get_announcement(self, page: int, size: int) -> dict:
        condition = {}
        count = self.db["announcement"].count_documents(condition)
        data = self.db["announcement"].find(condition, projection={"_id": False, "ip": False}) \
            .sort("_id", pymongo.DESCENDING).limit(size).skip((page - 1) * size)

        return {
            "data": list(data),
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

            item["children"] = []
            if children_data:
                item["children"].extend(children_data)
                item["childrenCount"] = children_count
            else:
                item["childrenCount"] = 0

    def get_user_group(self, data):
        for comment in data:
            username = comment["username"]
            user = self.db["users"].find_one({"username": username})
            group = user.get("group", ["user"])
            comment["group"] = group

    def get_comment(self, resource_id: int, page: int, size: int, **kwargs) -> dict:
        self.inner_page = kwargs.get("inner_page", 1)
        self.inner_size = kwargs.get("inner_size", 5)
        condition = {"resource_id": resource_id, "deleted_at": {"$exists": False}, "type": {"$ne": "child"}}
        if resource_id == -1:
            condition.pop("resource_id")

        count = self.db["comment"].count_documents(condition)
        data = self.db["comment"].find(condition, self.projection) \
            .sort("_id", pymongo.DESCENDING).limit(size).skip((page - 1) * size)
        data = list(data)
        self.find_children(data)
        self.convert_objectid(data)
        self.get_user_group(data)
        return {
            "data": data,
            "count": count,
            "resource_id": resource_id
        }

    def add_comment(self, captcha: str, captcha_id: int, content: str, resource_id: int,
                    ip: str, username: str, browser: str, parent_comment_id=None) -> dict:
        returned = {"status_code": 0, "message": ""}
        verify_result = CaptchaResource().verify_code(captcha, captcha_id)
        verify_result["status"] = 1
        if not verify_result["status"]:
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
        data = self.db["yyets"].find_one_and_update(
            {"data.info.id": resource_id},
            {'$inc': {'data.info.views': 1}},
            {'_id': False})

        if username:
            user_like_data = self.db["users"].find_one({"username": username})
            if user_like_data and resource_id in user_like_data.get("like", []):
                data["is_like"] = True
            else:
                data["is_like"] = False
        return data

    def search_resource(self, keyword: str) -> dict:
        projection = {'_id': False,
                      'data.info': True,
                      }

        data = self.db["yyets"].find({
            "$or": [
                {"data.info.cnname": {'$regex': f'.*{keyword}.*', "$options": "-i"}},
                {"data.info.enname": {'$regex': f'.*{keyword}.*', "$options": "-i"}},
                {"data.info.aliasname": {'$regex': f'.*{keyword}.*', "$options": "-i"}},
            ]},
            projection
        )
        data = list(data)
        returned = {}
        if data:
            returned = dict(data=data)
            returned["extra"] = []
        else:
            extra = self.fansub_search(ZimuxiaOnline.__name__, keyword) or \
                    self.fansub_search(NewzmzOnline.__name__, keyword) or \
                    self.fansub_search(ZhuixinfanOnline.__name__, keyword) or \
                    self.fansub_search(CK180Online.__name__, keyword)

            returned["data"] = []
            returned["extra"] = extra

        return returned


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
        all_data = {}
        for abbr, area in area_dict.items():
            data = self.db["yyets"].find({"data.info.area": area, "data.info.id": {"$ne": 233}}, self.projection). \
                sort("data.info.views", pymongo.DESCENDING).limit(15)
            all_data[abbr] = list(data)

        area_dict["ALL"] = "全部"
        all_data["class"] = area_dict
        return all_data


class UserLikeMongoResource(UserLikeResource, Mongo):
    projection = {'_id': False, 'data.info': True}

    def get_user_like(self, username: str) -> list:
        like_list = self.db["users"].find_one({"username": username}).get("like", [])
        data = self.db["yyets"].find({"data.info.id": {"$in": like_list}}, self.projection) \
            .sort("data.info.views", pymongo.DESCENDING)
        return list(data)


class UserMongoResource(UserResource, Mongo):
    def login_user(self, username: str, password: str, ip: str, browser: str) -> dict:
        data = self.db["users"].find_one({"username": username})
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
            hash_value = pbkdf2_sha256.hash(password)
            try:
                self.db["users"].insert_one(dict(username=username, password=hash_value,
                                                 date=ts_date(), ip=ip, browser=browser)
                                            )
                returned_value["status_code"] = HTTPStatus.CREATED

            except Exception as e:
                returned_value["status_code"] = HTTPStatus.INTERNAL_SERVER_ERROR
                returned_value["message"] = str(e)

        return returned_value

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

    def get_user_info(self, username: str) -> dict:
        projection = {"_id": False, "password": False}
        data = self.db["users"].find_one({"username": username}, projection)
        return data

    def update_user_last(self, username: str, now_ip: str) -> None:
        self.db["users"].update_one({"username": username},
                                    {"$set": {"lastDate": (ts_date()), "lastIP": now_ip}}
                                    )
