#!/usr/local/bin/python3
# coding: utf-8

# BagAndDrag - convert_db.py
# 1/12/21 18:24
#

__author__ = "Benny <benny.think@gmail.com>"

# convert to mongodb and con_sqlite

import json
from typing import List

import pymongo
import pymysql

con_mysql = pymysql.Connect(host="127.0.0.1", user="root", password="root", charset="utf8mb4", database="yyets",
                            cursorclass=pymysql.cursors.DictCursor
                            )

mongo_client = pymongo.MongoClient()

SIZE = 2000


def clear_mongodb():
    mongo_client.drop_database("zimuzu")


def mongodb_insert(data: List[dict]):
    db = mongo_client["zimuzu"]
    col = db["yyets"]
    # deserialize data.data
    inserted = []
    for i in data:
        api = json.loads(i["data"])
        views = api["data"]["info"]["views"]
        api["data"]["info"]["views"] = int(views)
        inserted.append(api)
    col.insert_many(inserted)


def main():
    clear_mongodb()

    mysql_cur = con_mysql.cursor()

    mysql_cur.execute("SELECT * FROM resource")

    while True:
        data = mysql_cur.fetchmany(SIZE)
        if data:
            mongodb_insert(data)
        else:
            break


if __name__ == '__main__':
    main()
    con_mysql.close()
    mongo_client.close()
