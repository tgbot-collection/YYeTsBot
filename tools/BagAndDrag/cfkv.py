#!/usr/local/bin/python3
# coding: utf-8

# BagAndDrag - cfkv.py
# 1/17/21 12:08
#

__author__ = "Benny <benny.think@gmail.com>"

import json
import os

import pymysql

con = pymysql.Connect(host="127.0.0.1", user="root", password="root", charset="utf8mb4", database="yyets",
                      cursorclass=pymysql.cursors.DictCursor)
cur = con.cursor()

SIZE = 3000
cur.execute("select count(id) from resource")
count = cur.fetchall()[0]["count(id)"]
LIMIT = count // SIZE + 1


def convert_kv():
    for i in range(1, LIMIT + 1):
        SQL = "select id,data from resource limit %d offset %d" % (SIZE, (i - 1) * SIZE)
        print(SQL)
        cur = con.cursor()
        cur.execute(SQL)
        data = cur.fetchall()
        write_data = []
        for datum in data:
            write_data.append({
                "key": str(datum["id"]),  # keys need to be str
                "value": datum['data']}
            )
        with open(f"kv/kv_data{i - 1}.json", "w") as f:
            json.dump(write_data, f, ensure_ascii=False)


def verify_kv_data():
    files = os.listdir("kv")
    rows = 0
    for file in files:
        if file.startswith("kv_data"):
            with open(f"kv/{file}") as f:
                data = json.load(f)
                rows += len(data)
    print(rows, count)
    # assert rows == count


def dump_index():
    cur = con.cursor()
    indexes = {}
    cur.execute("select name, id from resource")
    data = cur.fetchall()
    for datum in data:
        name = datum["name"]
        rid = datum["id"]
        indexes[name] = rid
    with open("kv/index.json", "w") as f:
        write_data = [
            {
                "key": "index",
                "value": json.dumps(indexes, ensure_ascii=False)
            }
        ]
        json.dump(write_data, f, ensure_ascii=False, indent=2)


def generate_command():
    files = os.listdir("kv")
    tpl = "wrangler kv:bulk put --namespace-id=01d666b5ebae464193998bb074f672cf {filename}"
    shell = []
    for file in files:
        if file.endswith(".json"):
            shell.append(tpl.format(filename=file) + "\n")
    with open("kv/bulk.sh", "w") as f:
        f.writelines(shell)


if __name__ == '__main__':
    convert_kv()
    verify_kv_data()
    dump_index()
    generate_command()
