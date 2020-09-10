# coding: utf-8
# YYeTsBot - utils.py
# 2019/8/15 20:27

__author__ = 'Benny <benny.think@gmail.com>'

import dbm
import os
import pickle
import json
import logging
import requests

from config import AJAX_LOGIN, USERNAME, PASSWORD

db_path = os.path.join(os.path.dirname(__file__), 'data', 'yyets.dbm')
db = dbm.open(db_path, 'c')
cookie_file = os.path.join(os.path.dirname(__file__), 'data', 'cookies.dump')


def batch_upsert(data: dict) -> None:
    for k in data:
        upsert(k, data[k])


def upsert(key: str, value: dict) -> None:
    db[key] = json.dumps(value, ensure_ascii=False)


def get(key: str) -> dict:
    return json.loads(db.get(key, '{}'), encoding='utf-8')


def delete(key: str) -> None:
    del db[key]


def save_dump(err):
    f = open(os.path.join(os.path.dirname(__file__), 'data', 'error.txt'), 'w', encoding='u8')
    f.write(err)
    f.close()


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
    r.close()
