#!/usr/bin/env python3
# coding: utf-8
import json
import time
from datetime import date, timedelta
from http import HTTPStatus
from pathlib import Path

from tornado import gen
from tornado.concurrent import run_on_executor

from handlers.base import BaseHandler

filename = Path(__file__).name.split(".")[0]


class MetricsHandler(BaseHandler):
    filename = filename

    @run_on_executor()
    def set_metrics(self):
        payload = self.json
        metrics_type = payload.get("type", self.get_query_argument("type", "unknown"))
        _id = payload.get("id")

        self.instance.set_metrics(metrics_type, _id)
        self.set_status(HTTPStatus.CREATED)
        return {}

    @run_on_executor()
    def get_metrics(self):
        if not self.instance.is_admin(self.get_current_user()):
            self.set_status(HTTPStatus.NOT_FOUND)
            return ""

        # only return latest 7 days. with days parameter to generate different range
        from_date = self.get_query_argument("from", None)
        to_date = self.get_query_argument("to", None)
        if to_date is None:
            to_date = time.strftime("%Y-%m-%d", time.localtime())
        if from_date is None:
            from_date = time.strftime("%Y-%m-%d", time.localtime(time.time() - 3600 * 24 * 7))

        return self.instance.get_metrics(from_date, to_date)

    @gen.coroutine
    def get(self):
        resp = yield self.get_metrics()
        self.write(resp)

    @gen.coroutine
    def post(self):
        resp = yield self.set_metrics()
        self.write(resp)

    @gen.coroutine
    def options(self):
        self.add_tauri()
        self.set_header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept")
        self.set_status(HTTPStatus.NO_CONTENT)
        self.finish()


class GrafanaIndexHandler(BaseHandler):
    filename = filename

    def get(self):
        self.write({})


class GrafanaSearchHandler(BaseHandler):
    filename = filename

    def post(self):
        data = [
            "resource",
            "top",
            "home",
            "search",
            "extra",
            "discuss",
            "multiDownload",
            "download",
            "user",
            "share",
            "me",
            "database",
            "help",
            "backOld",
            "favorite",
            "unFavorite",
            "comment",
        ]
        self.write(json.dumps(data))


class GrafanaQueryHandler(BaseHandler):
    filename = filename

    @staticmethod
    def generate_date_series(start: str, end: str) -> list:
        start_int = [int(i) for i in start.split("-")]
        end_int = [int(i) for i in end.split("-")]
        sdate = date(*start_int)  # start date
        edate = date(*end_int)  # end date

        delta = edate - sdate  # as timedelta
        days = []
        for i in range(delta.days + 1):
            day = sdate + timedelta(days=i)
            days.append(day.strftime("%Y-%m-%d"))
        return days

    @staticmethod
    def time_str_int(text):
        return time.mktime(time.strptime(text, "%Y-%m-%d"))

    def post(self):
        payload = self.json
        start = payload["range"]["from"].split("T")[0]
        end = payload["range"]["to"].split("T")[0]
        date_series = self.generate_date_series(start, end)
        targets = [i["target"] for i in payload["targets"] if i["target"]]
        grafana_data = []
        for target in targets:
            data_points = []
            result = self.instance.get_grafana_data(date_series)
            i: dict
            for i in result:
                datum = [i[target], self.time_str_int(i["date"]) * 1000] if i.get(target) else []
                data_points.append(datum)
            temp = {"target": target, "datapoints": data_points}
            grafana_data.append(temp)
        self.write(json.dumps(grafana_data))
