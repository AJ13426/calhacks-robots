"""Tiny client for the SpacetimeDB "hivemind" database over its HTTP API.

Only uses the Python standard library, so there is nothing to install.
  hive = Hive()
  hive.call("create_job", "pick_up", "orange cube", 60, 70, 3, 0)
  rows = hive.sql("SELECT * FROM job WHERE status = 'open'")
"""
import json
import os
import re
import urllib.error
import urllib.request

HOST = os.environ.get("SPACETIME_HOST", "http://127.0.0.1:3100")
DB = os.environ.get("SPACETIME_DB", "hivemind")


class HiveError(Exception):
    pass


def _snake(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _decode(value, typ):
    """Turn SpacetimeDB's JSON values into plain Python values."""
    if isinstance(typ, dict) and len(typ) == 1:
        kind, inner = next(iter(typ.items()))
        if kind == "Sum" and isinstance(value, dict) and len(value) == 1:  # option: {"some": v} or {"none": []}
            tag, v = next(iter(value.items()))
            return None if tag in ("none", "1") else v
        if kind == "Product" and isinstance(value, list) and len(value) == 1:  # timestamps and similar wrappers
            return value[0]
    return value


class Hive:
    def __init__(self, host=HOST, db=DB):
        self.host = host.rstrip("/")
        self.db = db
        self.token = None
        try:
            self.token = self._request("POST", "/v1/identity", None).get("token")
        except Exception:
            self.token = None  # anonymous still works for calls and public tables

    def _request(self, method, path, body, raw=False):
        data = None
        headers = {}
        if body is not None:
            if isinstance(body, str):
                data = body.encode()
                headers["Content-Type"] = "text/plain"
            else:
                data = json.dumps(body).encode()
                headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(self.host + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                text = resp.read().decode()
        except urllib.error.HTTPError as e:
            raise HiveError(f"{method} {path} failed ({e.code}): {e.read().decode()[:500]}") from None
        except urllib.error.URLError as e:
            raise HiveError(f"Cannot reach SpacetimeDB at {self.host}. Is 'spacetime start' running? ({e.reason})") from None
        if raw:
            return text
        return json.loads(text) if text.strip() else {}

    def call(self, reducer, *args):
        """Call a reducer. Arguments go in the same order as in the module."""
        return self._request("POST", f"/v1/database/{self.db}/call/{reducer}", list(args), raw=True)

    def sql(self, query):
        """Run SQL and get back a list of dicts, one per row."""
        results = self._request("POST", f"/v1/database/{self.db}/sql", query)
        out = []
        for stmt in results:
            elements = stmt["schema"]["elements"]
            names, types = [], []
            for el in elements:
                n = el.get("name")
                if isinstance(n, dict):
                    n = n.get("some")
                names.append(_snake(n or ""))
                types.append(el.get("algebraic_type"))
            for row in stmt["rows"]:
                out.append({names[i]: _decode(row[i], types[i]) for i in range(len(names))})
        return out


if __name__ == "__main__":
    h = Hive()
    for table in ("robot", "job", "bid", "assignment", "thought"):
        print(f"--- {table}")
        for r in h.sql(f"SELECT * FROM {table}"):
            print(r)
