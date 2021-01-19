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

from bs4 import BeautifulSoup

from config import (SEARCH_URL, GET_USER, BASE_URL, SHARE_WEB,
                    SHARE_URL, WORKERS, SHARE_API, USERNAME, PASSWORD,
                    AJAX_LOGIN, REDIS)
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

    def online_search_preview(self, search_text: str) -> dict:
        # try to retrieve critical information from html
        # this result must return to bot for manual selection
        # {"url1": "name1", "url2": "name2"}
        pass

    def online_search_result(self, resource_url: str) -> dict:
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

    def __execute_online_search_result__(self) -> dict:
        """
        Do the real search job, without any cache mechanism
        :return:    {"all": rss_result, "share": share_link, "cnname": cnname}
        """
        pass

    def offline_search_preview(self, search_text: str) -> dict:
        # this result must return to bot for manual selection
        # the same as online
        pass

    def offline_search_result(self, resource_url) -> dict:
        """
        Same as online_search_result
        :param resource_url:
        :return:
        """
        pass

    def __execute_offline_search_result(self) -> dict:
        """
        Do the search job, without any cache mechanism
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
        logging.info("Reading %s data from cache %s", self.label, url)
        data = self.redis.get(url)
        if data:
            logging.info("Cache hit")
            return json.loads(data)
        else:
            logging.info("Cache miss")
            result_method = getattr(self, method_name)
            self.__save_to_cache(url, result_method())
            return self.__get_from_cache__(url, method_name)

    def __save_to_cache(self, url: str, value: dict, ex=3600 * 12) -> None:
        data = json.dumps(value, ensure_ascii=False)
        self.redis.set(url, data, ex=ex)


class YYeTs(BaseFansub):
    label = "yyets"
    cookie_file = os.path.join("data", "cookies.dump")

    @property
    def id(self):
        # implement how to get the unique id for this resource
        rid = self.url.split('/')[-1]
        return rid

    def __get_search_html__(self, kw: str) -> str:
        # don't have to login here
        logging.info("Searching for %s", kw)
        r = session.get(SEARCH_URL.format(kw=kw))
        r.close()
        return r.text

    def online_search_preview(self, search_text: str) -> dict:
        html_text = self.__get_search_html__(search_text)
        logging.info('Parsing html...')
        soup = BeautifulSoup(html_text, 'lxml')
        link_list = soup.find_all("div", class_="clearfix search-item")
        dict_result = {}
        for block in link_list:
            name = block.find_all('a')[-1].text
            url = BASE_URL + block.find_all('a')[-1].attrs['href']
            dict_result[url] = name

        return dict_result

    def online_search_result(self, resource_url: str) -> dict:
        self.url = resource_url
        self.data = self.__get_from_cache__(self.url, self.__execute_online_search_result__.__name__)
        return self.data

    def __execute_online_search_result__(self) -> dict:
        logging.info("Loading detail page %s", self.url)
        share_link, api_res = self.__get_share_page()
        cnname = api_res["data"]["info"]["cnname"]
        self.data = {"all": api_res, "share": share_link, "cnname": cnname}
        return self.data

    def offline_search_preview(self, search_text: str) -> dict:
        # from cloudflare workers
        # no redis cache for now
        logging.info("Loading data from cfkv...")
        index = WORKERS.format(id="index")
        data: dict = requests.get(index).json()
        logging.info("Loading complete, searching now...")

        results = {}
        for name, rid in data.items():
            if search_text in name:
                fake_url = f"http://www.rrys2020.com/resource/{rid}"
                results[fake_url] = name.replace("\n", " ")
        logging.info("Search complete")
        return results

    def offline_search_result(self, resource_url) -> dict:
        self.url = resource_url
        query_url = WORKERS.format(id=self.id)
        self.data = {"all": None, "share": query_url, "cnname": None}
        return self.data

    def __login_check(self):
        logging.info("Checking login status...")
        if not os.path.exists(self.cookie_file):
            logging.warning("Cookie file not found")
            self.__manual_login()

        r = session.get(GET_USER, cookies=self.__load_cookies__())
        if not r.json()['status'] == 1:
            self.__manual_login()

    def __manual_login(self):
        data = {"account": USERNAME, "password": PASSWORD, "remember": 1}
        logging.info("Login in as %s", data)
        r = requests.post(AJAX_LOGIN, data=data)
        resp = r.json()
        if resp.get('status') == 1:
            logging.info("Login success! %s", r.cookies)
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
        logging.info("Share url is %s", share_url)

        # get api response
        api_response = session.get(SHARE_API.format(code=share_code)).json()
        return share_url, api_response


if __name__ == '__main__':
    y = YYeTs()
