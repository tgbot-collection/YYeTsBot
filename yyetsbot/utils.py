# coding: utf-8
# YYeTsBot - utils.py
# 2019/8/15 20:27

__author__ = 'Benny <benny.think@gmail.com>'

import pathlib

import redis

from config import REDIS

r = redis.StrictRedis(host=REDIS, decode_responses=True)

cookie_file = pathlib.Path(__file__).parent / 'data' / 'cookies.dump'


def save_error_dump(uid, err: str):
    r.set(uid, err)


def get_error_dump(uid) -> str:
    err = r.get(uid)
    r.delete(uid)
    if not err:
        err = ""
    return err


def redis_announcement(content="", op="get"):
    if op == "get":
        return r.get("announcement")
    elif op == "set":
        r.set("announcement", content)
    elif op == "del":
        r.delete("announcement")


def today_request(request_type: str):
    if r.exists("usage"):
        dict_data: dict = r.hgetall("usage")
        dict_data[request_type] = int(dict_data[request_type]) + 1
    else:
        data_format: dict = dict(total=0, invalid=0, answer=0, success=0, fail=0)
        data_format[request_type] += 1
        dict_data = data_format

    r.hset("usage", mapping=dict_data)


def reset_request():
    r.delete("usage")


def show_usage():
    m = "今天我已经服务了{total}次🤓，无效请求{invalid}😆，主人回复{answer}次🤨，成功请求{success}次😝，失败请求{fail}次🤣"
    if r.exists("usage"):
        dict_data: dict = r.hgetall("usage")
    else:
        dict_data: dict = dict(total=0, invalid=0, answer=0, success=0, fail=0)

    return m.format(**dict_data)
