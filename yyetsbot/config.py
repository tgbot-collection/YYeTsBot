# coding: utf-8
# YYeTsBot - config.py
# 2019/8/15 18:42

__author__ = "Benny <benny.think@gmail.com>"

import os

# website config
# yyets
BASE_URL = "http://www.rrys2020.com"
LOGIN_URL = "http://www.rrys2020.com/user/login"
GET_USER = "http://www.rrys2020.com/user/login/getCurUserTopInfo"
YYETS_SEARCH_URL = "http://www.rrys2020.com/search?keyword={kw}&type=resource"
AJAX_LOGIN = "http://www.rrys2020.com/User/Login/ajaxLogin"
SHARE_URL = "http://www.rrys2020.com/resource/ushare"
SHARE_WEB = "http://got002.com/resource.html?code={code}"
# http://got002.com/api/v1/static/resource/detail?code=9YxN91
SHARE_API = "http://got002.com/api/v1/static/resource/detail?code={code}"

# fix zimuxia
FIX_RESOURCE = "http://www.zimuxia.cn/portfolio/{name}"
FIX_SEARCH = "http://www.zimuxia.cn/?s={kw}"

# zhuixinfan
ZHUIXINFAN_SEARCH = "http://www.fanxinzhui.com/list?k={}"
ZHUIXINFAN_RESOURCE = "http://www.fanxinzhui.com{}"
# yyets website
DOMAIN = "https://yyets.click/"
WORKERS = f"{DOMAIN}resource?id=" + "{}"
# https://yyets.click/discuss#6464d5b1b27861fa44647e7e
DISCUSS = f"{DOMAIN}discuss#" + "{}"
# new zmz
NEWZMZ_SEARCH = "https://newzmz.com/subres/index/getres.html?keyword={}"
NEWZMZ_RESOURCE = "https://ysfx.tv/view/{}"

# BD2020
BD2020_SEARCH = "https://v.bd2020.me/search.jspx?q={}"

# XL720
XL720_SEARCH = "https://www.xl720.com/?s={}"

# authentication config
TOKEN = os.getenv("TOKEN")

# network and server config
PROXY = os.getenv("PROXY")
REDIS = os.getenv("REDIS", "redis")
MONGO = os.getenv("MONGO", "mongo")

# other
MAINTAINER = os.getenv("OWNER")
REPORT = os.getenv("REPORT", False)
# This name must match class name, other wise this bot won't running.
FANSUB_ORDER: str = os.getenv("ORDER") or "YYeTsOffline,ZimuxiaOnline,NewzmzOnline,ZhuixinfanOnline,XL720,BD2020"
