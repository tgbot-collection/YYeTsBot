# coding: utf-8
# YYeTsBot - fansub.py
# 2019/8/15 18:30

__author__ = 'Benny <benny.think@gmail.com>'

import contextlib
import hashlib
import json
import logging
import os
import pickle
import re
import sys

import fakeredis
import pymongo
import redis
import requests
from bs4 import BeautifulSoup
from bson.objectid import ObjectId

from config import (BD2020_SEARCH, FANSUB_ORDER, FIX_SEARCH, MONGO,
                    NEWZMZ_RESOURCE, NEWZMZ_SEARCH, REDIS, WORKERS,
                    XL720_SEARCH, ZHUIXINFAN_RESOURCE, ZHUIXINFAN_SEARCH)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(filename)s [%(levelname)s]: %(message)s')

session = requests.Session()
ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
session.headers.update({"User-Agent": ua})

this_module = sys.modules[__name__]


class Redis:
    def __init__(self):
        if os.getenv("DISABLE_REDIS"):
            self.r = fakeredis.FakeStrictRedis()
        else:
            self.r = redis.StrictRedis(host=REDIS, decode_responses=True)

    def __del__(self):
        self.r.close()

    @classmethod
    def preview_cache(cls, timeout=3600 * 24):
        def func(fun):
            def inner(*args, **kwargs):
                search_text = args[1]
                cache_value = cls().r.get(search_text)
                if cache_value:
                    logging.info('🎉 Preview cache hit for %s %s', fun, search_text)
                    return json.loads(cache_value)
                else:
                    logging.info('😱 Preview cache expired. Running %s %s', fun, search_text)
                    res = fun(*args, **kwargs)
                    # if res len is 1, then it means we have no search result at all.
                    if len(res) != 1:
                        json_str = json.dumps(res, ensure_ascii=False)
                        cls().r.set(search_text, json_str, ex=timeout)
                    # save hash->url mapping
                    res_copy = res.copy()
                    res_copy.pop("class")
                    for url_hash, value in res_copy.items():
                        cls().r.hset(url_hash, mapping=value)

                    return res

            return inner

        return func

    @classmethod
    def result_cache(cls, timeout=3600 * 24):
        def func(fun):
            def inner(*args, **kwargs):
                # this method will convert hash to url
                url_or_hash = args[1]
                if re.findall(r"http[s]?://", url_or_hash):
                    # means this is a url
                    url_hash = hashlib.sha1(url_or_hash.encode('u8')).hexdigest()
                    cls().r.hset(url_hash, mapping={"url": url_or_hash})
                else:
                    # this is cache, retrieve real url from redis
                    url_or_hash = cls().r.hget(url_or_hash, "url")
                    if not url_or_hash:
                        url_or_hash = ""

                url = url_or_hash
                del url_or_hash
                cache_value = cls().r.hgetall(url)
                if cache_value:
                    logging.info('🎉 Result cache hit for %s %s', fun, url)
                    return cache_value
                else:
                    logging.info('😱 Result cache expired. Running %s %s', fun, url)
                    new_args = (args[0], url)
                    res = fun(*new_args, **kwargs)
                    # we must have an result for it,
                    cls().r.hset(url, mapping=res)
                    cls().r.expire(url, timeout)

                    return res

            return inner

        return func


class BaseFansub:
    """
    all the subclass should implement three kinds of methods:
    1. online search, contains preview for bot and complete result
    2. login and check (set pass if not applicable)
    3. search_result as this is critical for bot to draw markup

    """
    cookie_file = None

    def __init__(self):
        self.redis = Redis().r

    @property
    def id(self):
        # implement how to get the unique id for this resource
        return None

    def get_html(self, link: str, encoding=None) -> str:
        # return html text of search page
        with session.get(link) as r:
            if encoding is not None:
                r.encoding = encoding
            html = r.text
        logging.info("[%s] [%s] Searching  for %s", self.__class__.__name__, r.status_code, link)
        return html

    def search_preview(self, search_text: str) -> dict:
        # try to retrieve critical information from html
        # this result must return to bot for manual selection
        # {"url1": "name1", "url2": "name2", "source":"yyets"}
        pass

    def search_result(self, url_or_hash: str) -> dict:
        """
        This will happen when user click one of the button, only by then we can know the resource link
        From the information above, try to get a detail dict structure.
        This method should check cache first if applicable
        This method should set self.link and self.data
        :param url_or_hash: url or hash.
        :return:    {"all": dict_result, "share": share_link, "cnname": cnname}

        """
        pass

    def __login_check(self):
        pass

    def __manual_login(self):
        pass

    def __save_cookies__(self, requests_cookiejar):
        with open(self.cookie_file, 'wb') as f:
            pickle.dump(requests_cookiejar, f)

    def __load_cookies__(self):
        with open(self.cookie_file, 'rb') as f:
            return pickle.load(f)


class YYeTsOffline(BaseFansub):

    def __init__(self, db="zimuzu", col="yyets"):
        super().__init__()
        self.mongo = pymongo.MongoClient(host=MONGO)
        self.db = self.mongo[db]
        self.collection = self.db[col]

    @Redis.preview_cache(60)
    def search_preview(self, search_text: str) -> dict:
        logging.info("[%s] Loading offline data from MongoDB...", self.__class__.__name__)

        projection = {'_id': False, 'data.info': True}
        data = self.collection.find({
            "$or": [
                {"data.info.cnname": {"$regex": f".*{search_text}.*", "$options": "i"}},
                {"data.info.enname": {"$regex": f".*{search_text}.*", "$options": "i"}},
                {"data.info.aliasname": {"$regex": f".*{search_text}.*", "$options": "i"}},
            ]},
            projection
        )
        results = {}
        for item in data:
            info = item["data"]["info"]
            url = WORKERS.format(info["id"])
            url_hash = hashlib.sha1(url.encode('u8')).hexdigest()
            all_name = info["cnname"] + info["enname"] + info["aliasname"]
            results[url_hash] = {
                "name": all_name,
                "url": url,
                "class": self.__class__.__name__
            }

        logging.info("[%s] Offline resource search complete", self.__class__.__name__)

        comments = self.db["comment"].find({"content": {"$regex": f".*{search_text}.*", "$options": "i"}})
        for c in comments:
            url = WORKERS + "#{}".format(c["resource_id"], str(c["_id"]))
            url_hash = hashlib.sha1(url.encode('u8')).hexdigest()
            all_name = c["content"]
            results[url_hash] = {
                "name": all_name,
                "url": url,
                "class": self.__class__.__name__
            }
        logging.info("[%s] Offline comment search complete", self.__class__.__name__)

        results["class"] = self.__class__.__name__
        return results

    @Redis.result_cache(10 * 60)
    def search_result(self, resource_url) -> dict:
        # yyets offline

        # resource: https://yyets.dmesg.app/resource.html?id=37089
        # comment: 'https://yyets.dmesg.app/resource.html?id=233#61893ae51e9152e43fa24124'
        if "#" in resource_url:
            cid = resource_url.split("#")[1]
            data: dict = self.db["comment"].find_one(
                {"_id": ObjectId(cid)},
                {'_id': False, "ip": False, "type": False, "children": False, "browser": False}
            )
            share = resource_url
            name = f"{data['username']} 的分享"
            t = "comment"
        else:
            rid = resource_url.split("id=")[1]
            data: dict = self.collection.find_one({"data.info.id": int(rid)}, {'_id': False})
            name = data["data"]["info"]["cnname"]
            share = WORKERS.format(rid)
            t = "resource"

        return {"all": json.dumps(data, ensure_ascii=False, indent=4), "share": share, "cnname": name, "type": t}

    def __del__(self):
        self.mongo.close()


class ZimuxiaOnline(BaseFansub):
    @Redis.preview_cache()
    def search_preview(self, search_text: str) -> dict:
        # zimuxia online
        search_url = FIX_SEARCH.format(kw=search_text)
        html_text = self.get_html(search_url)
        logging.info('[%s] Parsing html...', self.__class__.__name__)
        soup = BeautifulSoup(html_text, 'html.parser')
        link_list = soup.find_all("h2", class_="post-title")

        dict_result = {}
        for link in link_list:
            # TODO wordpress search content and title, some cases it would be troublesome
            url = link.a['href']
            url_hash = hashlib.sha1(url.encode('u8')).hexdigest()
            name = link.a.text
            dict_result[url_hash] = {
                "url": url,
                "name": name,
                "class": self.__class__.__name__
            }
        dict_result["class"] = self.__class__.__name__
        return dict_result

    @Redis.result_cache()
    def search_result(self, resource_url: str) -> dict:
        # zimuxia online
        logging.info("[%s] Loading detail page %s", self.__class__.__name__, resource_url)
        html = self.get_html(resource_url)
        soup = BeautifulSoup(html, 'html.parser')
        cnname = soup.title.text.split("|")[0]
        return {"all": html, "share": resource_url, "cnname": cnname, "type": "resource"}


class ZhuixinfanOnline(BaseFansub):

    @Redis.preview_cache()
    def search_preview(self, search_text: str) -> dict:
        # zhuixinfan online
        search_link = ZHUIXINFAN_SEARCH.format(search_text)
        html_text = self.get_html(search_link)
        logging.info('[%s] Parsing html...', self.__class__.__name__)
        soup = BeautifulSoup(html_text, 'html.parser')
        link_list = soup.find_all("ul", class_="resource_list")

        dict_result = {}
        for li in link_list:
            for link in li:
                with contextlib.suppress(AttributeError):
                    name = link.dd.text
                    url = ZHUIXINFAN_RESOURCE.format(link.dd.a["href"])
                    url_hash = hashlib.sha1(url.encode('u8')).hexdigest()
                    dict_result[url_hash] = {
                        "url": url,
                        "name": name,
                        "class": self.__class__.__name__
                    }
        dict_result["class"] = self.__class__.__name__
        return dict_result

    @Redis.result_cache()
    def search_result(self, url: str) -> dict:
        # zhuixinfan online
        # don't worry, url_hash will become real url
        logging.info("[%s] Loading detail page %s", self.__class__.__name__, url)
        html = self.get_html(url, "utf-8")
        # 解析获得cnname等信息
        soup = BeautifulSoup(html, 'html.parser')
        cnname = soup.title.text.split("_")[0]
        return {"all": html, "share": url, "cnname": cnname, "type": "resource"}


class NewzmzOnline(BaseFansub):

    @Redis.preview_cache()
    def search_preview(self, search_text: str) -> dict:
        # zhuixinfan online
        search_link = NEWZMZ_SEARCH.format(search_text)
        html_text = self.get_html(search_link)
        search_response = json.loads(html_text)

        dict_result = {}
        for item in search_response["data"]:
            url = NEWZMZ_RESOURCE.format(item["link_url"].split("-")[1])
            url_hash = hashlib.sha1(url.encode('u8')).hexdigest()
            dict_result[url_hash] = {
                "url": url,
                "name": item["name"] + item["name_eng"],
                "class": self.__class__.__name__
            }
        dict_result["class"] = self.__class__.__name__
        return dict_result

    @Redis.result_cache()
    def search_result(self, url: str) -> dict:
        logging.info("[%s] Loading detail page %s", self.__class__.__name__, url)
        html = self.get_html(url)
        # 解析获得cnname等信息
        soup = BeautifulSoup(html, 'html.parser')
        cnname = soup.title.text.split("-")[0]
        return {"all": html, "share": url, "cnname": cnname, "type": "resource"}


class BD2020(NewzmzOnline):

    @Redis.preview_cache()
    def search_preview(self, search_text: str) -> dict:
        search_link = BD2020_SEARCH.format(search_text)
        html_text = self.get_html(search_link)
        logging.info('[%s] Parsing html...', self.__class__.__name__)
        soup = BeautifulSoup(html_text, 'html.parser')
        link_list = soup.find_all("li", class_="list-item")

        dict_result = {}
        for item in link_list:
            name = item.div.a.text.strip()
            url = item.div.a["href"]
            url_hash = hashlib.sha1(url.encode('u8')).hexdigest()
            dict_result[url_hash] = {
                "url": url,
                "name": name,
                "class": self.__class__.__name__
            }

        dict_result["class"] = self.__class__.__name__
        return dict_result


class XL720(BD2020):

    @Redis.preview_cache()
    def search_preview(self, search_text: str) -> dict:
        search_link = XL720_SEARCH.format(search_text)
        html_text = self.get_html(search_link)
        logging.info('[%s] Parsing html...', self.__class__.__name__)
        soup = BeautifulSoup(html_text, 'html.parser')

        dict_result = {}
        link_list = soup.find_all("div", class_="post clearfix")
        for item in link_list:
            name = re.sub(r"\s", "", item.h3.a.text.strip())
            url = item.h3.a["href"]
            url_hash = hashlib.sha1(url.encode('u8')).hexdigest()
            dict_result[url_hash] = {
                "url": url,
                "name": name,
                "class": self.__class__.__name__

            }

        dict_result["class"] = self.__class__.__name__
        return dict_result

    @Redis.result_cache()
    def search_result(self, url: str) -> dict:
        logging.info("[%s] Loading detail page %s", self.__class__.__name__, url)
        html = self.get_html(url)
        soup = BeautifulSoup(html, 'html.parser')
        cnname = soup.title.text.split("迅雷下载")[0]
        return {"all": html, "share": url, "cnname": cnname, "type": "resource"}


class FansubEntrance(BaseFansub):
    order = FANSUB_ORDER.split(",")

    def search_preview(self, search_text: str) -> dict:
        class_ = "聪明机智温柔可爱善良的Benny"
        for sub_str in self.order:
            logging.info("Looping from %s", sub_str)
            fc = globals().get(sub_str)
            result = fc().search_preview(search_text)
            # this result contains source:sub, so we'll pop and add it
            class_ = result.pop("class")
            if result:
                logging.info("Result hit in %s %s", sub_str, fc)
                FansubEntrance.fansub_class = fc
                result["class"] = class_
                return result

        return {"class": class_}

    def search_result(self, resource_url_hash: str) -> dict:
        # entrance
        cache_data = self.redis.hgetall(resource_url_hash)
        resource_url = cache_data["url"]
        class_name = cache_data["class"]
        fc = globals().get(class_name)
        return fc().search_result(resource_url)


# we'll check if FANSUB_ORDER is correct. Must put it here, not before.
for fs in FANSUB_ORDER.split(","):
    if globals().get(fs) is None:
        raise NameError(f"FANSUB_ORDER is incorrect! {fs}")


# Commands can use latin letters, numbers and underscores. yyets_offline
def class_to_tg(sub_class: str):
    trans = {"Online": "_online", "Offline": "_offline"}

    for upper, lower in trans.items():
        sub_class = sub_class.replace(upper, lower)

    return sub_class.lower()


for sub_name in globals().copy():
    if sub_name.endswith("Offline") or sub_name.endswith("Online"):
        cmd_name = class_to_tg(sub_name)
        m = getattr(this_module, sub_name)
        logging.info("Mapping %s to %s", cmd_name, m)
        vars()[cmd_name] = m

if __name__ == '__main__':
    sub = ZimuxiaOnline()
    search = sub.search_preview("最爱")
    print(search)
    uh = "4bcd33af9be2fba0060c388e984c7a2509e7e654"
    result = sub.search_result(uh)
    print(json.dumps(result, ensure_ascii=False))
