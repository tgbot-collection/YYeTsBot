#!/usr/bin/env python3
# coding: utf-8

import pathlib
import sys
import unittest

from tornado.testing import AsyncHTTPTestCase

sys.path.append(pathlib.Path(__file__).parent.parent.as_posix())
from server import RunServer


class YYeTsTest(AsyncHTTPTestCase):
    def get_app(self):
        return RunServer.application


class TestIndex(YYeTsTest):
    def test_homepage(self):
        response = self.fetch("/")
        self.assertEqual(response.code, 200)
        self.assertTrue(b"<!doctype html>" in response.body)


if __name__ == "__main__":
    unittest.main()
