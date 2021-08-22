#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - convert_to_sqlite.py
# 6/17/21 12:41
#

__author__ = "Benny <benny.think@gmail.com>"

import json
import pymysql

import pymongo

mongo = pymongo.MongoClient()
yyets = mongo["zimuzu"]["yyets"]

con = pymysql.connect(host="mysql", user="root", password="root", charset="utf8mb4")
cur = con.cursor()
cur.execute("create database zimuzu")
cur.execute("use zimuzu")
TABLE_SQL = """
CREATE TABLE IF NOT EXISTS yyets
(
    id        int,
    cnname    text,
    enname    text,
    aliasname text,
    views     int,
    data      longtext
);
"""
cur.execute(TABLE_SQL)

INSERT_SQL = """
INSERT INTO yyets VALUES (%s, %s, %s, %s ,%s, %s);
"""
for resource in yyets.find(projection={"_id": False}):
    resource_id = resource["data"]["info"]["id"]
    cnname = resource["data"]["info"]["cnname"]
    enname = resource["data"]["info"]["enname"]
    aliasname = resource["data"]["info"]["aliasname"]
    views = resource["data"]["info"]["views"]
    cur.execute(INSERT_SQL, (resource_id, cnname, enname, aliasname, views, json.dumps(resource, ensure_ascii=False)))

con.commit()
con.close()
