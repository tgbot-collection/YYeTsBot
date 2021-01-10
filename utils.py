# coding: utf-8
# YYeTsBot - utils.py
# 2019/8/15 20:27

__author__ = 'Benny <benny.think@gmail.com>'

import os
import sys
import pickle
import json
import logging
import requests
import redis

from config import AJAX_LOGIN, USERNAME, PASSWORD, REDIS

r = redis.StrictRedis(host=REDIS, decode_responses=True)

cookie_file = os.path.join(os.path.dirname(__file__), 'data', 'cookies.dump')


def save_to_cache(url: str, value: dict) -> None:
    data = json.dumps(value, ensure_ascii=False)
    r.set(url, data, ex=3600 * 12)


def get_from_cache(url: str) -> dict:
    logging.info("Reading data from cache %s", url)
    from html_request import get_detail_page

    data = r.get(url)
    if data:
        logging.info("cache hit")
        return json.loads(data)
    else:
        logging.info("cache miss")
        save_to_cache(url, get_detail_page(url))
        return get_from_cache(url)


def save_error_dump(uid, err: str):
    r.set(uid, err)


def get_error_dump(uid) -> str:
    err = r.get(uid)
    r.delete(uid)
    if not err:
        err = ""
    return err


def save_cookies(requests_cookiejar):
    with open(cookie_file, 'wb') as f:
        pickle.dump(requests_cookiejar, f)


def load_cookies():
    with open(cookie_file, 'rb') as f:
        return pickle.load(f)


def login():
    data = {"account": USERNAME, "password": PASSWORD, "remember": 1}
    logging.info("login in as %s", data)
    r = requests.post(AJAX_LOGIN, data=data)
    resp = r.json()
    if resp.get('status') == 1:
        logging.info("Login success! %s", r.cookies)
        save_cookies(r.cookies)
    else:
        logging.error("Login failed! %s", resp)
        sys.exit(1)
    r.close()
