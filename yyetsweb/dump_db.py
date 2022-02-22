#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - dump_db.py
# 2/4/22 18:10
#

__author__ = "Benny <benny.think@gmail.com>"

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

data_path = pathlib.Path(__file__).parent.joinpath("templates", "data")
sqlite_file = data_path.joinpath("yyets.db")

CHUNK_SIZE = 1000


def get_conn():
    try:
        mongo = pymongo.MongoClient('mongo', 27017)
        mc = pymysql.connect(host='mysql', user='root', passwd='root', charset='utf8mb4')
        sc = sqlite3.connect(sqlite_file, check_same_thread=False)
        db = pymongo.MongoClient('mongo', 27017)["zimuzu"]
    except Exception as e:
        logging.error(e)
        return None, None, None, None
    return mongo, mc, sc, db


mongo, mc, sc, db = get_conn()


def read_resource():
    logging.info("Reading resource from mongo")
    return db["yyets"].find(projection={"_id": False})


def read_comment():
    logging.info("Reding comment from mongo")
    return db["comment"].find(
        projection={"_id": False, "username": False, "ip": False, "browser": False})


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
            data        longtext     null
        ) charset utf8mb4;
        """
    comment_sql = """
        create table comment
        (
            content  longtext null,
            date     varchar(256) null,
            id     int null,
            resource_id     varchar(256) null
        ) charset utf8mb4;
        """

    cur = mc.cursor()
    cur.execute(db_sql)
    cur.execute("use zimuzu")
    cur.execute(resource_sql)
    cur.execute(comment_sql)
    mc.commit()


def prepare_sqlite():
    logging.info("Preparing sqlite")
    cur = sc.cursor()
    resource_sql = """
            create table yyets
            (
                resource_id int          null,
                cnname      varchar(256) null,
                enname     varchar(256) null,
                aliasname   varchar(256) null,
                data        longtext     null
            );
            """
    comment_sql = """
            create table comment
            (
                content  longtext null,
                date     varchar(256) null,
                id     int null,
                resource_id     varchar(256) null
            );
            """

    cur.execute(resource_sql)
    cur.execute(comment_sql)
    sc.commit()


def dump_resource():
    res = read_resource()
    # insert into mysql
    batch_data = []
    mb = []
    for each in tqdm(res, total=db["yyets"].count_documents({})):
        data = each["data"]["info"]
        resource_id = data["id"]
        cnname = data["cnname"]
        enname = data["enname"]
        aliasname = data["aliasname"]
        data = json.dumps(each, ensure_ascii=False)

        batch_data.append((resource_id, cnname, enname, aliasname, data))
        mb.append(each)
        if len(batch_data) == CHUNK_SIZE:
            sql1 = "insert into yyets values (%s, %s, %s, %s, %s)"
            sql2 = "insert into yyets values (?, ?, ?, ?, ?)"
            insert_func(batch_data, mb, sql1, sql2, "resource")
            batch_data = []
            mb = []


def insert_func(batch_data, mb, sql1, sql2, col_name=None):
    mysql_cur = mc.cursor()
    sqlite_cur = sc.cursor()
    col = pymongo.MongoClient('mongo', 27017)["share"][col_name]
    mysql_cur.execute("use zimuzu")

    mysql_cur.executemany(sql1, batch_data)
    sqlite_cur.executemany(sql2, batch_data)
    col.insert_many(mb)
    mc.commit()
    sc.commit()


def dump_comment():
    res = read_comment()
    batch_data = []
    mb = []
    for each in tqdm(res, total=db["comment"].count_documents({})):
        content = each["content"]
        date = each["date"]
        id = each.get("id", 0)
        resource_id = each["resource_id"]
        batch_data.append((content, date, id, resource_id))
        mb.append(each)
        if len(batch_data) == CHUNK_SIZE:
            sql1 = "insert into comment values (%s, %s, %s, %s)"
            sql2 = "insert into comment values ( ?, ?, ?,?)"
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
    logging.info("Cleaning up...")
    mc.cursor().execute("drop database zimuzu")
    os.unlink(sqlite_file)
    mongo.drop_database("share")
    os.unlink("zimuzu.sql")


def entry_dump():
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
