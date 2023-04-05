#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - dump_db.py
# 2/4/22 18:10
#

__author__ = "Benny <benny.think@gmail.com>"

import contextlib
import json
import logging
import os
import pathlib
import sqlite3
import subprocess
import time
import zipfile

import pymongo
import pymysql
import pymysql.cursors
from tqdm import tqdm

from common.utils import setup_logger

setup_logger()
data_path = pathlib.Path(__file__).parent.parent.joinpath("templates", "dump")
data_path.mkdir(exist_ok=True)
sqlite_file = data_path.joinpath("yyets.db")

CHUNK_SIZE = 1000


def SQLite():
    return sqlite3.connect(sqlite_file, check_same_thread=False)


def MySQL():
    return pymysql.connect(host="mysql", user="root", passwd="root", charset="utf8mb4")


def MongoDB():
    return pymongo.MongoClient("mongo", 27017, connect=False)


def read_resource():
    logging.info("Reading resource from mongo")
    client = MongoDB()
    data = client["zimuzu"]["yyets"].aggregate(
        [
            {
                "$project": {
                    "data.info.id": 1,
                    "data.info.cnname": 1,
                    "data.info.enname": 1,
                    "data.info.aliasname": 1,
                    "data.info.views": 1,
                    "data.info.area": 1,
                    "fullDocument": "$data",
                }
            },
            {
                "$replaceRoot": {
                    "newRoot": {
                        "$mergeObjects": [
                            "$data.info",
                            {"data": "$fullDocument"},
                        ]
                    }
                }
            },
        ]
    )
    return data


def read_comment():
    logging.info("Reading comment from mongo")
    client = MongoDB()
    res = client["zimuzu"]["comment"].aggregate(
        [
            {
                "$project": {
                    "_id": 0,
                    "content": 1,
                    "date": 1,
                    "resource_id": 1,
                    "browser": "browser",
                    "username": "username",
                }
            }
        ]
    )
    return res


def prepare_mysql():
    logging.info("Preparing mysql")
    db_sql = "create database zimuzu;"
    resource_sql = """
        create table yyets
        (
            resource_id int          null,
            cnname      varchar(256) null,
            enname     varchar(256) null,
            aliasname   varchar(256) null,
            area varchar(32),
            views int null,
            data        longtext     null,
            douban longtext null,
            image blob null
        ) charset utf8mb4;
        """
    comment_sql = """
        create table comment
        (
            date     varchar(256) null,
            content  longtext null,
            resource_id     varchar(256) null,
            browser     varchar(256) null,
            username     varchar(256) null
        ) charset utf8mb4;
        """
    con = MySQL()
    cur = con.cursor()
    cur.execute(db_sql)
    cur.execute("use zimuzu")
    cur.execute(resource_sql)
    cur.execute(comment_sql)
    con.commit()
    con.close()


def prepare_sqlite():
    logging.info("Preparing sqlite")
    con = SQLite()
    cur = con.cursor()
    resource_sql = """
            create table yyets
            (
                resource_id int          null,
                cnname      varchar(256) null,
                enname     varchar(256) null,
                aliasname   varchar(256) null,
                area varchar(32),
                views int null,
                data        longtext     null,
                douban longtext null,
                image blob null
            );
            """
    comment_sql = """
            create table comment
            (
             date     varchar(256) null,
                content  longtext null,
               
                resource_id     varchar(256) null,
                browser     varchar(256) null,
                username     varchar(256) null
            );
            """

    cur.execute(resource_sql)
    cur.execute(comment_sql)
    con.commit()
    con.close()


def dump_resource():
    res = read_resource()
    # insert into mysql
    batch_data = []
    mb = []
    client = MongoDB()
    db = client["zimuzu"]
    for each in tqdm(res, total=db["yyets"].count_documents({})):
        line = list(each.values())
        line[-1] = json.dumps(line[-1], ensure_ascii=False)
        line.extend(["", ""])
        batch_data.append(line)
        mb.append(each)
        if len(batch_data) == CHUNK_SIZE:
            sql1 = "insert into yyets values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            sql2 = "insert into yyets values (?, ?, ?, ?, ?,?,?,?,?)"
            insert_func(batch_data, mb, sql1, sql2, "yyets")
            batch_data = []
            mb = []


def insert_func(batch_data, mb, sql1, sql2, col_name=None):
    mysql_con = MySQL()
    sqlite_con = SQLite()
    mysql_cur = mysql_con.cursor()
    sqlite_cur = sqlite_con.cursor()
    client = MongoDB()
    col = client["share"][col_name]
    mysql_cur.execute("use zimuzu")

    mysql_cur.executemany(sql1, batch_data)
    sqlite_cur.executemany(sql2, batch_data)
    col.insert_many(mb)
    mysql_con.commit()
    sqlite_con.commit()
    mysql_con.close()
    sqlite_con.close()


def dump_comment():
    res = read_comment()
    batch_data = []
    mb = []
    client = MongoDB()
    for each in tqdm(res, total=client["zimuzu"]["comment"].count_documents({})):
        batch_data.append(list(each.values()))
        mb.append(each)
        if len(batch_data) == CHUNK_SIZE:
            sql1 = "insert into comment values (%s, %s, %s, %s,%s)"
            sql2 = "insert into comment values ( ?, ?, ?, ?,?)"
            insert_func(batch_data, mb, sql1, sql2, "comment")
            batch_data = []
            mb = []


def zip_file():
    logging.info("Zipping SQLite...")
    p = data_path.joinpath("yyets_sqlite.zip")
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(sqlite_file, "yyets_sqlite.db")

    logging.info("Dumping MySQL...")
    subprocess.check_output("mysqldump -h mysql -u root -proot zimuzu > zimuzu.sql", shell=True)
    p = data_path.joinpath("yyets_mysql.zip")
    logging.info("Zipping MySQL...")
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write("zimuzu.sql")

    logging.info("Dumping MongoDB")
    subprocess.check_output(
        "mongodump -h mongo -d share --gzip --archive=" + data_path.joinpath("yyets_mongo.gz").as_posix(),
        shell=True,
    )


def cleanup():
    # this function will never occur any errors!
    logging.info("Cleaning up...")
    with contextlib.suppress(Exception):
        con = MySQL()
        con.cursor().execute("drop database zimuzu")
        con.close()
    with contextlib.suppress(Exception):
        os.unlink(sqlite_file)
    with contextlib.suppress(Exception):
        MongoDB().drop_database("share")
    with contextlib.suppress(Exception):
        os.unlink("zimuzu.sql")


def entry_dump():
    cleanup()
    t0 = time.time()
    prepare_mysql()
    prepare_sqlite()
    dump_resource()
    dump_comment()
    logging.info("Write done! Time used: %.2fs" % (time.time() - t0))
    zip_file()
    cleanup()
    logging.info("Total time used: %.2fs" % (time.time() - t0))


if __name__ == "__main__":
    t0 = time.time()
    entry_dump()
    logging.info("Total time used: %.2fs" % (time.time() - t0))
