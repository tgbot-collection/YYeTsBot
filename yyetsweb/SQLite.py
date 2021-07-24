#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - SQLite.py
# 6/17/21 12:53
#

__author__ = "Benny <benny.think@gmail.com>"

import json
import logging
import sqlite3

from database import ResourceResource

logging.warning("\n\n%s\n### SQLite adapter is immature! Only search and view resource is available for now. ###\n%s\n",
                "#" * 87, "#" * 87)


class SQLite:
    def __init__(self):
        self.con = sqlite3.connect("yyets.sqlite", check_same_thread=False)
        self.cur = self.con.cursor()

    def __del__(self):
        self.con.close()


class FakeSQLiteResource:
    pass


class ResourceSQLiteResource(ResourceResource, SQLite):
    def get_resource_data(self, resource_id: int, username=None) -> dict:
        self.cur.execute("SELECT data FROM yyets WHERE id=?", (resource_id,))

        data = self.cur.fetchone()
        return json.loads(data[0])

    def search_resource(self, keyword: str) -> dict:
        Query = """
        SELECT id, cnname, enname, aliasname FROM yyets WHERE 
        cnname LIKE ? or enname LIKE ? or aliasname LIKE ?;
        """
        keyword = f"%{keyword}%"
        self.cur.execute(Query, (keyword, keyword, keyword))
        data = self.cur.fetchall()
        final_data = []
        for item in data:
            single = {
                "data": {
                    "info": {
                        "id": item[0],
                        "cnname": item[1],
                        "enname": item[2],
                        "aliasname": item[3],
                    }
                }
            }
            final_data.append(single)
        return dict(data=list(final_data))


if __name__ == '__main__':
    r = SQLite()
    print(globals())
    # r.get_resource_data(80000)
    # a = r.search_resource("NIGERUHA")
    # print(json.dumps(a, ensure_ascii=False))
