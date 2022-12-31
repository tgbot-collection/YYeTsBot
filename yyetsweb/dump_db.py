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

logging.basicConfig(level=logging.INFO)

data_path = pathlib.Path(__file__).parent.joinpath("templates", "dump")
data_path.mkdir(exist_ok=True)
sqlite_file = data_path.joinpath("yyets.db")

CHUNK_SIZE = 1000


def SQLite():
    return sqlite3.connect(sqlite_file, check_same_thread=False)


def MySQL():
    return pymysql.connect(host='mysql', user='root', passwd='root', charset='utf8mb4')


def MongoDB():
    return pymongo.MongoClient('mongo', 27017, connect=False)


def read_resource():
    logging.info("Reading resource from mongo")
    client = MongoDB()
    data = client["zimuzu"]["yyets"].find(projection={"_id": False})
    return data


def read_comment():
    logging.info("Reding comment from mongo")
    client = MongoDB()
    data = client["zimuzu"]["comment"].find(
        projection={"_id": False, "username": False, "ip": False, "browser": False})
    return data


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
            content  longtext null,
            date     varchar(256) null,
            id     int null,
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
                content  longtext null,
                date     varchar(256) null,
                id     int null,
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
        data = each["data"]["info"]
        resource_id = data["id"]
        cnname = data["cnname"]
        enname = data["enname"]
        aliasname = data["aliasname"]
        views = data["views"]
        area = data["area"]
        data = json.dumps(each, ensure_ascii=False)

        batch_data.append((resource_id, cnname, enname, aliasname, area, views, data, "", ""))
        mb.append(each)
        if len(batch_data) == CHUNK_SIZE:
            sql1 = "insert into yyets values (%s, %s, %s, %s, %s, %s, %s, %s,%s)"
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
        content = each["content"]
        date = each["date"]
        id = each.get("id", 0)
        resource_id = each["resource_id"]
        browser = "Fake Browser"
        username = "Anonymous"
        batch_data.append((content, date, id, resource_id, browser, username))
        each.update(browser=browser, username=username)
        mb.append(each)
        if len(batch_data) == CHUNK_SIZE:
            sql1 = "insert into comment values (%s, %s, %s, %s, %s, %s)"
            sql2 = "insert into comment values ( ?, ?, ?,?, ?,?)"
            insert_func(batch_data, mb, sql1, sql2, "comment")
            batch_data = []
            mb = []


def zip_file():
    logging.info("Zipping SQLite...")
    p = data_path.joinpath("yyets_sqlite.zip")
    with zipfile.ZipFile(p, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(sqlite_file, "yyets_sqlite.db")

    logging.info("Dumping MySQL...")
    subprocess.check_output("mysqldump -h mysql -u root -proot zimuzu > zimuzu.sql", shell=True)
    p = data_path.joinpath("yyets_mysql.zip")
    logging.info("Zipping MySQL...")
    with zipfile.ZipFile(p, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write("zimuzu.sql")

    logging.info("Dumping MongoDB")
    subprocess.check_output(
        "mongodump -h mongo -d share --gzip --archive=" + data_path.joinpath("yyets_mongo.gz").as_posix(),
        shell=True)


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


if __name__ == '__main__':
    entry_dump()
