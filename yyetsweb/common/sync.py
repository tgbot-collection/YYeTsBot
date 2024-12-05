#!/usr/bin/env python3
# coding: utf-8
import contextlib
import logging
import os
import random
import re
import time
from copy import deepcopy

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from databases.base import Mongo
from databases.douban import Douban


class BaseSync:
    def __init__(self):
        self.mongo = Mongo()
        self.yyets = self.mongo.db["yyets"]
        self.sync = self.mongo.db["sync"]
        self.structure = {
            "status": 1,
            "info": "OK",
            "data": {
                "info": {
                    "id": None,
                    "cnname": "",
                    "enname": " ",
                    "aliasname": "",
                    "channel": "",
                    "channel_cn": "",
                    "area": "日本",
                    "show_type": "",
                    "expire": "",
                    "views": 0,
                    "year": [],
                },
                "list": [
                    {
                        "season_num": "101",
                        "season_cn": "单剧",
                        "items": {"MP4": []},
                        "formats": [
                            "MP4",
                        ],
                    }
                ],
            },
        }
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36"
            }
        )

    @staticmethod
    def sleep(times=1):
        time.sleep(random.random() * times)


class Zhuixinfan(BaseSync):
    def run(self):
        zhuixinfan = "http://www.fanxinzhui.com/rr/{}"
        start = (self.sync.find_one({"name": "zhuixinfan"}) or {}).get("resource_id", os.getenv("ZHUIXINFAN_START", 20))
        end = os.getenv("ZHUIXINFAN_END", 2500)
        for i in range(start, end):
            url = zhuixinfan.format(i)
            html = self.session.get(zhuixinfan.format(i)).content.decode("u8")
            self.sleep()
            if html != "资源不存在":
                self.build_data(html, url)

        self.sync.update_one({"name": "zhuixinfan"}, {"$set": {"resource_id": end}})
        logging.info("Zhuixinfan Finished")

    def build_data(self, html, link):
        structure = deepcopy(self.structure)
        if "更新至" in html or re.findall(r"全\d+回", html):
            channel, channel_cn = "tv", "日剧"
        else:
            channel, channel_cn = "movie", "日影"
        soup = BeautifulSoup(html, "html.parser")
        title = soup.find_all("div", class_="resource_title")[0].h2.text
        chn = soup.title.text.split("_")[0]
        eng = title.replace(chn, "").split("(")[0].strip()
        year = int("".join(re.findall(r"\d{4}", title)[-1]).strip())
        structure["data"]["info"]["cnname"] = chn
        structure["data"]["info"]["enname"] = eng
        structure["data"]["info"]["year"] = [year]
        structure["data"]["info"]["source"] = link
        structure["data"]["info"]["channel"] = channel
        structure["data"]["info"]["channel_cn"] = channel_cn

        logging.info("Building data for %s -  %s", chn, link)

        li = soup.find("ul", class_="item_list")
        if li:
            li = li.find_all("li")
        else:
            li = []

        for p in li:
            resource = {
                "itemid": "",
                "episode": p.span.text,
                "name": p.span.nextSibling.text,
                "size": "unknown",
                "yyets_trans": 0,
                "dateline": str(int(time.time())),
                "files": [],
            }

            res = p.find("p", class_="way")
            if res.span is None:
                continue
            links = res.find_all("a")
            for item in links:
                content = item["href"]
                if "ed2k" in content:
                    resource["files"].append({"way": "1", "way_cn": "电驴", "address": content, "passwd": ""})
                elif "magnet" in content:
                    resource["files"].append({"way": "2", "way_cn": "磁力", "address": content, "passwd": ""})
                elif "pan.baidu" in content:
                    baidu_password = res.span.a.nextSibling.nextSibling.text
                    resource["files"].append(
                        {
                            "way": "13",
                            "way_cn": "百度网盘",
                            "address": content,
                            "passwd": baidu_password,
                        }
                    )
                elif "weiyun" in content:
                    resource["files"].append({"way": "14", "way_cn": "微云", "address": content, "passwd": ""})
                else:
                    logging.debug("Unknown link: %s", content)

            structure["data"]["list"][0]["items"]["MP4"].append(resource)

        self.update_yyets(structure)

    def update_yyets(self, data):
        source = data["data"]["info"]["source"]
        exists = self.yyets.find_one({"data.info.source": source})
        already_cond = {"data.info.cnname": data["data"]["info"]["cnname"]}
        already_in = self.yyets.find_one(already_cond)
        if already_in:
            logging.info("Already in old yyets, updating data.info.source: %s", source)
            self.yyets.update_one(already_cond, {"$set": {"data.info.source": source}})
        elif exists:
            logging.info("Updating new data.info.id: %s", source)
            self.yyets.update_one(
                {"data.info.source": source},
                {"$set": {"data.list": data["data"]["list"]}},
            )
        else:
            last_id = 90000
            last = self.yyets.find_one({"data.info.id": {"$gte": last_id}}, sort=[("data.info.id", -1)])
            if last:
                last_id = last["data"]["info"]["id"] + 1
            logging.info("Inserting data.info.id: %s", last_id)
            data["data"]["info"]["id"] = last_id
            self.yyets.insert_one(data.copy())


class YYSub(BaseSync):
    def get_lastest_id(self):
        url = "https://www.yysub.net/resourcelist?channel=&area=&category=&year=&tvstation=&sort=pubdate&page=1"
        html = self.session.get(url).content.decode("u8")
        soup = BeautifulSoup(html, "html.parser")
        x = soup.find("div", class_="resource-showlist has-point")
        return int(x.ul.li.div.a["href"].split("/")[-1])

    def get_channel_cn(self, channel, area):
        if len(area) == 2 and channel == "tv":
            return f"{area[0]}剧"
        if channel == "movie":
            return "电影"
        return ""

    def run(self):
        logging.info("Starting to sync YYSub...")
        structure = deepcopy(self.structure)
        end = self.get_lastest_id() + 1
        # end = 41566
        start = (self.sync.find_one({"name": "yysub"}) or {}).get("resource_id", 41557)
        api = "https://m.yysub.net/api/resource/{}"
        for i in range(start, end):
            resp = self.session.get(api.format(i))
            self.sleep()
            if resp.status_code != 200:
                continue
            data = resp.json()["data"]
            if data.get("cnname"):
                logging.info("Found valid resource: %s - %s", data["cnname"], i)
                channel_cn = self.get_channel_cn(data["channel"], data["area"])
                structure["data"]["info"]["id"] = i
                structure["data"]["info"]["cnname"] = data["cnname"]
                structure["data"]["info"]["enname"] = data["enname"]
                structure["data"]["info"]["aliasname"] = data["aliasname"]
                structure["data"]["info"]["channel"] = data["channel"]
                structure["data"]["info"]["channel_cn"] = data["channel_cn"] or channel_cn
                structure["data"]["info"]["area"] = data["area"]
                structure["data"]["list"] = []
                structure["data"]["info"]["source"] = f"https://www.yysub.net/resource/{i}"
                self.insert_data(structure.copy())

        self.sync.update_one({"name": "yysub"}, {"$set": {"resource_id": end}}, upsert=True)
        logging.info("YYsub Finished")

    def insert_data(self, data):
        rid = data["data"]["info"]["id"]
        self.yyets.update_one({"data.info.id": rid}, {"$set": data}, upsert=True)


def sync_douban():
    douban = Douban()
    session = requests.Session()
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4280.88 Safari/537.36"
    session.headers.update({"User-Agent": ua})

    yyets_data = douban.db["yyets"].aggregate(
        [
            {"$group": {"_id": None, "ids": {"$push": "$data.info.id"}}},
            {"$project": {"_id": 0, "ids": 1}},
        ]
    )
    douban_data = douban.db["douban"].aggregate(
        [
            {"$group": {"_id": None, "ids": {"$push": "$resourceId"}}},
            {"$project": {"_id": 0, "ids": 1}},
        ]
    )

    id1 = next(yyets_data)["ids"]
    id2 = next(douban_data)["ids"]
    rids = list(set(id1).difference(id2))
    rids.remove(233)
    logging.info("resource id complete %d", len(rids))
    for rid in tqdm(rids):
        with contextlib.suppress(Exception):
            d = douban.find_douban(rid)
            logging.info("Processed %s, length %d", rid, len(d))

    logging.info("ALL FINISH!")


if __name__ == "__main__":
    a = Zhuixinfan()
    # a.build_data(open("1.html").read(), "https://www.zhuixinfan.com/resource/1.html")
    a.run()
    # b = YYSub()
    # b.run()
