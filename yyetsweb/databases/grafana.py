#!/usr/bin/env python3
# coding: utf-8
import time
from datetime import date, timedelta

import pymongo

from databases.base import Mongo


class GrafanaQuery(Mongo):
    def get_grafana_data(self, date_series) -> str:
        condition = {"date": {"$in": date_series}}
        projection = {"_id": False}
        return self.db["metrics"].find(condition, projection)


class Metrics(Mongo):
    def set_metrics(self, metrics_type: str, data: str):
        today = time.strftime("%Y-%m-%d", time.localtime())
        if metrics_type == "viewSubtitle":
            self.db["subtitle"].find_one_and_update({"id": data}, {"$inc": {"views": 1}})
        else:
            self.db["metrics"].update_one({"date": today}, {"$inc": {metrics_type: 1}}, upsert=True)

    def get_metrics(self, from_date: str, to_date: str) -> dict:
        start_int = [int(i) for i in from_date.split("-")]
        end_int = [int(i) for i in to_date.split("-")]
        sdate = date(*start_int)  # start date
        edate = date(*end_int)  # end date
        date_range = [str(sdate + timedelta(days=x)) for x in range((edate - sdate).days + 1)]
        condition = {"date": {"$in": date_range}}
        result = self.db["metrics"].find(condition, {"_id": False}).sort("date", pymongo.DESCENDING)

        return dict(metrics=list(result))
