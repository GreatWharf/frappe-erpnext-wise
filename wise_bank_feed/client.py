"""GET-only Wise client. Errors exclude raw financial payloads and authentication headers."""

import json
import re
import time

import requests


class WiseError(Exception):
    def __init__(self, message, status=None, sca=False):
        super().__init__(message)
        self.status, self.sca = status, sca


class WiseClient:
    def __init__(self, token, environment="Production", session=None):
        if environment not in ("Production", "Sandbox"):
            raise ValueError("Invalid environment.")
        if not token or any(c.isspace() for c in token):
            raise ValueError("Missing or malformed API token.")
        self.token = token
        self.deadline = time.monotonic() + 700
        self.base = (
            "https://api.wise.com" if environment == "Production" else "https://api.wise-sandbox.com"
        ) + "/2026Q3"
        self.session = session or requests.Session()
        self.session.trust_env = False

    def close(self):
        self.session.close()

    def get(self, path, params=None):
        if not re.fullmatch(
            r"/profiles(?:/\d+/(?:activities|balances|balance-statements/\d+/statement\.json))?", path
        ):
            raise ValueError("Endpoint is not allowlisted.")
        for attempt in range(3):
            if time.monotonic() > self.deadline:
                raise WiseError("Wise request time budget exceeded; checkpoint not advanced.")
            try:
                r = self.session.get(
                    self.base + path,
                    params=params,
                    headers={"Authorization": "Bearer " + self.token, "Accept": "application/json"},
                    timeout=(10, 30),
                    allow_redirects=False,
                )
            except requests.ConnectionError, requests.Timeout:
                if attempt < 2:
                    time.sleep(2**attempt)
                    continue
                raise WiseError("Wise network request failed; retry later.") from None
            except requests.RequestException:
                raise WiseError("Wise network request failed; retry later.") from None
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                delay = r.headers.get("Retry-After", "")
                if delay and (not delay.isdigit() or int(delay) > 10):
                    raise WiseError("Wise rate limit; retry on a later scheduled run.", r.status_code)
                time.sleep(max(2**attempt, int(delay or 0)))
                continue
            if r.status_code != 200:
                sca = bool(r.headers.get("x-2fa-approval"))
                raise WiseError(
                    "Wise requires additional authentication." if sca else f"Wise HTTP {r.status_code}.",
                    r.status_code,
                    sca,
                )
            if len(r.content) > 8 * 1024 * 1024:
                raise WiseError("Wise response exceeds 8 MiB.")
            try:
                return json.loads(r.content, parse_float=str)
            except ValueError, UnicodeError:
                raise WiseError("Wise returned invalid JSON.") from None

    @staticmethod
    def ident(value):
        if not re.fullmatch(r"\d+", str(value)):
            raise ValueError("Wise ID must be numeric.")
        return str(value)

    def profiles(self):
        result = self.get("/profiles")
        if not isinstance(result, list):
            raise WiseError("Unexpected profiles schema.")
        return result

    def balances(self, profile):
        result = self.get(f"/profiles/{self.ident(profile)}/balances", {"types": "STANDARD,SAVINGS"})
        if not isinstance(result, list):
            raise WiseError("Unexpected balances schema.")
        return result

    def activities(self, profile, start, end):
        params = {"since": start, "until": end, "size": 100}
        seen = set()
        for _ in range(100):
            data = self.get(f"/profiles/{self.ident(profile)}/activities", dict(params))
            if (
                not isinstance(data, dict)
                or not isinstance(data.get("activities"), list)
                or "cursor" not in data
            ):
                raise WiseError("Unexpected activity schema.")
            yield from data["activities"]
            cursor = data.get("cursor")
            if cursor is None:
                return
            if not isinstance(cursor, str) or not cursor or cursor in seen:
                raise WiseError("Wise pagination did not advance.")
            seen.add(cursor)
            params["nextCursor"] = cursor
        raise WiseError("Activity page limit reached; checkpoint not advanced.")

    def statement(self, profile, balance, currency, start, end):
        data = self.get(
            f"/profiles/{self.ident(profile)}/balance-statements/{self.ident(balance)}/statement.json",
            {"currency": currency, "intervalStart": start, "intervalEnd": end, "type": "COMPACT"},
        )
        if not isinstance(data, dict) or not isinstance(data.get("transactions"), list):
            raise WiseError("Unexpected statement schema.")
        return data["transactions"]
