#!/usr/bin/env python3
# coding: utf-8

# YYeTsBot - migrate_sub.py

import pymongo
import pymysql
from pymysql.cursors import DictCursor

con = pymysql.connect(host="mysql", user="root", password="root", database="yyets", charset="utf8")
cur = con.cursor(cursor=DictCursor)
mongo_client = pymongo.MongoClient(host="mongo")
col = mongo_client["zimuzu"]["subtitle"]

cur.execute("select * from subtitle")

# 56134 rows
for sub in cur.fetchall():
    col.insert_one(sub)
