# coding: utf-8
# YYeTsBot - html_request.py
# 2019/8/15 18:30

__author__ = 'Benny <benny.think@gmail.com>'

import os
import logging
import requests
import feedparser
from bs4 import BeautifulSoup

from config import SEARCH_URL, GET_USER, RSS_URL, BASE_URL, SHARE_WEB, SHARE_URL, RESOURCE_SCORE, SHARE_API
from utils import load_cookies, cookie_file, login

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(filename)s [%(levelname)s]: %(message)s')

s = requests.Session()
ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
s.headers.update({"User-Agent": ua})


def get_search_html(kw: str) -> str:
    if not os.path.exists(cookie_file):
        logging.warning("Cookie file not found")
        login()
    if not is_cookie_valid():
        login()
    cookie = load_cookies()
    logging.info("searching for %s", kw)
    r = s.get(SEARCH_URL.format(kw=kw), cookies=cookie)

    r.close()
    return r.text


def get_detail_page(url: str) -> dict:
    logging.info("loading detail page %s", url)
    share_link, api_res = analysis_share_page(url)
    cnname = api_res["data"]["info"]["cnname"]
    logging.info("Share page complete for %s", cnname)

    logging.info("Getting rss...")
    rss_url = RSS_URL.format(id=url.split("/")[-1])
    rss_result = analyse_rss(rss_url)
    logging.info("RSS complete...")

    # get name from here...
    if not rss_result:
        rss_result = api_res

    return {"all": rss_result, "share": share_link, "cnname": cnname}


def analyse_search_html(html: str) -> dict:
    logging.info('Parsing html...')
    soup = BeautifulSoup(html, 'lxml')
    link_list = soup.find_all("div", class_="clearfix search-item")
    list_result = {}
    for block in link_list:
        name = block.find_all('a')[-1].text
        url = BASE_URL + block.find_all('a')[-1].attrs['href']
        list_result[url] = {"name": name, "score": get_score(url.split('/')[-1])}

    return list_result


def analyse_rss(feed_url: str) -> dict:
    # feed parser is meaningless now
    return {}
    # d = feedparser.parse(feed_url)
    # # data['feed']['title']
    # result = {}
    # for item in d['entries']:
    #     download = {
    #         "title": getattr(item, "title", ""),
    #         "ed2k": getattr(item, "ed2k", ""),
    #         "magnet": getattr(item, "magnet", ""),
    #         "pan": getattr(item, "pan", "")}
    #     result[item.guid] = download
    # return result


def analysis_share_page(detail_url: str) -> (str, dict):
    rid = detail_url.split('/')[-1]
    logging.info("rid is %s", rid)

    res = s.post(SHARE_URL, data={"rid": rid}, cookies=load_cookies()).json()
    share_code = res['data'].split('/')[-1]
    logging.info("Share code is %s", share_code)
    share_url = SHARE_WEB.format(code=share_code)
    logging.info("Share url %s", share_url)

    # get api response
    api_response = s.get(SHARE_API.format(code=share_code)).json()
    return share_url, api_response


def get_score(rid: str) -> float:
    # there is actually no meaning in getting score for now
    return 10.0
    # return s.post(RESOURCE_SCORE, data={"rid": rid}).json()['score']


def is_cookie_valid() -> bool:
    cookie = load_cookies()
    r = s.get(GET_USER, cookies=cookie)
    return r.json()['status'] == 1


if __name__ == '__main__':
    __search = get_search_html('轮到你了')
    __search_result = analyse_search_html(__search)
    __chose = "http://www.rrys2020.com/resource/38000"
    __link = get_detail_page(__chose)
    print(__link)
