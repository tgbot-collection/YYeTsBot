# coding: utf-8
# YYeTsBot - config.py
# 2019/8/15 18:42

__author__ = 'Benny <benny.think@gmail.com>'

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
# fix
FIX_RESOURCE = "https://www.zimuxia.cn/portfolio/{name}"
FIX_SEARCH = "https://www.zimuxia.cn/?s={kw}"
# cloudflare worker
WORKERS = "https://yyets.dmesg.app/resource.html?id={id}"

# authentication config
TOKEN = os.environ.get("TOKEN") or "TOKEN"
USERNAME = os.environ.get("USERNAME") or "USERNAME"
PASSWORD = os.environ.get("PASSWORD") or "password"

# network and server config
PROXY = os.environ.get("PROXY")
REDIS = os.environ.get("REDIS") or "redis"
MONGO = os.environ.get("MONGO") or "mongo"

# other
MAINTAINER = os.environ.get("MAINTAINER")
REPORT = os.environ.get("REPORT") or False
# This name must match class name, other wise this bot won't functional.
FANSUB_ORDER: str = os.environ.get("ORDER") or 'YYeTsOffline,ZimuxiaOnline'
