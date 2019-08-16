# coding: utf-8
# YYeTsBot - utils.py
# 2019/8/15 20:27

__author__ = 'Benny <benny.think@gmail.com>'

import dbm
import json
import os

db_path = os.path.join(os.path.dirname(__file__), 'data', 'yyets.dbm')
db = dbm.open(db_path, 'c')


def bunch_upsert(d: dict) -> None:
    for k in d:
        upsert(k, d[k])


def upsert(key: str, value: dict) -> None:
    db[key] = json.dumps(value, ensure_ascii=False)


def get(key: str) -> dict:
    return json.loads(db.get(key, '{}'), encoding='utf-8')


if __name__ == '__main__':
    s = {
        'e4b6bb1cb95c4f3d': {
            'id': 'e4b6bb1cb95c4f3d1',
            'name': '轮到你了 番外篇 房门之内 304室.Ep14.Chi_Jap.WEBrip.1280X720.mp4[RRYS.TV]',
            'season': '',
            'size': '263.5 MB',
            'episode': '14',
            'ed2k': 'ed2k://|file|%E8%BD%AE%E5%88%B0%E4%BD%A0%E4%BA%86%20%E7%95%AA%E5%A4%96%E7%AF%87%20%E6%88%BF%E9%97%A8%E4%B9%8B%E5%86%85%20304%E5%AE%A4.Ep14.Chi_Jap.WEBrip.1280X720.mp4|276330589|5cfb0eae0dc1b592f36ca2e9f2c14b5a|h=qfvoxipxceltqgx27xmsjclwzc3x73vo|/',
            'magnet': 'magnet:?xt=urn:btih:4ebf194be91d9520fa27d4f027efa2029e668ad4&tr=udp://9.rarbg.to:2710/announce&tr=udp://9.rarbg.me:2710/announce&tr=http://tr.cili001.com:8070/announce&tr=http://tracker.trackerfix.com:80/announce&tr=udp://open.demonii.com:1337&tr=udp://tracker.opentrackr.org:1337/announce&tr=udp://p4p.arenabg.com:1337&tr=wss://tracker.openwebtorrent.com&tr=wss://tracker.btorrent.xyz&tr=wss://tracker.fastcast.nz'
        },
        '75a392f11b8848ee': {
            'id': '75a392f11b8848ee',
            'name': '轮到你了 反击篇.Anata.no.Ban.Desu.Hangeki.hen.Ep15.Chi_Jap.HDTVrip.1280X720V2.mp4[RRYS.TV]',
            'season': '',
            'size': '673.3 MB',
            'episode': '15',
            'ed2k': 'ed2k://|file|%E8%BD%AE%E5%88%B0%E4%BD%A0%E4%BA%86%20%E5%8F%8D%E5%87%BB%E7%AF%87.Anata.no.Ban.Desu.Hangeki.hen.Ep15.Chi_Jap.HDTVrip.1280X720V2.mp4|706020550|023d98fc0ee5df59cf3c57606529b709|h=ewtroszyq6gijfzyrwepzrkvqb3tyrte|/',
            'magnet': 'magnet:?xt=urn:btih:2d913d96d062fd3f00357d78eecd29b1f2ddb742&tr=udp://9.rarbg.to:2710/announce&tr=udp://9.rarbg.me:2710/announce&tr=http://tr.cili001.com:8070/announce&tr=http://tracker.trackerfix.com:80/announce&tr=udp://open.demonii.com:1337&tr=udp://tracker.opentrackr.org:1337/announce&tr=udp://p4p.arenabg.com:1337&tr=wss://tracker.openwebtorrent.com&tr=wss://tracker.btorrent.xyz&tr=wss://tracker.fastcast.nz'
        },
    }
    bunch_upsert(s)
    print(get('e4b6bb1cb95c4f3d'))
