#!/usr/local/bin/python3
# coding: utf-8

# BagAndDrag - bag.py
# 1/10/21 15:29
#

__author__ = "Benny <benny.think@gmail.com>"

import contextlib
import json
import logging
import os
import pickle
import sys
import time
import traceback

import pymysql
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(filename)s [%(levelname)s]: %(message)s')

COOKIES = os.path.join(os.path.dirname(__file__), 'cookies.dump')
USERNAME = os.environ.get("USERNAME") or "321"
PASSWORD = os.environ.get("PASSWORD") or "xa31sge"

GET_USER = "http://www.rrys2020.com/user/login/getCurUserTopInfo"
AJAX_LOGIN = "http://www.rrys2020.com/User/Login/ajaxLogin"
RESOURCE = "http://www.rrys2020.com/resource/{id}"
SHARE_URL = "http://www.rrys2020.com/resource/ushare"
# http://got002.com/api/v1/static/resource/detail?code=9YxN91
API_DATA = "http://got002.com/api/v1/static/resource/detail?code={code}"
ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"


def save_cookies(requests_cookiejar):
    with open(COOKIES, 'wb') as f:
        pickle.dump(requests_cookiejar, f)


def load_cookies():
    with contextlib.suppress(Exception):
        with open(COOKIES, 'rb') as f:
            return pickle.load(f)


def login():
    data = {"account": USERNAME, "password": PASSWORD, "remember": 1}
    logging.info("login in as %s", data)
    r = requests.post(AJAX_LOGIN, data=data, headers={"User-Agent": ua})
    resp = r.json()
    if resp.get('status') == 1:
        logging.info("Login success! %s", r.cookies)
        save_cookies(r.cookies)
    else:
        logging.error("Login failed! %s", resp)
        sys.exit(1)
    r.close()


def is_cookie_valid() -> bool:
    cookie = load_cookies()
    r = requests.get(GET_USER, cookies=cookie, headers={"User-Agent": ua})
    return r.json()['status'] == 1


def insert_db(data: dict):
    try:
        # INSERT INTO resource VALUE(id,url,name,expire,data)
        sql = "INSERT INTO resource VALUE(%s,%s,%s,%s,%s,%s)"
        con = pymysql.Connect(host="127.0.0.1", user="root", password="root", database="yyets", charset="utf8mb4")
        cur = con.cursor()
        info = data["data"]["info"]
        id = info["id"]
        url = RESOURCE.format(id=id)
        name = '{cnname}\n{enname}\n{alias}'.format(cnname=info["cnname"], enname=info["enname"],
                                                    alias=info["aliasname"])
        expire = info["expire"]
        date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(expire)))
        d = json.dumps(data, ensure_ascii=False, indent=2)

        cur.execute(sql, (id, url, name, expire, date, d))
        con.commit()
    except Exception as e:
        logging.error("insert error %s", e)
        logging.error(traceback.format_exc())


def insert_error(rid, tb):
    logging.warning("Logging error into database %s", rid)
    sql = "INSERT INTO failure VALUE (%s,%s)"
    con = pymysql.Connect(host="127.0.0.1", user="root", password="root", database="yyets", charset="utf8mb4")
    cur = con.cursor()
    cur.execute(sql, (rid, tb))
    con.commit()


def __load_sample():
    with open("sample.json") as f:
        return json.load(f)


if __name__ == '__main__':
    d = __load_sample()
    insert_db(d)
    insert_error(2331, "eeeeee")
