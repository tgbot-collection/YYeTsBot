# coding: utf-8
# YYeTsBot - bot.py
# 2019/8/15 15:55

__author__ = 'Benny <benny.think@gmail.com>'

from typing import List, Dict
from uuid import uuid4
from bs4 import BeautifulSoup
import re
from copy import deepcopy
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(filename)s [%(levelname)s]: %(message)s')


def parser(html: str) -> (List, Dict):
    logging.info('Parsing html...')
    soup = BeautifulSoup(html, 'lxml')
    link_list = soup.find_all("ul", class_="link-list")
    list_result = []
    for block in link_list:
        line = block.find_all('li')
        _id = 1
        for ele in line:
            if ele.get('data-cat'):
                episode = ele.span.text
                size = ele.find_all('span')[2].text
                magnet = ed2k = ''
                if ele.get('data-ed2k'):
                    ed2k = ele.get('data-ed2k')
                if ele.get('data-magnet'):
                    magnet = ele.get('data-magnet')
                s, e = __season_episode(episode)
                logging.info('Saving links...')
                list_result.append(
                    {"id": uuid4().hex[:16],
                     "name": episode,
                     "season": s,
                     "size": size,
                     "episode": e,
                     "ed2k": ed2k,
                     "magnet": magnet
                     }
                )
    dict_result = {}
    for item in list_result:
        dict_result[item['id']] = deepcopy(item)
    return list_result, dict_result


def __season_episode(full_name):
    se_regex = r'\.(Ep\d*|S\d*E\d*)\.'
    names = re.findall(se_regex, full_name)
    season = episode = ''
    if names:
        s = re.findall(r'\d{2}', names[0])
        if len(s) == 2:
            episode = s[-1]
            season = s[0]
        else:
            episode = s[-1]

    return season, episode


if __name__ == '__main__':
    text = open('test.html', encoding='u8').read()
    s = parser(text)
    print(s)
