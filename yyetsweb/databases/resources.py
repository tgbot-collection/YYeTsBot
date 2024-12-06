#!/usr/bin/env python3
# coding: utf-8
import json
import logging
import os
import random

import pymongo
import zhconv
from tqdm import tqdm

from common.utils import hide_phone, ts_date
from databases.base import Mongo, Redis, SearchEngine
from databases.comment import CommentSearch


class SubtitleDownload(Mongo):
    def add_download(self, _id):
        self.db["subtitle"].find_one_and_update({"id": _id}, {"$inc": {"downloads": 1}})


class Resource(SearchEngine):
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
            {"$inc": {"data.info.views": 1}},
            {"_id": False},
        )
        if not data:
            return {}
        if username:
            user_like_data = self.db["users"].find_one({"username": username})
            if user_like_data and resource_id in user_like_data.get("like", []):
                data["is_like"] = True
            else:
                data["is_like"] = False
        return data

    def search_resource(self, keyword: str, search_type: "str") -> dict:
        # search_type: default,subtitle,douban,comment
        if os.getenv("MEILISEARCH"):
            return self.meili_search(keyword, search_type)
        else:
            return self.mongodb_search(keyword, search_type)

    def meili_search(self, keyword: "str", search_type: "str") -> dict:
        resource_data, subtitle_data, comment_data = [], [], []

        if search_type == "resource":
            resource_data = self.search_yyets(keyword)

        if search_type == "comment":
            comment_data = hide_phone(self.search_comment(keyword))

        if search_type == "subtitle":
            # TODO: just get data from mongodb for now.
            subtitle_data = list(
                self.db["subtitle"].find(
                    {
                        "$or": [
                            {"cnname": {"$regex": f".*{keyword}.*", "$options": "i"}},
                            {"enname": {"$regex": f".*{keyword}.*", "$options": "i"}},
                        ]
                    },
                    {"_id": False},
                )
            )

        if search_type == "default":
            resource_data = self.search_yyets(keyword)
            subtitle_data = self.search_subtitle(keyword)
            comment_data = hide_phone(self.search_comment(keyword))
        return {
            "resource": resource_data,
            "subtitle": subtitle_data,
            "comment": comment_data,
        }

    def mongodb_search(self, keyword: str, search_type: str) -> dict:
        # search_type: default,resource,subtitle,comment default is everything
        keyword = zhconv.convert(keyword, "zh-hans")
        resource_data, subtitle_data, comment_data = [], [], []

        def search_resource():
            data = self.db["yyets"].find(
                {
                    "$or": [
                        {
                            "data.info.cnname": {
                                "$regex": f".*{keyword}.*",
                                "$options": "i",
                            }
                        },
                        {
                            "data.info.enname": {
                                "$regex": f".*{keyword}.*",
                                "$options": "i",
                            }
                        },
                        {
                            "data.info.aliasname": {
                                "$regex": f".*{keyword}.*",
                                "$options": "i",
                            }
                        },
                    ]
                },
                {"_id": False, "data.info": True},
            )

            for item in data:
                item["data"]["info"]["origin"] = "yyets"
                resource_data.append(item["data"]["info"])

        def search_subtitle():
            subdata = self.db["subtitle"].find(
                {
                    "$or": [
                        {"cnname": {"$regex": f".*{keyword}.*", "$options": "i"}},
                        {"enname": {"$regex": f".*{keyword}.*", "$options": "i"}},
                    ]
                },
                {"_id": False},
            )
            subtitle_data.extend(list(subdata))

        def search_comment():
            comments = CommentSearch().get_comment(1, 2**10, keyword)
            hide_phone(comments.get("data", []))
            for c in comments.get("data", []):
                comment_rid = c["resource_id"]
                res = self.db["yyets"].find_one({"data.info.id": comment_rid}, projection={"data.info": True})
                if res:
                    comment_data.append(
                        {
                            "username": c["username"],
                            "date": c["date"],
                            "comment": c["content"],
                            "commentID": c["id"],
                            "resourceID": comment_rid,
                            "resourceName": res["data"]["info"]["cnname"],
                            "origin": "comment",
                            "hasAvatar": c["hasAvatar"],
                            "hash": c.get("hash"),
                        }
                    )

        if search_type == "resource":
            search_resource()

        if search_type == "comment":
            search_comment()

        if search_type == "subtitle":
            search_subtitle()
        if search_type == "default":
            search_resource()
            search_comment()
            search_subtitle()

        return {
            "resource": resource_data,
            "subtitle": subtitle_data,
            "comment": comment_data,
        }

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
                if new_data["season_num"] in [
                    season["season_num"],
                    int(season["season_num"]),
                ]:
                    user_format = new_data["formats"][0]
                    for u in new_data["items"][user_format]:
                        season["items"][user_format].append(u)

        self.db["yyets"].find_one_and_replace({"data.info.id": rid}, old_data)

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
                        if (
                            v["episode"] == meta["episode"]
                            and v["name"] == meta["name"]
                            and v["size"] == meta["size"]
                            and v["dateline"] == meta["dateline"]
                        ):
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
        if number in (0, "0"):
            return "正片"
        else:
            return f"第{number}季"


class Top(Mongo):
    projection = {"_id": False, "data.info": True}

    def get_most(self) -> list:
        projection = {"_id": False, "like": True}
        data = self.db["users"].find({}, projection)
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
            data = (
                self.db["yyets"]
                .find(
                    {"data.info.area": area, "data.info.id": {"$ne": 233}},
                    self.projection,
                )
                .sort("data.info.views", pymongo.DESCENDING)
                .limit(15)
            )
            all_data[abbr] = list(data)

        all_data["class"] = area_dict
        return all_data


class ResourceLatest(Mongo, Redis):
    def get_latest_resource(self) -> dict:
        key = "latest-resource"
        latest = self.r.get(key)
        if latest:
            logging.info("Cache hit for latest resource")
            latest = json.loads(latest)
            latest["data"] = latest["data"][:100]
        else:
            logging.warning("Cache miss for latest resource")
            latest = ResourceLatest().query_db()
            self.r.set(key, json.dumps(latest, ensure_ascii=False))
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
                        episode_data[name] = {
                            "timestamp": ts,
                            "size": size,
                            "resource_id": res["data"]["info"]["id"],
                            "res_name": res_name,
                            "date": ts_date(int(ts)),
                        }

        sorted_res: list = sorted(episode_data.items(), key=lambda x: x[1]["timestamp"], reverse=True)
        limited_res = dict(sorted_res[:100])
        ok = []
        for k, v in limited_res.items():
            t = {"name": k}
            t.update(v)
            ok.append(t)
        return dict(data=ok)

    def refresh_latest_resource(self):
        logging.info("Getting new resources...")
        latest = self.query_db()
        self.r.set("latest-resource", json.dumps(latest, ensure_ascii=False))
        logging.info("latest-resource data refreshed.")


class Name(Mongo):
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
                                "$data.info.aliasname",
                            ]
                        },
                        "_id": False,
                    }
                }
            ]
            query_cursor = self.db["yyets"].aggregate(aggregation)
        else:
            projection = {
                "_id": False,
                "data.info.cnname": True,
                "data.info.enname": True,
                "data.info.aliasname": True,
                "data.info.channel_cn": True,
            }
            query_cursor = self.db["yyets"].find({}, projection)

        data = []
        for i in query_cursor:
            data.extend(i.values())

        return dict(data=data)
