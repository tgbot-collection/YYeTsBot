#!/usr/bin/env python3
# coding: utf-8
import logging
import os
import time

import meilisearch

from Mongo import Mongo
from utils import setup_logger

# YYeTsBot - fulltext.py
# 2023-03-08  19:35


setup_logger()


class SearchEngine(Mongo):
    def __init__(self):
        self.search_client = meilisearch.Client(
            os.getenv("MEILISEARCH", "http://127.0.0.1:7700"), "masterKey"
        )
        self.yyets_index = self.search_client.index("yyets")
        self.comment_index = self.search_client.index("comment")
        self.douban_index = self.search_client.index("douban")
        super().__init__()

    def __get_yyets(self):
        return self.db["yyets"].aggregate(
            [
                {
                    "$project": {
                        "data.info.cnname": 1,
                        "data.info.enname": 1,
                        "data.info.aliasname": 1,
                        "data.info.area": 1,
                        "data.info.id": 1,
                    }
                },
                {"$replaceRoot": {"newRoot": "$data.info"}},
            ]
        )

    def __get_comment(self):
        return self.db["comment"].aggregate(
            [
                {
                    "$lookup": {
                        "from": "yyets",
                        "localField": "resource_id",
                        "foreignField": "data.info.id",
                        "as": "resource",
                    }
                },
                {
                    "$project": {
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
                },
            ]
        )

    def __get_douban(self):
        return self.db["douban"].aggregate(
            [
                {
                    "$project": {
                        "_id": 0,
                        "doubanLink": 0,
                        "posterLink": 0,
                        "posterData": 0,
                    }
                }
            ]
        )

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


if __name__ == "__main__":
    # docker run -it --rm -p 7700:7700 -e MEILI_HTTP_PAYLOAD_SIZE_LIMIT=1073741824 getmeili/meilisearch:v1.0
    a = SearchEngine()
    a.run_import()
