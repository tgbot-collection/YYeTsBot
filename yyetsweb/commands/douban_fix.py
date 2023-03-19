#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - douban_fix.py
# 7/11/21 09:37
#

__author__ = "Benny <benny.think@gmail.com>"

import argparse
import pathlib
import sys

import requests

lib_path = pathlib.Path(__file__).parent.parent.resolve().as_posix()
sys.path.append(lib_path)

from databases.douban import Douban

parser = argparse.ArgumentParser(description="豆瓣数据修复")
parser.add_argument("resource_id", metavar="r", type=int, help="resource id")
parser.add_argument("douban_id", metavar="d", type=int, help="douban id")
args = parser.parse_args()
resource_id = args.resource_id
douban_id = args.douban_id

douban = Douban()
session = requests.Session()
ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
session.headers.update({"User-Agent": ua})

yyets_data = douban.db["yyets"].find_one({"data.info.id": resource_id})
search_html = ""
cname = yyets_data["data"]["info"]["cnname"]

final_data = douban.get_craw_data(cname, douban_id, resource_id, search_html, session)
douban.db["douban"].find_one_and_replace({"resourceId": resource_id}, final_data)
print("fix complete")
sys.exit(0)
