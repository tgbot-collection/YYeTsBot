#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - convert_db.py
# 2/5/21 13:46
#

__author__ = "Benny <benny.think@gmail.com>"

# convert to mongodb and con_sqlite

import pymongo
import pymysql
import tqdm
import json

from typing import List

con_mysql = pymysql.Connect(host="127.0.0.1", user="root", password="root", charset="utf8mb4", database="zimuxia",
                            cursorclass=pymysql.cursors.DictCursor
                            )

mongo_client = pymongo.MongoClient()

SIZE = 2000


def clear_mongodb():
    mongo_client.drop_database("zimuxia")


def clear_mysql():
    con_mysql.cursor().execute("truncate table resource;")
    con_mysql.commit()


def mysql_insert(data: List[dict]):
    sql = "INSERT INTO resource VALUES(NULL,%(url)s,%(name)s,NULL,NULL,%(data)s)"
    cur = con_mysql.cursor()
    for i in data:
        cur.execute(sql, i)
    con_mysql.commit()


def mongodb_insert(data: List[dict]):
    db = mongo_client["zimuxia"]
    col = db["resource"]
    col.insert_many(data)


def main():
    clear_mongodb()
    clear_mysql()
    with open("result.json") as f:
        data = json.load(f)
    # [{"url": "https://www.zimuxia.cn/portfolio/%e6%888b%e5%8f%8b", "name": "我家的女儿交不到男朋友", "data":""}]
    mysql_insert(data)
    mongodb_insert(data)


if __name__ == '__main__':
    main()
    con_mysql.close()
    mongo_client.close()
