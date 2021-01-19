# coding: utf-8

import unittest
import os
import sys

sys.path.append("../yyetsbot")

from fansub import BaseFansub, YYeTs


class TestBaseFunsub(unittest.TestCase):
    def setUp(self) -> None:
        self.ins = BaseFansub()
        self.cookie_jar = dict(name="hello")
        self.ins.cookie_file = "test_cookies.dump"  # generate on tests/test_cookies.dump

    def tearDown(self) -> None:
        self.ins.redis.flushall()

    def test_save_cookies(self):
        self.ins.__save_cookies__(self.cookie_jar)
        exists = os.path.exists(self.ins.cookie_file)
        self.assertTrue(exists)

    def test_load_cookies(self):
        cookie = self.ins.__load_cookies__()
        self.assertEqual(cookie, self.cookie_jar)

    def test_get_from_cache(self):
        value = self.ins.__get_from_cache__("http://test.url", "__hash__")
        self.assertEqual(value, self.ins.__hash__())

    def test_save_to_cache(self):
        # never expire
        url = "http://test2.url"
        self.ins.__save_to_cache__(url, self.cookie_jar)
        cache_copy = self.ins.__get_from_cache__(url, "never mind method")
        self.assertEqual(cache_copy, self.cookie_jar)


if __name__ == '__main__':
    unittest.main()
