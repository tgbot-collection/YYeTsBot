#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - grafana_test_data.py
# 3/14/21 18:25
#

__author__ = "Benny <benny.think@gmail.com>"

import random
from datetime import date, timedelta

from common import Mongo

col = Mongo().client["zimuzu"]["metrics"]


def generate_date_series(start: str, end: str) -> list:
    start_int = [int(i) for i in start.split("-")]
    end_int = [int(i) for i in end.split("-")]
    sdate = date(*start_int)  # start date
    edate = date(*end_int)  # end date

    delta = edate - sdate  # as timedelta
    days = []
    for i in range(delta.days + 1):
        day = sdate + timedelta(days=i)
        days.append(day.strftime("%Y-%m-%d"))
    return days


date_series = generate_date_series("2021-02-01", "2021-03-14")

inserted = []
for date in date_series:
    inserted.append(
        {
            "date": date,
            "access": random.randint(1, 50),
            "search": random.randint(1, 50),
            "resource": random.randint(1, 50),
        }
    )

col.insert_many(inserted)
