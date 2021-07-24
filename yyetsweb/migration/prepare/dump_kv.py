#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - dump_kv.py
# 2/6/21 18:12
#

__author__ = "Benny <benny.think@gmail.com>"

import json
import threading
from concurrent.futures.thread import ThreadPoolExecutor

import requests

s = requests.Session()

with open("index.json", ) as f:
    ids = json.load(f)

chunk = [ids[x:x + 3000] for x in range(0, len(ids), 3000)]


def download(c):
    print("running batch ", c[0])
    for i in c:
        data = s.get("https://yyets.dmesg.app/id={}".format(i)).json()
        with open(f"{i}.json", "w") as f:
            json.dump(data, f)


if __name__ == '__main__':
    threads = []
    for part in chunk:
        # Create 9 threads counting 10-19, 20-29, ... 90-99.
        thread = threading.Thread(target=download, args=(part,))
        threads.append(thread)

    # Start them all
    for thread in threads:
        thread.start()

    # Wait for all to complete
    for thread in threads:
        thread.join()
