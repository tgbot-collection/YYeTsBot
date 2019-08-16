# coding: utf-8
# YYeTsBot - html_request.py
# 2019/8/15 18:30

__author__ = 'Benny <benny.think@gmail.com>'

import logging
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(filename)s [%(levelname)s]: %(message)s')

URL = 'http://oabt005.com/index/index/k/{kw}/p/{page}'

s = requests.Session()


def get_html(kw: str) -> list:
    contents = []
    for i in range(1, 20):
        url = URL.format(kw=kw, page=i)
        logging.info('Requesting %s' % url)
        r = s.get(url)
        # status code is always 200
        if '一共0条内容' not in r.text:
            contents.append(r.text)
        else:
            break
    return contents


if __name__ == '__main__':
    get_html('轮到你了')
