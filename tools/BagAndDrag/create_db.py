#!/usr/local/bin/python3
# coding: utf-8

# BagAndDrag - create_db.py
# 1/10/21 15:23
#

__author__ = "Benny <benny.think@gmail.com>"

import pymysql

con = pymysql.Connect(host="127.0.0.1", user="root", password="root", charset="utf8mb4")

sql = [
    "CREATE DATABASE yyets CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;",
    "use yyets",
    """
    create table resource
    (
        id         int primary key,
        url        varchar(255) null unique ,
        name       text         null,
        expire     int          null,
        expire_cst varchar(255) null,
        data       longtext     null
    
    )charset utf8mb4;
    
    
    """,

    """
    create table failure
    (
        id        int primary key not null,
        traceback longtext        null
    )charset utf8mb4;
    """,

]
cur = con.cursor()
for s in sql:
    cur.execute(s)
con.close()
