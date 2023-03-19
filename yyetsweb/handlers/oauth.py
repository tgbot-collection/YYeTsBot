#!/usr/bin/env python3
# coding: utf-8
import logging
import os
from pathlib import Path
from urllib.parse import urlencode

import requests
from tornado.auth import GoogleOAuth2Mixin, OAuth2Mixin, TwitterMixin

from handlers.base import BaseHandler

filename = Path(__file__).name.split(".")[0]


class OAuth2Handler(BaseHandler, OAuth2Mixin):
    filename = filename
    _OAUTH_AUTHORIZE_URL = ""
    _OAUTH_ACCESS_TOKEN_URL = ""
    _OAUTH_API_REQUEST_URL = ""

    def add_oauth_user(self, username, unique, source):
        logging.info("User %s login with %s now...", username, source)
        ip = self.get_real_ip()
        browser = self.request.headers["user-agent"]
        result = self.instance.add_user(username, ip, browser, unique, source)
        if result["status"] == "success":
            self.set_secure_cookie("username", username, 365)
        self.redirect("/login?" + urlencode(result))

    def get_authenticated_user(self, client_id: str, client_secret: str, code: str, extra_fields: dict = None):
        args = {"code": code, "client_id": client_id, "client_secret": client_secret}
        if extra_fields:
            args.update(extra_fields)
        return requests.post(
            self._OAUTH_ACCESS_TOKEN_URL,
            headers={"Accept": "application/json"},
            data=args,
        ).json()

    def oauth2_sync_request(self, access_token, extra_fields=None):
        return requests.get(
            self._OAUTH_API_REQUEST_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            params=extra_fields,
        ).json()

    def get_secret(self, settings_key):
        settings = self.settings.get(settings_key)
        client_id = settings.get("key")
        client_secret = settings.get("secret")
        redirect_uri = os.getenv("DOMAIN") + self.request.path
        return client_id, client_secret, redirect_uri


class GitHubOAuth2LoginHandler(OAuth2Handler):
    _OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    _OAUTH_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
    _OAUTH_API_REQUEST_URL = "https://api.github.com/user"

    def get(self):
        client_id, client_secret, redirect_uri = self.get_secret("github_oauth")
        code = self.get_argument("code", None)
        if code:
            access = self.get_authenticated_user(client_id, client_secret, code)
            resp = self.oauth2_sync_request(access["access_token"])
            username = resp["login"]
            db_id = resp["id"]
            self.add_oauth_user(username, db_id, "GitHub")
        else:
            self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=client_id,
                scope=[],
                response_type="code",
            )


class MSOAuth2LoginHandler(OAuth2Handler):
    _OAUTH_AUTHORIZE_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    _OAUTH_ACCESS_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    _OAUTH_API_REQUEST_URL = "https://graph.microsoft.com/v1.0/me"

    def get(self):
        client_id, client_secret, redirect_uri = self.get_secret("ms_oauth")
        code = self.get_argument("code", None)
        if code:
            access = self.get_authenticated_user(
                client_id,
                client_secret,
                code,
                {"grant_type": "authorization_code", "redirect_uri": redirect_uri},
            )
            resp = self.oauth2_sync_request(access["access_token"])
            email = resp["userPrincipalName"]
            uid = resp["id"]
            self.add_oauth_user(email, uid, "Microsoft")

        else:
            self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=client_id,
                scope=["https://graph.microsoft.com/User.Read"],
                response_type="code",
            )


class GoogleOAuth2LoginHandler(GoogleOAuth2Mixin, OAuth2Handler):
    async def get(self):
        redirect_uri = os.getenv("DOMAIN") + self.request.path
        code = self.get_argument("code", None)
        if code:
            access = await self.get_authenticated_user(redirect_uri=redirect_uri, code=code)
            user = await self.oauth2_request(
                "https://www.googleapis.com/oauth2/v1/userinfo",
                access_token=access["access_token"],
            )
            email = user["email"]
            # Google's email can't be changed
            self.add_oauth_user(email, email, "Google")
        else:
            self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=self.settings["google_oauth"]["key"],
                scope=["email"],
                response_type="code",
                extra_params={"approval_prompt": "auto"},
            )


class TwitterOAuth2LoginHandler(TwitterMixin, OAuth2Handler):
    async def get(self):
        if self.get_argument("oauth_token", None):
            user = await self.get_authenticated_user()
            username = user["username"]
            id_str = user["id_str"]
            self.add_oauth_user(username, id_str, "Twitter")
        else:
            await self.authorize_redirect(extra_params={"x_auth_access_type": "read"})


class FacebookAuth2LoginHandler(OAuth2Handler):
    _OAUTH_AUTHORIZE_URL = "https://www.facebook.com/v16.0/dialog/oauth"
    _OAUTH_ACCESS_TOKEN_URL = "https://graph.facebook.com/oauth/access_token"
    _OAUTH_API_REQUEST_URL = "https://graph.facebook.com/me"

    def get(self):
        client_id, client_secret, redirect_uri = self.get_secret("fb_oauth")
        code = self.get_argument("code", None)
        if code:
            access = self.get_authenticated_user(client_id, client_secret, code, {"redirect_uri": redirect_uri})
            resp = self.oauth2_sync_request(access["access_token"], {"fields": "name,id"})
            # Facebook doesn't allow to get email except for business accounts
            uid = resp["id"]
            email = "{}_{}".format(resp["name"], uid)
            self.add_oauth_user(email, uid, "Facebook")

        else:
            self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=client_id,
            )
