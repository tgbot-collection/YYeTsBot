#!/usr/bin/env python3
# coding: utf-8

# YYeTsBot - add_dl.py


import random
import time
from db import Mongo


def prompt_default(text, default):
    value = input(f"{text} [{default}]: ").strip()
    return value if value else default


def main():
    mongo = Mongo()
    client = mongo.client["zimuzu"]
    col = client["yyets"]

    resource_id = int(input("请输入 resource id: ").strip())

    doc = col.find_one({"data.info.id": resource_id})
    if not doc:
        raise RuntimeError(f"resource id {resource_id} not found")

    season_num = prompt_default("请输入季", "0")
    video_format = prompt_default("请输入视频格式", "1080P").upper()
    episode = prompt_default("请输入集数", "0")

    size = input("请输入大小，比如 3GB / 7MB: ").strip()
    name = input("请输入名字: ").strip()

    address = ""
    while not address:
        address = input("请输入网盘地址 address: ").strip()

    passwd = input("请输入网盘密码 passwd，默认空: ").strip()

    new_item = {
        "itemid": str(random.randint(10_0000, 20_0000)),
        "episode": str(episode),
        "name": name,
        "size": size,
        "yyets_trans": 0,
        "dateline": str(int(time.time())),
        "files": [
            {
                "way": "9",
                "way_cn": "网盘",
                "address": address,
                "passwd": passwd,
            }
        ],
    }

    target_season = None

    for season in doc["data"]["list"]:
        if str(season.get("season_num")) == str(season_num):
            target_season = season
            break

    # 不存在这个季就自动创建
    if target_season is None:
        target_season = {
            "season_num": str(season_num),
            "season_cn": "正片" if str(season_num) == "0" else f"第{season_num}季",
            "items": {},
            "formats": [],
        }
        doc["data"]["list"].append(target_season)

    items = target_season.setdefault("items", {})
    formats = target_season.setdefault("formats", [])

    # 不存在这个格式就创建
    if video_format not in items:
        items[video_format] = []

    # append 新数据
    items[video_format].append(new_item)

    # formats 顺便补一下
    if video_format not in formats:
        formats.append(video_format)

    # 写回 mongodb
    result = col.replace_one(
        {"_id": doc["_id"]},
        doc,
    )

    print("\n写入成功")
    print("matched:", result.matched_count)
    print("modified:", result.modified_count)
    print("新增 itemid:", new_item["itemid"])


if __name__ == "__main__":
    while True:
        main()
