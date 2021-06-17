#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - utils.py
# 6/16/21 21:42
#

__author__ = "Benny <benny.think@gmail.com>"

import time


def ts_date(ts=None):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
