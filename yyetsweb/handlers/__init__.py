#!/usr/bin/env python3
# coding: utf-8
import json

from tornado import escape

from common.utils import setup_logger, Cloudflare

setup_logger()
cf = Cloudflare()
escape.json_encode = lambda value: json.dumps(value, ensure_ascii=False)
