#!/usr/bin/env python3
# coding: utf-8
import contextlib
import logging
import os
import time

import meilisearch

from Mongo import Mongo
from utils import setup_logger

setup_logger()


class SearchEngine(Mongo):
    yyets_projection = {
        "data.info.cnname": 1,
        "data.info.enname": 1,
        "data.info.aliasname": 1,
        "data.info.area": 1,
        "data.info.id": 1,
    }

    douban_projection = {
        "_id": 0,
        "doubanLink": 0,
        "posterLink": 0,
        "posterData": 0,
    }

    comment_projection = {
        "username": 1,
        "date": 1,
        "comment": "$content",
        "_id": 0,
        "commentID": {"$toString": "$_id"},
        "origin": "comment",
        "hasAvatar": {"$toBool": "$avatar"},
        "resourceID": "$resource_id",
        "resourceName": {"$first": "$resource.data.info.cnname"},
        "id": {"$toString": "$_id"},
    }
    comment_lookup = {
        "from": "yyets",
        "localField": "resource_id",
        "foreignField": "data.info.id",
        "as": "resource",
    }

    def __init__(self):
        self.search_client = meilisearch.Client(os.getenv("MEILISEARCH", "http://127.0.0.1:7700"), "masterKey")
        self.yyets_index = self.search_client.index("yyets")
        self.comment_index = self.search_client.index("comment")
        self.douban_index = self.search_client.index("douban")
        super().__init__()

    def __get_yyets(self):
        return self.db["yyets"].aggregate(
            [
                {"$project": self.yyets_projection},
                {"$replaceRoot": {"newRoot": "$data.info"}},
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
        return self.db["douban"].aggregate([{"$project": self.douban_projection}])

    def add_yyets(self):
        logging.info("Adding yyets data to search engine")
        data = list(self.__get_yyets())
        self.yyets_index.add_documents(data)

    def add_comment(self):
        logging.info("Adding comment data to search engine")
        data = list(self.__get_comment())
        self.comment_index.add_documents(data, primary_key="commentID")

    def add_douban(self):
        logging.info("Adding douban data to search engine")
        data = list(self.__get_douban())
        self.douban_index.add_documents(data, primary_key="resourceId")

    def search_yyets(self, keyword: "str"):
        return self.yyets_index.search(keyword, {"matchingStrategy": "all"})

    def search_comment(self, keyword: "str"):
        return self.comment_index.search(keyword, {"matchingStrategy": "all"})

    def search_douban(self, keyword: "str"):
        return self.douban_index.search(keyword, {"matchingStrategy": "all"})

    def run_import(self):
        t0 = time.time()
        self.add_yyets()
        self.add_comment()
        self.add_douban()
        logging.info(f"Imported data to search engine in {time.time() - t0:.2f}s")

    def monitor_yyets(self):
        cursor = self.db.yyets.watch()
        for change in cursor:
            with contextlib.suppress(Exception):
                key = change["documentKey"]["_id"]
                data = self.db.yyets.find_one({"_id": key}, projection=self.yyets_projection)
                index = data["data"]["info"]
                logging.info("Updating yyets index: %s", index["cnname"])
                self.yyets_index.add_documents([index])

    def monitor_douban(self):
        cursor = self.db.douban.watch()
        for change in cursor:
            with contextlib.suppress(Exception):
                key = change["documentKey"]["_id"]
                data = self.db.douban.find_one({"_id": key}, projection=self.douban_projection)
                logging.info("Updating douban index: %s", data["name"])
                self.douban_index.add_documents([data], primary_key="resourceId")

    def monitor_comment(self):
        cursor = self.db.comment.watch()
        for change in cursor:
            with contextlib.suppress(Exception):
                key = change["documentKey"]["_id"]
                data = self.db.comment.aggregate(
                    [
                        {"$match": {"_id": key}},
                        {"$lookup": self.comment_lookup},
                        {"$project": self.comment_projection},
                    ]
                )
                data = list(data)
                logging.info("Updating comment index: %s", data[0]["commentID"])
                self.comment_index.add_documents(data, primary_key="commentID")


if __name__ == "__main__":
    # docker run -it --rm -p 7700:7700 -e MEILI_HTTP_PAYLOAD_SIZE_LIMIT=1073741824 getmeili/meilisearch:v1.0
    a = SearchEngine()
    a.run_import()
