#!/usr/bin/env python3
# coding: utf-8
import contextlib
import os
import re
from http import HTTPStatus

import pymongo
from bson import ObjectId

from common.utils import check_spam, send_mail, ts_date
from databases.base import Mongo
from databases.other import Captcha, SpamProcess


class Comment(Mongo):
    def __init__(self):
        super().__init__()
        self.inner_page = 1
        self.inner_size = 5
        self.projection = {"ip": False, "parent_id": False}

    @staticmethod
    def convert_objectid(data):
        # change _id to id, remove _id
        for item in data:
            item["id"] = str(item["_id"])
            item.pop("_id")
            for child in item.get("children", []):
                with contextlib.suppress(Exception):
                    child["id"] = str(child["_id"])
                    child.pop("_id")

    def find_children(self, parent_data):
        for item in parent_data:
            children_ids = item.get("children", [])
            condition = {
                "_id": {"$in": children_ids},
                "deleted_at": {"$exists": False},
                "type": "child",
            }
            children_count = self.db["comment"].count_documents(condition)
            children_data = (
                self.db["comment"]
                .find(condition, self.projection)
                .sort("_id", pymongo.DESCENDING)
                .limit(self.inner_size)
                .skip((self.inner_page - 1) * self.inner_size)
            )
            children_data = list(children_data)
            self.get_user_group(children_data)
            self.add_reactions(children_data)

            item["children"] = []
            if children_data:
                item["children"].extend(children_data)
                item["childrenCount"] = children_count
            else:
                item["childrenCount"] = 0

    def get_user_group(self, data):
        whitelist = os.getenv("whitelist", "").split(",")
        for comment in data:
            username = comment["username"]
            user = self.db["users"].find_one({"username": username}) or {}
            group = user.get("group", ["user"])
            comment["group"] = group
            comment["hasAvatar"] = bool(user.get("avatar"))
            if username in whitelist:
                comment["group"].append("publisher")

    def add_reactions(self, data):
        for comment in data:
            cid = comment.get("id") or comment.get("_id")
            cid = str(cid)
            reactions = (
                self.db["reactions"].find_one({"comment_id": cid}, projection={"_id": False, "comment_id": False}) or {}
            )
            for verb, users in reactions.items():
                if users:
                    comment.setdefault("reactions", []).append({"verb": verb, "users": users})

    def get_comment(self, resource_id: int, page: int, size: int, **kwargs) -> dict:
        self.inner_page = kwargs.get("inner_page", 1)
        self.inner_size = kwargs.get("inner_size", 5)
        comment_id = kwargs.get("comment_id")
        sort = kwargs.get("sort")
        if sort == "newest":
            sort = pymongo.DESCENDING
        else:
            sort = pymongo.ASCENDING

        condition = {
            "resource_id": resource_id,
            "deleted_at": {"$exists": False},
            "type": {"$ne": "child"},
        }
        if comment_id:
            # 搜索某个评论id的结果
            condition = {
                "deleted_at": {"$exists": False},
                "$or": [
                    # 如果是子评论id，搜索子评论，会将整个父评论带出
                    {"children": {"$in": [ObjectId(comment_id)]}},
                    # 如果是父评论id，搜索父评论，并且排除子评论的记录
                    {"_id": ObjectId(comment_id), "type": {"$ne": "child"}},
                ],
            }

        count = self.db["comment"].count_documents(condition)
        data = (
            self.db["comment"]
            .find(condition, self.projection)
            .sort("_id", pymongo.DESCENDING)
            .limit(size)
            .skip((page - 1) * size)
        ).sort("_id", sort)
        data = list(data)
        self.find_children(data)
        self.convert_objectid(data)
        self.get_user_group(data)
        self.add_reactions(data)

        return {"data": data, "count": count, "resource_id": resource_id}

    def add_comment(
        self,
        captcha: str,
        captcha_id: int,
        content: str,
        resource_id: int,
        ip: str,
        username: str,
        browser: str,
        parent_comment_id=None,
    ) -> dict:
        user_data = self.db["users"].find_one({"username": username})
        # old user is allowed to comment without verification
        if not self.is_old_user(username) and user_data.get("email", {}).get("verified", False) is False:
            return {
                "status_code": HTTPStatus.TEMPORARY_REDIRECT,
                "message": "你需要验证邮箱才能评论，请到个人中心进行验证",
            }
        returned = {"status_code": 0, "message": ""}
        # check if this user is blocked
        reason = self.is_user_blocked(username)
        if reason:
            return {"status_code": HTTPStatus.FORBIDDEN, "message": reason}
        if check_spam(ip, browser, username, content) != 0:
            document = {
                "username": username,
                "ip": ip,
                "date": ts_date(),
                "browser": browser,
                "content": content,
                "resource_id": resource_id,
            }
            inserted_id = self.db["spam"].insert_one(document).inserted_id
            document["_id"] = str(inserted_id)
            SpamProcess.request_approval(document)
            return {
                "status_code": HTTPStatus.FORBIDDEN,
                "message": f"possible spam, reference id: {inserted_id}",
            }

        user_group = user_data.get("group", [])
        if not user_group:
            # admin don't have to verify code
            verify_result = Captcha().verify_code(captcha, captcha_id)
            if os.getenv("PYTHON_DEV"):
                pass
            elif not verify_result["status"]:
                returned["status_code"] = HTTPStatus.BAD_REQUEST
                returned["message"] = verify_result["message"]
                return returned

        exists = self.db["yyets"].find_one({"data.info.id": resource_id})
        if not exists:
            returned["status_code"] = HTTPStatus.NOT_FOUND
            returned["message"] = "资源不存在"
            return returned

        if parent_comment_id:
            exists = self.db["comment"].find_one({"_id": ObjectId(parent_comment_id)})
            if not exists:
                returned["status_code"] = HTTPStatus.NOT_FOUND
                returned["message"] = "评论不存在"
                return returned

        basic_comment = {
            "username": username,
            "ip": ip,
            "date": ts_date(),
            "browser": browser,
            "content": content,
            "resource_id": resource_id,
        }
        if parent_comment_id is None:
            basic_comment["type"] = "parent"
        else:
            basic_comment["type"] = "child"
        # 无论什么评论，都要插入一个新的document
        inserted_id: str = self.db["comment"].insert_one(basic_comment).inserted_id

        if parent_comment_id is not None:
            # 对父评论的子评论，需要给父评论加children id
            self.db["comment"].find_one_and_update(
                {"_id": ObjectId(parent_comment_id)},
                {"$push": {"children": inserted_id}},
            )
            self.db["comment"].find_one_and_update(
                {"_id": ObjectId(inserted_id)},
                {"$set": {"parent_id": ObjectId(parent_comment_id)}},
            )
        returned["status_code"] = HTTPStatus.CREATED
        returned["message"] = "评论成功"

        # notification
        if parent_comment_id:
            # find username

            self.db["notification"].find_one_and_update(
                {"username": exists["username"]},
                {"$push": {"unread": inserted_id}},
                upsert=True,
            )
            # send email
            parent_comment = self.db["comment"].find_one({"_id": ObjectId(parent_comment_id)})
            if resource_id == 233:
                link = f"https://yyets.click/discuss#{parent_comment_id}"
            else:
                link = f"https://yyets.click/resource?id={resource_id}#{parent_comment_id}"
            user_info = self.db["users"].find_one({"username": parent_comment["username"], "email.verified": True})
            if user_info:
                subject = "[人人影视下载分享站] 你的评论有了新的回复"
                pt_content = content.split("</reply>")[-1]
                text = (
                    f"你的评论 {parent_comment['content']} 有了新的回复：<br>{pt_content}"
                    f"<br>你可以<a href='{link}'>点此链接</a>查看<br><br>请勿回复此邮件"
                )
                context = {"username": username, "text": text}
                send_mail(user_info["email"]["address"], subject, context)
        return returned

    def delete_comment(self, comment_id):
        current_time = ts_date()
        count = (
            self.db["comment"]
            .update_one(
                {"_id": ObjectId(comment_id), "deleted_at": {"$exists": False}},
                {"$set": {"deleted_at": current_time}},
            )
            .modified_count
        )
        # 找到子评论，全部标记删除
        parent_data = self.db["comment"].find_one({"_id": ObjectId(comment_id)})
        if parent_data:
            child_ids = parent_data.get("children", [])
        else:
            child_ids = []
        count += (
            self.db["comment"]
            .update_many(
                {"_id": {"$in": child_ids}, "deleted_at": {"$exists": False}},
                {"$set": {"deleted_at": current_time}},
            )
            .modified_count
        )

        returned = {"status_code": 0, "message": "", "count": -1}
        if count == 0:
            returned["status_code"] = HTTPStatus.NOT_FOUND
            returned["count"] = 0
        else:
            returned["status_code"] = HTTPStatus.OK
            returned["count"] = count

        return returned


class CommentReaction(Mongo):
    def react_comment(self, username, data):
        # {"comment_id":"da23","😊":["user1","user2"]}
        comment_id = data["comment_id"]
        verb = data["verb"]
        method = data["method"]
        if not self.db["comment"].find_one({"_id": ObjectId(comment_id)}):
            return {
                "status": False,
                "message": "Where is your comments?",
                "status_code": HTTPStatus.NOT_FOUND,
            }

        if method == "POST":
            self.db["reactions"].update_one({"comment_id": comment_id}, {"$addToSet": {verb: username}}, upsert=True)
            code = HTTPStatus.CREATED
        elif method == "DELETE":
            self.db["reactions"].update_one({"comment_id": comment_id}, {"$pull": {verb: username}})
            code = HTTPStatus.ACCEPTED
        else:
            code = HTTPStatus.BAD_REQUEST
        return {"status": True, "message": "success", "status_code": code}


class CommentChild(Comment, Mongo):
    def __init__(self):
        super().__init__()
        self.page = 1
        self.size = 5
        self.projection = {"ip": False, "parent_id": False}

    def get_comment(self, parent_id: str, page: int, size: int) -> dict:
        condition = {
            "parent_id": ObjectId(parent_id),
            "deleted_at": {"$exists": False},
            "type": "child",
        }

        count = self.db["comment"].count_documents(condition)
        data = (
            self.db["comment"]
            .find(condition, self.projection)
            .sort("_id", pymongo.DESCENDING)
            .limit(size)
            .skip((page - 1) * size)
        )
        data = list(data)
        self.convert_objectid(data)
        self.get_user_group(data)
        return {
            "data": data,
            "count": count,
        }


class CommentNewest(Comment, Mongo):
    def __init__(self):
        super().__init__()
        self.page = 1
        self.size = 5
        self.projection = {"ip": False, "parent_id": False, "children": False}
        self.condition: "dict" = {"deleted_at": {"$exists": False}}

    def get_comment(self, page: int, size: int, keyword="") -> dict:
        # ID，时间，用户名，用户组，资源名，资源id
        count = self.db["comment"].count_documents(self.condition)
        data = (
            self.db["comment"]
            .find(self.condition, self.projection)
            .sort("_id", pymongo.DESCENDING)
            .limit(size)
            .skip((page - 1) * size)
        )
        data = list(data)
        self.convert_objectid(data)
        self.get_user_group(data)
        self.extra_info(data)
        return {
            "data": data,
            "count": count,
        }

    def extra_info(self, data):
        for i in data:
            resource_id = i.get("resource_id", 233)
            res = self.db["yyets"].find_one({"data.info.id": resource_id})
            if res:
                i["cnname"] = res["data"]["info"]["cnname"]


class CommentSearch(CommentNewest):
    def get_comment(self, page: int, size: int, keyword="") -> dict:
        self.projection.pop("children")
        self.condition.update(content={"$regex": f".*{keyword}.*", "$options": "i"})
        data = list(
            self.db["comment"]
            .find(self.condition, self.projection)
            .sort("_id", pymongo.DESCENDING)
            .limit(size)
            .skip((page - 1) * size)
        )
        self.convert_objectid(data)
        self.get_user_group(data)
        self.extra_info(data)
        self.fill_children(data)
        # final step - remove children
        for i in data:
            i.pop("children", None)
        return {
            "data": data,
        }

    def fill_children(self, data):
        for item in data:
            child_id: "list" = item.get("children", [])
            children = list(
                self.db["comment"].find({"_id": {"$in": child_id}}, self.projection).sort("_id", pymongo.DESCENDING)
            )
            self.convert_objectid(children)
            self.get_user_group(children)
            self.extra_info(children)
            data.extend(children)


class Notification(Mongo):
    def get_notification(self, username, page, size):
        # .sort("_id", pymongo.DESCENDING).limit(size).skip((page - 1) * size)
        notify = self.db["notification"].find_one({"username": username}, projection={"_id": False})
        if not notify:
            return {
                "username": username,
                "unread_item": [],
                "read_item": [],
                "unread_count": 0,
                "read_count": 0,
            }

        # size is shared
        unread = notify.get("unread", [])
        id_list = []
        for item in unread[(page - 1) * size : size * page]:
            id_list.append(item)
        notify["unread_item"] = self.get_content(id_list)

        size = size - len(unread)
        read = notify.get("read", [])
        id_list = []
        for item in read[(page - 1) * size : size * page]:
            id_list.append(item)
        notify["read_item"] = self.get_content(id_list)

        notify.pop("unread", None)
        notify.pop("read", None)
        notify["unread_count"] = len(unread)
        notify["read_count"] = len(read)
        return notify

    def get_content(self, id_list):
        comments = (
            self.db["comment"]
            .find({"_id": {"$in": id_list}}, projection={"ip": False, "parent_id": False})
            .sort("_id", pymongo.DESCENDING)
        )
        comments = list(comments)
        for comment in comments:
            comment["id"] = str(comment["_id"])
            comment.pop("_id")
            reply_to_id = re.findall(r'"(.*)"', comment["content"])[0]
            rtc = self.db["comment"].find_one(
                {"_id": ObjectId(reply_to_id)},
                projection={"content": True, "_id": False},
            )
            comment["reply_to_content"] = getattr(rtc, "content", "")

        return comments

    def update_notification(self, username, verb, comment_id):
        if verb == "read":
            v1, v2 = "read", "unread"
        else:
            v1, v2 = "unread", "read"
        self.db["notification"].find_one_and_update(
            {"username": username},
            {"$push": {v1: ObjectId(comment_id)}, "$pull": {v2: ObjectId(comment_id)}},
        )

        return {}
