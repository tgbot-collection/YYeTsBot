#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - test_bot.py
# 1/31/21 14:05
#

__author__ = "Benny <benny.think@gmail.com>"

import unittest
import sys
from unittest import mock

from telebot.types import Message

sys.path.append("../yyetsbot")
import bot as mybot


@mock.patch("bot.bot")
class TestStartHandler(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        jsonstring = r'{"message_id":1,"from":{"id":108929734,"first_name":"Frank","last_name":"Wang","username":"eternnoir","is_bot":true},"chat":{"id":1734,"first_name":"F","type":"private","last_name":"Wa","username":"oir"},"date":1435296025,"text":"/start"}'
        cls.message = Message.de_json(jsonstring)

    @classmethod
    def tearDownClass(cls) -> None:
        pass

    def test_start(self, b):
        mybot.send_welcome(self.message)
        self.assertEqual(1, b.send_message.call_count)
        self.assertEqual(1, b.send_chat_action.call_count)
        self.assertEqual(self.message.chat.id, b.send_message.call_args.args[0])
        self.assertIn("欢迎使用", b.send_message.call_args.args[1])
