#!/usr/bin/env python3
# coding: utf-8
import json

from common.utils import Cloudflare, setup_logger
from tornado import escape

setup_logger()
cf = Cloudflare()
escape.json_encode = lambda value: json.dumps(value, ensure_ascii=False)
