# coding: utf-8
# YYeTsBot - fansub.py
# 2019/8/15 18:30

__author__ = 'Benny <benny.think@gmail.com>'

import os
import logging
import requests
import pickle
import sys
import json
import hashlib

from bs4 import BeautifulSoup

from config import (YYETS_SEARCH_URL, GET_USER, BASE_URL, SHARE_WEB,
                    SHARE_URL, WORKERS, SHARE_API, USERNAME, PASSWORD,
                    AJAX_LOGIN, REDIS, FANSUB_ORDER, FIX_SEARCH)
import redis

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(filename)s [%(levelname)s]: %(message)s')

session = requests.Session()
ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
session.headers.update({"User-Agent": ua})


class BaseFansub:
    """
    all the subclass should implement three kinds of methods:
    1. online search, contains preview for bot and complete result
    2. offline search (set pass if not applicable)
    3. login and check (set pass if not applicable)
    4. search_result this is critical for bot to draw markup

    """
    label = None
    cookie_file = None

    def __init__(self):
        self.data = None
        self.url = None
        self.redis = redis.StrictRedis(host=REDIS, decode_responses=True)

    @property
    def id(self):
        # implement how to get the unique id for this resource
        return None

    def __get_search_html__(self, kw: str) -> str:
        # return html text of search page
        pass

    def search_preview(self, search_text: str) -> dict:
        # try to retrieve critical information from html
        # this result must return to bot for manual selection
        # {"url1": "name1", "url2": "name2"}
        # don't forget to add this!
        # dict_result["source"] = self.label
        pass

    def search_result(self, resource_url: str) -> dict:
        """
        This will happen when user click one of the button, only by then we can know the resource link
        From the information above, try to get a detail dict structure.
        This method should check cache first if applicable
        This method should set self.link and self.data
        This method should call __execute_online_search
        :param resource_url:
        :return:    {"all": rss_result, "share": share_link, "cnname": cnname}

        """
        pass

    def __execute_search_result__(self) -> dict:
        """
        Do the real search job, without any cache mechanism
        :return:    {"all": rss_result, "share": share_link, "cnname": cnname}
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

    def __get_from_cache__(self, url: str, method_name: str) -> dict:
        logging.info("[%s] Reading data from cache %s", self.label, url)
        data = self.redis.get(url)
        if data:
            logging.info("Cache hit")
            return json.loads(data)
        else:
            logging.info("Cache miss")
            result_method = getattr(self, method_name)
            self.__save_to_cache__(url, result_method())
            return self.__get_from_cache__(url, method_name)

    def __save_to_cache__(self, url: str, value: dict, ex=3600 * 12) -> None:
        data = json.dumps(value, ensure_ascii=False)
        self.redis.set(url, data, ex=ex)


class YYeTsOnline(BaseFansub):
    label = "yyets online"
    cookie_file = os.path.join("data", "cookies.dump")

    @property
    def id(self):
        # implement how to get the unique id for this resource
        rid = self.url.split('/')[-1]
        return rid

    def __get_search_html__(self, kw: str) -> str:
        # don't have to login here
        logging.info("[%s] Searching for %s", self.label, kw)
        r = session.get(YYETS_SEARCH_URL.format(kw=kw))
        r.close()
        return r.text

    def search_preview(self, search_text: str) -> dict:
        html_text = self.__get_search_html__(search_text)
        logging.info('[%s] Parsing html...', self.label)
        soup = BeautifulSoup(html_text, 'html.parser')
        link_list = soup.find_all("div", class_="clearfix search-item")
        dict_result = {}
        for block in link_list:
            name = block.find_all('a')[-1].text
            url = BASE_URL + block.find_all('a')[-1].attrs['href']
            dict_result[url] = name
        dict_result["source"] = self.label
        return dict_result

    def search_result(self, resource_url: str) -> dict:
        self.url = resource_url
        self.data = self.__get_from_cache__(self.url, self.__execute_search_result__.__name__)
        return self.data

    def __execute_search_result__(self) -> dict:
        logging.info("[%s] Loading detail page %s", self.label, self.url)
        share_link, api_res = self.__get_share_page()
        cnname = api_res["data"]["info"]["cnname"]
        self.data = {"all": api_res, "share": share_link, "cnname": cnname}
        return self.data

    def __login_check(self):
        logging.debug("[%s] Checking login status...", self.label)
        if not os.path.exists(self.cookie_file):
            logging.warning("[%s] Cookie file not found", self.label)
            self.__manual_login()

        r = session.get(GET_USER, cookies=self.__load_cookies__())
        if not r.json()['status'] == 1:
            self.__manual_login()

    def __manual_login(self):
        data = {"account": USERNAME, "password": PASSWORD, "remember": 1}
        logging.info("[%s] Login in as %s", self.label, data)
        r = requests.post(AJAX_LOGIN, data=data)
        resp = r.json()
        if resp.get('status') == 1:
            logging.debug("Login success! %s", r.cookies)
            self.__save_cookies__(r.cookies)
        else:
            logging.error("Login failed! %s", resp)
            sys.exit(1)
        r.close()

    def __get_share_page(self):
        self.__login_check()
        rid = self.id

        res = session.post(SHARE_URL, data={"rid": rid}, cookies=self.__load_cookies__()).json()
        share_code = res['data'].split('/')[-1]
        share_url = SHARE_WEB.format(code=share_code)
        logging.info("[%s] Share url is %s", self.label, share_url)

        # get api response
        api_response = session.get(SHARE_API.format(code=share_code)).json()
        return share_url, api_response


class YYeTsOffline(BaseFansub):
    label = "yyets offline"

    def search_preview(self, search_text: str) -> dict:
        # from cloudflare workers
        # no redis cache for now - why? because we may update cloudflare
        logging.info("[%s] Loading offline data from cloudflare KV storage...", self.label)
        index = WORKERS.format(id="index")
        data: dict = requests.get(index).json()

        results = {}
        for name, rid in data.items():
            # make them both lower
            if search_text.lower() in name.lower():
                fake_url = f"http://www.rrys2020.com/resource/{rid}"
                results[fake_url] = name.replace("\n", " ")
        logging.info("[%s] Offline search complete", self.label)
        results["source"] = self.label
        return results

    def search_result(self, resource_url) -> dict:
        self.url = resource_url
        query_url = WORKERS.format(id=self.id)
        # for universal purpose, we return the same structure.
        self.data = {"all": None, "share": query_url, "cnname": None}
        return self.data


class ZimuxiaOnline(BaseFansub):
    label = "zimuxia online"

    @property
    def id(self):
        # implement how to get the unique id for this resource
        rid = self.url.split('/')[-1]
        return rid

    def __get_search_html__(self, kw: str) -> str:
        # don't have to login here
        logging.info("[%s] Searching  for %s", self.label, kw)
        r = session.get(FIX_SEARCH.format(kw=kw))
        r.close()
        return r.text

    def search_preview(self, search_text: str) -> dict:
        html_text = self.__get_search_html__(search_text)
        logging.info('[%s] Parsing html...', self.label)
        soup = BeautifulSoup(html_text, 'html.parser')
        link_list = soup.find_all("h2", class_="post-title")

        dict_result = {}
        for link in link_list:
            # Warning: we can't simple return url here.
            # Telegram bot button callback data must be less than 64bytes.
            # Therefore we use sha1 to hash the url, save to redis.
            url = link.a['href']
            url_hash = hashlib.sha1(url.encode('u8')).hexdigest()
            name = link.a.text
            dict_result[url_hash] = name
            self.redis.set(url_hash, url)
        dict_result["source"] = self.label
        return dict_result

    def search_result(self, url_hash: str) -> dict:
        self.redis.get(url_hash)
        self.url = self.redis.get(url_hash)
        self.data = self.__get_from_cache__(self.url, self.__execute_search_result__.__name__)
        return self.data

    def __execute_search_result__(self) -> dict:
        logging.info("[%s] Loading detail page %s", self.label, self.url)
        cnname, html_text = self.obtain_all_response()
        self.data = {"all": html_text, "share": self.url, "cnname": cnname}
        return self.data

    def obtain_all_response(self) -> (str, str):
        r = session.get(self.url)
        soup = BeautifulSoup(r.text, 'html.parser')
        cnname = soup.title.text.split("|")[0]
        return cnname, dict(html=r.text)


class ZimuxiaOffline(BaseFansub):
    label = "zimuxia offline"

    def search_preview(self, search_text: str) -> dict:
        raise NotImplementedError("Give me some time...")

    def search_result(self, resource_url) -> dict:
        raise NotImplementedError("Give me some time...")


class FansubEntrance(BaseFansub):
    order = FANSUB_ORDER.split(",")
    fansub_class = None

    def search_preview(self, search_text: str) -> dict:
        source = "聪明机智温柔可爱善良的Benny"
        for sub in self.order:
            logging.info("Looping from %s", sub)
            class_ = globals().get(sub)
            result = class_().search_preview(search_text)
            # this result contains source:sub, so we'll pop and add it
            source = result.pop("source")
            if result:
                logging.info("Result hit in %s", sub)
                FansubEntrance.fansub_class = sub
                result["source"] = source
                return result

        return dict(source=source)

    def search_result(self, resource_url: str) -> dict:
        return self.fansub_class().search_result(resource_url)


# we'll check if FANSUB_ORDER is correct. Must put it here, not before.
for fs in FANSUB_ORDER.split(","):
    if globals().get(fs) is None:
        raise NameError(f"FANSUB_ORDER is incorrect! {fs}")
