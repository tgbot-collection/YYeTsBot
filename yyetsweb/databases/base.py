#!/usr/bin/env python3
# coding: utf-8
import json
import logging
import os
import time

import meilisearch

from databases import db, redis_client


class Mongo:
    def __init__(self):
        self.db = db
        super().__init__()

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


class Redis:
    def __init__(self):
        self.r = redis_client
        super().__init__()

    @classmethod
    def cache(cls, timeout: int):
        def func(fun):
            def inner(*args, **kwargs):
                func_name = fun.__name__
                cache_value = cls().r.get(func_name)
                if cache_value:
                    logging.info("Retrieving %s data from redis", func_name)
                    return json.loads(cache_value)
                else:
                    logging.info("Cache expired. Executing %s", func_name)
                    res = fun(*args, **kwargs)
                    cls().r.set(func_name, json.dumps(res), ex=timeout)
                    return res

            return inner

        return func


class SearchEngine(Mongo):
    yyets_projection = {
        "data.info.cnname": 1,
        "data.info.enname": 1,
        "data.info.aliasname": 1,
        "data.info.area": 1,
        "data.info.id": 1,
        "data.info.channel_cn": 1,
        "data.info.channel": 1,
        "_id": {"$toString": "$_id"},
        "origin": "yyets",
    }

    douban_projection = {
        "_id": {"$toString": "$_id"},
        "id": "$resourceId",
        "cnname": {"$first": "$resource.data.info.cnname"},
        "enname": {"$first": "$resource.data.info.enname"},
        "aliasname": {"$first": "$resource.data.info.aliasname"},
        "area": {"$first": "$resource.data.info.area"},
        "channel_cn": {"$first": "$resource.data.info.channel_cn"},
        "channel": {"$first": "$resource.data.info.channel"},
        "origin": "yyets",
        "actors": 1,
        "directors": 1,
        "genres": 1,
        "writers": 1,
        "introduction": 1,
    }

    douban_lookup = {
        "from": "yyets",
        "localField": "resourceId",
        "foreignField": "data.info.id",
        "as": "resource",
    }
    comment_projection = {
        "username": 1,
        "date": 1,
        "comment": "$content",
        "commentID": {"$toString": "$_id"},
        "origin": "comment",
        "hasAvatar": "yes",
        "resourceID": "$resource_id",
        "resourceName": {"$first": "$resource.data.info.cnname"},
        "_id": {"$toString": "$_id"},
    }
    comment_lookup = {
        "from": "yyets",
        "localField": "resource_id",
        "foreignField": "data.info.id",
        "as": "resource",
    }

    def __init__(self):
        self.search_client = meilisearch.Client(os.getenv("MEILISEARCH"), "masterKey")
        self.yyets_index = self.search_client.index("yyets")
        self.comment_index = self.search_client.index("comment")
        self.douban_index = self.search_client.index("douban")
        self.subtitle_index = self.search_client.index("subtitle")
        super().__init__()

    def __del__(self):
        pass

    def __get_yyets(self):
        return self.db["yyets"].aggregate(
            [
                {"$project": self.yyets_projection},
                {
                    "$replaceRoot": {
                        "newRoot": {
                            "$mergeObjects": [
                                {"origin": "yyets"},
                                "$data.info",
                                {"_id": "$_id"},
                            ]
                        }
                    }
                },
            ]
        )

    def __get_comment(self):
        return self.db["comment"].aggregate(
            [
                {"$lookup": self.comment_lookup},
                {"$project": self.comment_projection},
            ]
        )

    def __get_douban(self):
        return self.db["douban"].aggregate(
            [
                {"$lookup": self.douban_lookup},
                {"$project": self.douban_projection},
            ]
        )

    def __get_subtitle(self):
        return self.db["subtitle"].aggregate(
            [
                {
                    "$addFields": {
                        "_id": {"$toString": "$_id"},
                    }
                },
            ]
        )

    def add_yyets(self):
        logging.info("Adding yyets data to search engine")
        data = list(self.__get_yyets())
        self.yyets_index.add_documents(data, primary_key="_id")

    def add_comment(self):
        logging.info("Adding comment data to search engine")
        data = list(self.__get_comment())
        self.comment_index.add_documents(data, primary_key="_id")

    def add_douban(self):
        logging.info("Adding douban data to search engine")
        data = list(self.__get_douban())
        self.douban_index.add_documents(data, primary_key="_id")

    def add_subtitle(self):
        logging.info("Adding subtitle data to search engine")
        data = list(self.__get_subtitle())
        self.subtitle_index.add_documents(data, primary_key="_id")

    def search_yyets(self, keyword: "str"):
        return self.yyets_index.search(keyword, {"matchingStrategy": "all"})["hits"]

    def search_comment(self, keyword: "str"):
        return self.comment_index.search(keyword, {"matchingStrategy": "all"})["hits"]

    def search_douban(self, keyword: "str"):
        return self.douban_index.search(keyword, {"matchingStrategy": "all"})["hits"]

    def search_subtitle(self, keyword: "str"):
        return self.subtitle_index.search(keyword, {"matchingStrategy": "all"})["hits"]

    def run_import(self):
        t0 = time.time()
        self.add_yyets()
        self.add_comment()
        self.add_douban()
        self.add_subtitle()
        logging.info(f"Import data to search engine in {time.time() - t0:.2f}s")

    def __monitor(self, col, fun):
        cursor = self.db[col].watch()
        for change in cursor:
            op_type = change["operationType"]
            _id = change["documentKey"]["_id"]
            search_index = getattr(self, f"{col}_index")
            logging.info("%s %s change stream for %s", col, op_type, _id)

            if op_type == "delete":
                search_index.delete_document(_id)
            else:
                data = fun(_id)
                search_index.add_documents(data, primary_key="_id")

    def monitor_yyets(self):
        def get_data(_id) -> list:
            data = self.db.yyets.find_one({"_id": _id}, projection=self.yyets_projection)["data"]["info"]
            data["_id"] = str(_id)
            data["origin"] = "yyets"
            return [data]

        self.__monitor("yyets", get_data)

    def monitor_douban(self):
        def get_data(_id) -> list:
            data = self.db.douban.aggregate(
                [
                    {"$match": {"_id": _id}},
                    {"$lookup": self.douban_lookup},
                    {"$project": self.douban_projection},
                ]
            )
            return list(data)

        self.__monitor("douban", get_data)

    def monitor_comment(self):
        def get_data(_id) -> list:
            data = self.db.comment.aggregate(
                [
                    {"$match": {"_id": _id}},
                    {"$lookup": self.comment_lookup},
                    {"$project": self.comment_projection},
                ]
            )
            return list(data)

        self.__monitor("comment", get_data)
