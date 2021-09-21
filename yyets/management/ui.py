#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - ui.py
# 2/8/21 17:55
#

__author__ = "Benny <benny.think@gmail.com>"

import json
import time

import PySimpleGUI as sg

# All the stuff inside your window.
channel_map = {
    "movie": "电影",
    "tv": "电视剧"
}

complete = {
    "status": 1,
    "info": "OK",
    "data": {
        "info": {},
        "list": [
            {
                "season_num": "1",
                "season_cn": "第一季",
                "items": {},
                "formats": [
                    "MP4"
                ]
            }
        ]
    }
}

dl = {
    "itemid": "",
    "episode": "0",
    "name": "",
    "size": "",
    "yyets_trans": 0,
    "dateline": str(int(time.time())),
    "files": [
        {
            "way": "1",
            "way_cn": "电驴",
            "address": "",
            "passwd": ""
        },
        {
            "way": "2",
            "way_cn": "磁力",
            "address": "",
            "passwd": ""
        },
        {
            "way": "9",
            "way_cn": "百度网盘",
            "address": "",
            "passwd": ""
        },
        {
            "way": "115",
            "way_cn": "115网盘",
            "address": "",
            "passwd": ""
        }
    ]
}
item_structure = {
    "MP4": [
    ]
}


def get_value():
    for i in range(1, int(episode_input[1].get()) + 1):
        d = dl.copy()
        d["episode"] = str(i)
        d["name"] = "{}第{}集".format(cn_input[1].get(), i)
        item_structure["MP4"].append(d)

    info_structure = {
        "id": 0,
        "cnname": cn_input[1].get(),
        "enname": en_input[1].get(),
        "aliasname": alias_input[1].get(),
        "channel": channel_input[1].get(),
        "channel_cn": channel_map.get(channel_input[1].get(), ""),
        "area": area_input[1].get(),
        "show_type": "",
        "expire": "1610401225",
        "views": 0
    }

    complete["data"]["info"] = info_structure
    complete["data"]["list"][0]["items"] = item_structure

    with open("sample.json", "w") as f:
        json.dump(complete, f, indent=4, ensure_ascii=False)


cn_input = [sg.Text('cn name'), sg.InputText()]
en_input = [sg.Text('en name'), sg.InputText()]
alias_input = [sg.Text('alias name'), sg.InputText()]
channel_input = [sg.Text('channel'), sg.Combo(['movie', 'tv'], "tv")]
area_input = [sg.Text('area'), sg.Combo(['美国', '日本', '韩国', '英国'], "美国")]
episode_input = [sg.Text('episode count'), sg.InputText()]

layout = [cn_input, en_input, alias_input, channel_input, area_input, episode_input,
          [sg.Button('Ok')]
          ]

# Create the Window
window = sg.Window('Management', layout)
# Event Loop to process "events" and get the "values" of the inputs
while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED or event == 'Cancel':  # if user closes window or clicks cancel
        break
    if event == "Ok":
        print('You entered ', values[0], values[1], values[2])
        get_value()
        break
window.close()
