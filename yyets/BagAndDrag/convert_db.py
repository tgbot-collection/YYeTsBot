#!/usr/local/bin/python3
# coding: utf-8

# BagAndDrag - convert_db.py
# 1/12/21 18:24
#

__author__ = "Benny <benny.think@gmail.com>"

# convert to mongodb and con_sqlite

import json
import sqlite3
from typing import List

import pymongo
import pymysql
import tqdm

con_mysql = pymysql.Connect(host="127.0.0.1", user="root", password="root", charset="utf8mb4", database="yyets",
                            cursorclass=pymysql.cursors.DictCursor
                            )

mongo_client = pymongo.MongoClient()
con_sqlite = sqlite3.connect("yyets.db")

SIZE = 2000


def create_sqlite_database():
    sql = ["""
   DROP TABLE IF EXISTS resource;
    """,
           """
         create table resource
           (
               id         int primary key,
               url        varchar(255) null unique ,
               name       text         null,
               expire     int          null,
               expire_cst varchar(255) null,
               data       longtext     null
       
           )
           """
           ]
    cur = con_sqlite.cursor()
    for s in sql:
        cur.execute(s)
    con_sqlite.commit()


def clear_mongodb():
    mongo_client.drop_database("yyets")


def sqlite_insert(data: List[dict]):
    cur = con_sqlite.cursor()
    sql = "INSERT INTO resource VALUES(?,?,?,?,?,?)"

    cur.executemany(sql, [list(i.values()) for i in data])
    con_sqlite.commit()


def mongodb_insert(data: List[dict]):
    db = mongo_client["yyets"]
    col = db["resource"]
    # deserialize data.data
    inserted = []
    for i in data:
        i["data"] = json.loads(i["data"])
        inserted.append(i)
    col.insert_many(inserted)


def main():
    create_sqlite_database()
    clear_mongodb()

    mysql_cur = con_mysql.cursor()
    mysql_cur.execute("select count(id) from resource")
    count = mysql_cur.fetchall()[0]["count(id)"]

    mysql_cur.execute("SELECT * FROM resource")

    with tqdm.tqdm(total=count * 2) as pbar:
        while True:
            data = mysql_cur.fetchmany(SIZE)
            if data:
                sqlite_insert(data)
                pbar.update(SIZE)
                mongodb_insert(data)
                pbar.update(SIZE)
            else:
                break


if __name__ == '__main__':
    main()
    con_mysql.close()
    con_sqlite.close()
    mongo_client.close()
