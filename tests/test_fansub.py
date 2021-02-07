# coding: utf-8

import unittest
import os
import sys

import requests_mock
from unittest import mock

sys.path.append("../yyetsbot")
import bot as _

from fansub import BaseFansub, YYeTsOnline, YYeTsOffline


class TestBaseFunsub(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ins = BaseFansub()
        cls.cookie_jar = dict(name="hello")
        cls.ins.cookie_file = "test_cookies.dump"  # generate on tests/test_cookies.dump

    @classmethod
    def tearDownClass(cls) -> None:
        cls().ins.redis.flushall()
        os.unlink(cls().ins.cookie_file)

    def test_save_cookies(self):
        self.ins.__save_cookies__(self.cookie_jar)
        exists = os.path.exists(self.ins.cookie_file)
        self.assertTrue(exists)

    def test_load_cookies(self):
        self.test_save_cookies()
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


class TestYYeTsTestOnline(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ins = YYeTsOnline()
        cls.cookie_jar = dict(name="hello yyets")
        cls.ins.cookie_file = "test_cookies.dump"  # generate on tests/test_cookies.dump
        cls.ins.url = "http://www.rrys2020.com/resource/1988"
        with open("data/yyets_search.html") as f:
            cls.search_html = f.read()

    @classmethod
    def tearDownClass(cls) -> None:
        cls().ins.redis.flushall()
        # os.unlink(cls().ins.cookie_file)

    def test_get_id(self):
        self.assertEqual(self.ins.id, "1988")

    @requests_mock.mock()
    def test_get_search_html(self, m):
        m.get('http://www.rrys2020.com/search?keyword=abc&type=resource', text=self.search_html)
        response = self.ins.__get_search_html__("abc")
        self.assertEqual(self.search_html, response)

    @requests_mock.mock()
    def test_search_preview(self, m):
        kw = "abc"
        m.get(f'http://www.rrys2020.com/search?keyword={kw}&type=resource', text=self.search_html)
        results = self.ins.search_preview(kw)
        results.pop("source")
        for name in results.values():
            self.assertIn(kw, name.lower())

    # TODO....
    def test_search_result(self):
        pass


class TestYYeTsTestOffline(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ins = YYeTsOffline(db="test")

    @classmethod
    def tearDownClass(cls) -> None:
        cls().ins.mongo.close()

    def test_search_preview(self):
        kw = "逃避"
        results = self.ins.search_preview(kw)
        self.assertEqual(results["source"], self.ins.label)
        results.pop("source")
        self.assertEqual(3, len(results))
        for name in results.values():
            self.assertIn(kw, name)

    def test_search_result(self):
        url = "http://www.rrys2020.com/resource/34812"
        results = self.ins.search_result(url)
        self.assertIn(str(results['all']['data']['info']['id']), url)
        self.assertIn("逃避可耻", results["cnname"])
        self.assertIn("34812", results["share"])


if __name__ == '__main__':
    unittest.main()
