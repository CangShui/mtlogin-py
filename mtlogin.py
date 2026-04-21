#!/usr/bin/env python3
import base64
import argparse
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import sys
import threading
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl, urlencode

import pyotp
import requests as std_requests
from croniter import croniter
from curl_cffi import requests

DB_KEY = "m-team-auth"
DID_KEY = "m-team-did"
VISITOR_ID_KEY = "m-team-visitorid"
SIGN_SECRET = "HLkPcWmycL57mfJt"
# If you do not want to use environment variables, you can put fixed values
# in LOCAL_CONFIG_OVERRIDES and start with `--use-local-config`.
LOCAL_CONFIG_OVERRIDES: Dict[str, object] = {
    # "username": "your_username",
    # "password": "your_password",
    # "totpsecret": "your_totp_secret",
    # "crontab": "2 */2 * * *",
    # "tgbot_token": "123456:token",
    # "tgbot_chat_id": -1001234567890,
}
LOG_FILE_PATH: Optional[str] = None
SENSITIVE_FIELDS = {
    "password",
    "otpCode",
    "totpsecret",
    "tgbot_token",
    "ntfy_token",
    "qqpush_token",
    "m_team_auth",
}
SENSITIVE_HEADERS = {"authorization"}


def log_info(message: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {message}"
    try:
        print(line, flush=True)
    except UnicodeEncodeError:
        # Fallback for terminals with limited encodings (e.g. Windows gbk).
        print(line.encode("ascii", "backslashreplace").decode("ascii"), flush=True)
    if LOG_FILE_PATH:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as fp:
            fp.write(line + "\n")


def mask_secret(value: Any) -> str:
    text = str(value)
    if not text:
        return ""
    if len(text) <= 8:
        return "*" * len(text)
    return f"{text[:3]}***{text[-3:]}"


def redact_headers(headers: Dict[str, str]) -> Dict[str, str]:
    redacted: Dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() in SENSITIVE_HEADERS:
            redacted[key] = mask_secret(value)
        else:
            redacted[key] = value
    return redacted


def redact_body(data: Any) -> Any:
    if not isinstance(data, str) or "=" not in data:
        return data
    try:
        items = parse_qsl(data, keep_blank_values=True)
    except ValueError:
        return data
    redacted = []
    for key, value in items:
        if key in SENSITIVE_FIELDS:
            redacted.append((key, mask_secret(value)))
        else:
            redacted.append((key, value))
    return urlencode(redacted)


@dataclass
class Config:
    username: str = ""
    password: str = ""
    totpsecret: str = ""
    crontab: str = ""
    proxy: str = ""
    qqpush: str = ""
    qqpush_token: str = ""
    m_team_auth: str = ""
    ua: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
    api_host: str = "api.m-team.io"
    referer: str = "https://kp.m-team.cc/"
    wxcorpid: str = ""
    wxagentsecret: str = ""
    wxagentid: int = 0
    wxuserid: str = "@all"
    timeout: int = 60
    db_path: str = "/data/cookie.db"
    version: str = "1.1.4"
    web_version: str = "1140"
    m_team_did: str = ""
    ding_talk_robot_webhook_token: str = ""
    ding_talk_robot_secret: str = ""
    ding_talk_robot_at_mobiles: str = ""
    tgbot_token: str = ""
    tgbot_chat_id: int = 0
    tgbot_proxy: str = ""
    feishu_webhookurl: str = ""
    feishu_secret: str = ""
    ntfy_url: str = ""
    ntfy_topic: str = ""
    ntfy_user: str = ""
    ntfy_password: str = ""
    ntfy_token: str = ""
    cookie_mode: str = "normal"
    skip_cache: bool = False


@dataclass
class TaskResult:
    success: bool
    message: str
    started_at: str
    finished_at: str
    username: str = ""
    uploaded: str = ""
    downloaded: str = ""
    bonus: str = ""
    last_login: str = ""
    last_browse: str = ""


class KVStore:
    def __init__(self, path: str):
        db_dir = os.path.dirname(path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL)")
        self.conn.commit()
        self.lock = threading.Lock()

    def get(self, key: str) -> Optional[str]:
        with self.lock:
            row = self.conn.execute("SELECT v FROM kv WHERE k=?", (key,)).fetchone()
            return row[0] if row else None

    def put(self, key: str, value: str) -> None:
        with self.lock:
            self.conn.execute("INSERT OR REPLACE INTO kv(k,v) VALUES (?,?)", (key, value))
            self.conn.commit()

    def delete(self, key: str) -> None:
        with self.lock:
            self.conn.execute("DELETE FROM kv WHERE k=?", (key,))
            self.conn.commit()


class MTClient:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.store = KVStore(cfg.db_path)
        self.token = ""
        self.did = cfg.m_team_did
        self.visitorid = self.store.get(VISITOR_ID_KEY) or secrets.token_hex(16)
        self.store.put(VISITOR_ID_KEY, self.visitorid)
        self.uploaded = ""
        self.downloaded = ""
        self.bonus = ""
        self.username = ""
        self.last_login = ""
        self.last_browse = ""

        self.session = requests.Session(impersonate="chrome124")
        if cfg.proxy:
            self.session.proxies = {"http": cfg.proxy, "https": cfg.proxy}

    def _update_did_from_response(self, resp: Any) -> None:
        new_did = resp.headers.get("Did") or resp.headers.get("did")
        if new_did:
            self.did = new_did
            self.store.put(DID_KEY, self.did)

    def _log_http(self, method: str, url: str, req_headers: Dict[str, str], req_data: Any, resp: Any) -> None:
        log_info(f"HTTP {method} {url}")
        log_info(f"Request headers: {json.dumps(redact_headers(req_headers), ensure_ascii=False)}")
        log_info(f"Request body: {redact_body(req_data)}")
        log_info(f"Response status: {resp.status_code}")
        log_info(f"Response headers: {redact_headers(dict(resp.headers))}")
        log_info(f"Response body: {resp.text}")

    def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        data: Any = None,
        timeout: Optional[int] = None,
        allow_redirects: bool = False,
        proxies: Optional[Dict[str, str]] = None,
    ) -> Any:
        resp = self.session.request(
            method=method,
            url=url,
            headers=headers,
            data=data,
            timeout=timeout or self.cfg.timeout,
            allow_redirects=allow_redirects,
            proxies=proxies,
        )
        self._update_did_from_response(resp)
        self._log_http(method, url, headers or {}, data, resp)
        return resp

    def _ts_ms(self) -> int:
        return int(time.time() * 1000)

    def _sign(self, method: str, path: str, ts_ms: int) -> str:
        raw = f"{method}&{path}&{ts_ms}".encode()
        sig = hmac.new(SIGN_SECRET.encode(), raw, hashlib.sha1).digest()
        return base64.b64encode(sig).decode()

    def _headers(self, ts_sec: Optional[int] = None) -> Dict[str, str]:
        if ts_sec is None:
            ts_sec = int(time.time())
        return {
            "User-Agent": self.cfg.ua,
            "referer": self.cfg.referer,
            "origin": self.cfg.referer,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "application/json;charset=UTF-8",
            "Ts": str(ts_sec),
            "version": self.cfg.version,
            "webversion": self.cfg.web_version,
            "Did": self.did,
            "visitorid": self.visitorid,
        }

    def _post(self, path: str, auth: bool = False) -> Any:
        ts = self._ts_ms()
        body = {
            "_timestamp": str(ts),
            "_sgin": self._sign("POST", path, ts),
        }
        headers = self._headers()
        if auth:
            headers["Authorization"] = self.token
        return self._request(
            "POST",
            f"https://{self.cfg.api_host}{path}",
            data=urlencode(body),
            headers=headers,
            timeout=self.cfg.timeout,
            allow_redirects=False,
        )

    def login(self) -> None:
        log_info("Starting login flow")
        ck, did = self.store.get(DB_KEY), self.store.get(DID_KEY)
        if ck and did and not self.cfg.skip_cache:
            self.token, self.did = ck, did
            log_info("Detected local token/did cache, skipping login")
            return
        if self.cfg.skip_cache:
            log_info("skip-cache enabled, forcing fresh login")
        ts = self._ts_ms()
        payload = {
            "username": self.cfg.username,
            "password": self.cfg.password,
            "turnstile": "",
            "_timestamp": str(ts),
            "_sgin": self._sign("POST", "/api/login", ts),
        }
        headers = self._headers()
        headers["Did"] = secrets.token_hex(16)

        resp = self._request(
            "POST",
            f"https://{self.cfg.api_host}/api/login",
            data=urlencode(payload),
            headers=headers,
            timeout=self.cfg.timeout,
            allow_redirects=False,
        )
        data = resp.json()
        if data.get("code") == 1001:
            payload["otpCode"] = pyotp.TOTP(self.cfg.totpsecret).now()
            resp = self._request(
                "POST",
                f"https://{self.cfg.api_host}/api/login",
                data=urlencode(payload),
                headers=headers,
                timeout=self.cfg.timeout,
                allow_redirects=False,
            )
            data = resp.json()
        if resp.status_code != 200 or data.get("message") != "SUCCESS":
            raise RuntimeError(f"Login failed: status={resp.status_code}, body={resp.text}")
        self.token = resp.headers.get("Authorization", "")
        self.did = resp.headers.get("Did") or resp.headers.get("did") or self.did
        self.store.put(DB_KEY, self.token)
        self.store.put(DID_KEY, self.did)
        log_info("Login succeeded and local token/did cache has been updated")

    def _func_state(self) -> None:
        for path, method in [
            ("/api/system/unix", "GET"),
            ("/ping", "GET"),
            ("/api/laboratory/funcState", "POST"),
            ("/api/fun/first", "POST"),
            ("/api/system/state", "POST"),
            ("/api/links/view", "POST"),
            ("/api/msg/statistic", "POST"),
        ]:
            if method == "GET":
                self._request("GET", f"https://{self.cfg.api_host}{path}", headers=self._headers(), timeout=self.cfg.timeout)
            else:
                self._post(path, auth=True)

    def check(self) -> None:
        log_info("Starting account status check")
        if self.cfg.m_team_auth:
            self.token = self.cfg.m_team_auth
            log_info("Using M_TEAM_AUTH for authentication")
        self._func_state()
        profile = self._post("/api/member/profile", auth=True)
        data = profile.json()
        if data.get("code") == 401:
            self.store.delete(DB_KEY)
            raise RuntimeError("Full authentication is required to access this resource")
        if data.get("message") != "SUCCESS":
            raise RuntimeError(f"Cookie is invalid or expired: {profile.text}")
        member = data.get("data", {}).get("memberCount", {})
        status = data.get("data", {}).get("memberStatus", {})
        self.uploaded = f"{int(member.get('uploaded', 0))/1073741824:.2f} Gb"
        self.downloaded = f"{int(member.get('downloaded', 0))/1073741824:.2f} Gb"
        self.bonus = str(member.get("bonus", ""))
        self.username = data.get("data", {}).get("username", "")
        self.last_login = status.get("lastLogin", "")
        self.last_browse = status.get("lastBrowse", "")
        self._func_state()
        updated = self._post("/api/member/updateLastBrowse", auth=True).json()
        if updated.get("message") != "SUCCESS":
            raise RuntimeError("Connected successfully, but failed to update status")
        log_info("Status check succeeded, last browse has been refreshed")


class JobServer:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.client = MTClient(cfg)
        self.failed = 0

    def _proxies(self, override: str = "") -> Optional[Dict[str, str]]:
        proxy = override or self.cfg.proxy
        if not proxy:
            return None
        return {"http": proxy, "https": proxy}

    def run_once(self) -> TaskResult:
        started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_info("Task execution started")
        try:
            if not self.cfg.m_team_auth and not self.cfg.m_team_did:
                self.client.login()
            self.client.check()
            self.failed = 0
            self.notify_success()
            log_info("Task execution succeeded")
            return TaskResult(
                success=True,
                message="Task execution succeeded",
                started_at=started_at,
                finished_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                username=self.client.username,
                uploaded=self.client.uploaded,
                downloaded=self.client.downloaded,
                bonus=self.client.bonus,
                last_login=self.client.last_login,
                last_browse=self.client.last_browse,
            )
        except Exception as exc:
            self.failed += 1
            if self.cfg.cookie_mode == "strict" or self.failed > 5:
                self.client.store.delete(DB_KEY)
                log_info("Triggered local token cleanup")
            self.notify_error(str(exc))
            log_info(f"Task execution failed: {exc}")
            return TaskResult(
                success=False,
                message=str(exc),
                started_at=started_at,
                finished_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                username=self.client.username,
                uploaded=self.client.uploaded,
                downloaded=self.client.downloaded,
                bonus=self.client.bonus,
                last_login=self.client.last_login,
                last_browse=self.client.last_browse,
            )

    def loop(self) -> None:
        if not self.cfg.crontab:
            raise ValueError("CRONTAB is required for scheduled mode")
        if not croniter.is_valid(self.cfg.crontab):
            raise ValueError(f"Invalid CRONTAB expression: {self.cfg.crontab}")

        schedule = croniter(self.cfg.crontab, datetime.now())
        log_info(f"Schedule mode enabled, CRONTAB={self.cfg.crontab}")
        while True:
            next_at = schedule.get_next(datetime)
            sleep_s = max(0, (next_at - datetime.now()).total_seconds())
            log_info(f"Next run at {next_at.strftime('%Y-%m-%d %H:%M:%S')}, sleeping {int(sleep_s)} seconds")
            time.sleep(sleep_s)
            self.run_once()

    def notify_success(self) -> None:
        msg = (
            f"m-team account {self.client.username} refresh succeeded\n"
            f"Uploaded: {self.client.uploaded}\nDownloaded: {self.client.downloaded}\n"
            f"Bonus: {self.client.bonus}\nLast login: {self.client.last_login}\nLast browse: {self.client.last_browse}"
        )
        self._notify(msg)

    def notify_error(self, err: str) -> None:
        self._notify(f"m-team login failed err={err}")

    def _notify(self, message: str) -> None:
        if self.cfg.qqpush:
            resp = std_requests.get(
                f"https://qmsg.zendee.cn/send/{self.cfg.qqpush_token}",
                params={"msg": message, "qq": self.cfg.qqpush},
                proxies=self._proxies(),
                timeout=10,
            )
            log_info(f"QQPush status={resp.status_code} body={resp.text}")
        if self.cfg.feishu_webhookurl:
            resp = std_requests.post(
                self.cfg.feishu_webhookurl,
                json={"msg_type": "text", "content": {"text": message}},
                proxies=self._proxies(),
                timeout=10,
            )
            log_info(f"Feishu status={resp.status_code} body={resp.text}")
        if self.cfg.tgbot_token and self.cfg.tgbot_chat_id:
            tg_api = f"https://api.telegram.org/bot{self.cfg.tgbot_token}/sendMessage"
            proxies = self._proxies(self.cfg.tgbot_proxy)
            resp = std_requests.post(
                tg_api,
                data={"chat_id": str(self.cfg.tgbot_chat_id), "text": message},
                proxies=proxies,
                timeout=10,
            )
            log_info(f"Telegram status={resp.status_code} body={resp.text}")
        if self.cfg.ntfy_url and self.cfg.ntfy_topic:
            headers = {}
            if self.cfg.ntfy_token:
                headers["Authorization"] = f"Bearer {self.cfg.ntfy_token}"
            elif self.cfg.ntfy_user and self.cfg.ntfy_password:
                tok = base64.b64encode(f"{self.cfg.ntfy_user}:{self.cfg.ntfy_password}".encode()).decode()
                headers["Authorization"] = f"Basic {tok}"
            resp = std_requests.post(
                f"{self.cfg.ntfy_url.rstrip('/')}/{self.cfg.ntfy_topic}",
                data=message.encode(),
                headers=headers,
                proxies=self._proxies(),
                timeout=10,
            )
            log_info(f"Ntfy status={resp.status_code} body={resp.text}")


def env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    return int(v) if v not in (None, "") else default


def load_config() -> Config:
    return Config(
        username=os.getenv("USERNAME", ""),
        password=os.getenv("PASSWORD", ""),
        totpsecret=os.getenv("TOTPSECRET", ""),
        crontab=os.getenv("CRONTAB", ""),
        proxy=os.getenv("PROXY", ""),
        qqpush=os.getenv("QQPUSH", ""),
        qqpush_token=os.getenv("QQPUSH_TOKEN", ""),
        m_team_auth=os.getenv("M_TEAM_AUTH", ""),
        ua=os.getenv("UA", Config.ua),
        api_host=os.getenv("API_HOST", "api.m-team.io"),
        referer=os.getenv("API_REFERER", "https://kp.m-team.cc/"),
        wxcorpid=os.getenv("WXCORPID", ""),
        wxagentsecret=os.getenv("WXAGENTSECRET", ""),
        wxagentid=env_int("WXAGENTID", 0),
        wxuserid=os.getenv("WXUSERID", "@all"),
        timeout=env_int("TIME_OUT", 60),
        db_path=os.getenv("DB_PATH", "/data/cookie.db"),
        version=os.getenv("VERSION", "1.1.4"),
        web_version=os.getenv("WEB_VERSION", "1140"),
        m_team_did=os.getenv("M_TEAM_DID", ""),
        ding_talk_robot_webhook_token=os.getenv("DING_TALK_ROBOT_WEBHOOK_TOKEN", ""),
        ding_talk_robot_secret=os.getenv("DING_TALK_ROBOT_SECRET", ""),
        ding_talk_robot_at_mobiles=os.getenv("DING_TALK_ROBOT_AT_MOBILES", ""),
        tgbot_token=os.getenv("TGBOT_TOKEN", ""),
        tgbot_chat_id=env_int("TGBOT_CHAT_ID", 0),
        tgbot_proxy=os.getenv("TGBOT_PROXY", ""),
        feishu_webhookurl=os.getenv("FEISHU_WEBHOOKURL", ""),
        feishu_secret=os.getenv("FEISHU_SECRET", ""),
        ntfy_url=os.getenv("NTFY_URL", ""),
        ntfy_topic=os.getenv("NTFY_TOPIC", ""),
        ntfy_user=os.getenv("NTFY_USER", ""),
        ntfy_password=os.getenv("NTFY_PASSWORD", ""),
        ntfy_token=os.getenv("NTFY_TOKEN", ""),
        cookie_mode=os.getenv("COOKIE_MODE", "normal"),
    )


def clone_config(cfg: Config) -> Config:
    return deepcopy(cfg)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="m-team keepalive script (Python)")
    parser.add_argument("--username")
    parser.add_argument("--password")
    parser.add_argument("--totpsecret")
    parser.add_argument("--crontab", help="Cron expression for scheduled execution, for example '2 */2 * * *'")
    parser.add_argument("--m-team-auth")
    parser.add_argument("--m-team-did")
    parser.add_argument("--proxy", help="HTTP/HTTPS proxy URL, for example http://127.0.0.1:3301")
    parser.add_argument("--api-host")
    parser.add_argument("--api-referer")
    parser.add_argument("--tgbot-token")
    parser.add_argument("--tgbot-chat-id", type=int)
    parser.add_argument("--db-path")
    parser.add_argument("--skip-cache", action="store_true", help="Force fresh login and ignore local token/did cache")
    parser.add_argument("--use-local-config", action="store_true")
    parser.add_argument("--verbose-config", action="store_true", help="Print key startup config (with sensitive fields hidden)")
    parser.add_argument("--log-file", help="Log file path; when set, logs are written to both stdout and file")
    return parser.parse_args()


def apply_overrides(cfg: Config, args: argparse.Namespace) -> Config:
    if args.use_local_config and LOCAL_CONFIG_OVERRIDES:
        for k, v in LOCAL_CONFIG_OVERRIDES.items():
            if hasattr(cfg, k) and v not in (None, ""):
                setattr(cfg, k, v)

    mapping = {
        "username": args.username,
        "password": args.password,
        "totpsecret": args.totpsecret,
        "crontab": args.crontab,
        "m_team_auth": args.m_team_auth,
        "m_team_did": args.m_team_did,
        "proxy": args.proxy,
        "api_host": args.api_host,
        "referer": args.api_referer,
        "tgbot_token": args.tgbot_token,
        "tgbot_chat_id": args.tgbot_chat_id,
        "db_path": args.db_path,
    }
    for field, value in mapping.items():
        if value not in (None, ""):
            setattr(cfg, field, value)
    if args.skip_cache:
        cfg.skip_cache = True
    return cfg


if __name__ == "__main__":
    args = parse_args()
    LOG_FILE_PATH = args.log_file
    cfg = apply_overrides(load_config(), args)
    if args.verbose_config:
        log_info(
            "Startup config: "
            + json.dumps(
                {
                    "api_host": cfg.api_host,
                    "crontab": cfg.crontab,
                    "db_path": cfg.db_path,
                    "skip_cache": cfg.skip_cache,
                    "has_username": bool(cfg.username),
                    "has_password": bool(cfg.password),
                    "has_totpsecret": bool(cfg.totpsecret),
                    "has_m_team_auth": bool(cfg.m_team_auth),
                    "has_tgbot_token": bool(cfg.tgbot_token),
                    "tgbot_chat_id": cfg.tgbot_chat_id,
                },
                ensure_ascii=False,
            )
        )
    job = JobServer(cfg)
    if cfg.crontab:
        job.loop()
    else:
        job.run_once()
        log_info("Single-run execution completed, exiting")
    sys.exit(0)

