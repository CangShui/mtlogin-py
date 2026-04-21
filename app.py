#!/usr/bin/env python3
import argparse
import json
import os
import secrets
import threading
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List, Optional

import requests as std_requests
import mtlogin
from croniter import croniter
from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from mtlogin import Config, JobServer, KVStore, TaskResult, clone_config, load_config, log_info

LEGACY_TASK_SETTINGS_KEY = "web:task_settings"
ADMIN_SETTINGS_KEY = "web:admin_settings"
RUNTIME_STATE_KEY = "web:runtime_state"

DEFAULT_MT_CODE = "mt"
DEFAULT_MT_NAME = "M-Team"
DEFAULT_MT_API_HOST = "api.m-team.io"
DEFAULT_MT_REFERER = "https://kp.m-team.cc/"

CHANNEL_TYPE_TG = "tg"
ACCOUNT_SECRET_FIELDS = {"password", "totpsecret", "m_team_auth"}
CHANNEL_SECRET_FIELDS = {"tgbot_token"}
BOOL_FIELDS = {"enabled", "skip_cache"}
ADMIN_NAV_ITEMS = [
    {"page": "accounts", "endpoint": "accounts_page", "label": "账户管理"},
    {"page": "platforms", "endpoint": "platforms_page", "label": "平台配置"},
    {"page": "notifications", "endpoint": "notifications_page", "label": "通知管理"},
    {"page": "history", "endpoint": "history_page", "label": "执行记录"},
    {"page": "settings", "endpoint": "settings_page", "label": "系统设置"},
]


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_int(value: Any, field_name: str, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} 必须是整数。") from exc


def parse_datetime_filter(value: str, field_name: str) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} 格式无效。") from exc
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "on", "yes"}


def safe_int(value: str) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def next_run_text(crontab_expr: Any) -> str:
    expr = str(crontab_expr or "").strip()
    if not expr or not croniter.is_valid(expr):
        return ""
    return croniter(expr, datetime.now()).get_next(datetime).strftime("%Y-%m-%d %H:%M:%S")


class SettingsStore:
    def __init__(self, db_path: str):
        self.kv = KVStore(db_path)
        self.kv.execute("PRAGMA foreign_keys = ON")
        self._init_schema()
        self._ensure_builtin_platform()
        self._migrate_legacy_task_settings()

    def _row_to_dict(self, row: Any) -> Dict[str, Any]:
        return dict(row) if row else {}

    def _rows_to_dicts(self, rows: List[Any]) -> List[Dict[str, Any]]:
        return [dict(row) for row in rows]

    def _get_json(self, key: str, default: Dict[str, Any]) -> Dict[str, Any]:
        raw = self.kv.get(key)
        if not raw:
            return default.copy()
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return default.copy()
        return value if isinstance(value, dict) else default.copy()

    def _put_json(self, key: str, value: Dict[str, Any]) -> None:
        self.kv.put(key, json.dumps(value, ensure_ascii=False))

    def _init_schema(self) -> None:
        statements = [
            """
            CREATE TABLE IF NOT EXISTS platforms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                api_host TEXT NOT NULL,
                referer TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                builtin INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS notification_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                tgbot_token TEXT NOT NULL DEFAULT '',
                tgbot_chat_id INTEGER NOT NULL DEFAULT 0,
                tgbot_proxy TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                platform_id INTEGER NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                username TEXT NOT NULL DEFAULT '',
                password TEXT NOT NULL DEFAULT '',
                totpsecret TEXT NOT NULL DEFAULT '',
                m_team_auth TEXT NOT NULL DEFAULT '',
                m_team_did TEXT NOT NULL DEFAULT '',
                proxy TEXT NOT NULL DEFAULT '',
                crontab TEXT NOT NULL DEFAULT '',
                timeout INTEGER NOT NULL DEFAULT 60,
                cookie_mode TEXT NOT NULL DEFAULT 'normal',
                skip_cache INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(platform_id) REFERENCES platforms(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS account_notifications (
                account_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                PRIMARY KEY(account_id, channel_id),
                FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                FOREIGN KEY(channel_id) REFERENCES notification_channels(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS execution_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                platform_id INTEGER NOT NULL,
                trigger_mode TEXT NOT NULL,
                status TEXT NOT NULL,
                result_message TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                run_username TEXT NOT NULL DEFAULT '',
                uploaded TEXT NOT NULL DEFAULT '',
                downloaded TEXT NOT NULL DEFAULT '',
                bonus TEXT NOT NULL DEFAULT '',
                last_login TEXT NOT NULL DEFAULT '',
                last_browse TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES accounts(id),
                FOREIGN KEY(platform_id) REFERENCES platforms(id)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_platforms_enabled ON platforms(enabled)",
            "CREATE INDEX IF NOT EXISTS idx_channels_enabled ON notification_channels(enabled)",
            "CREATE INDEX IF NOT EXISTS idx_accounts_enabled ON accounts(enabled)",
            "CREATE INDEX IF NOT EXISTS idx_accounts_platform_id ON accounts(platform_id)",
            "CREATE INDEX IF NOT EXISTS idx_exec_account_started ON execution_records(account_id, started_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_exec_platform_started ON execution_records(platform_id, started_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_exec_status_started ON execution_records(status, started_at DESC)",
        ]
        for statement in statements:
            self.kv.execute(statement)

    def _ensure_builtin_platform(self) -> None:
        created_at = now_text()
        self.kv.execute(
            """
            INSERT OR IGNORE INTO platforms(code, name, api_host, referer, enabled, builtin, created_at, updated_at)
            VALUES (?, ?, ?, ?, 1, 1, ?, ?)
            """,
            (DEFAULT_MT_CODE, DEFAULT_MT_NAME, DEFAULT_MT_API_HOST, DEFAULT_MT_REFERER, created_at, created_at),
        )
        self.kv.execute(
            """
            UPDATE platforms
            SET name = ?, api_host = ?, referer = ?, builtin = 1, updated_at = ?
            WHERE code = ?
            """,
            (DEFAULT_MT_NAME, DEFAULT_MT_API_HOST, DEFAULT_MT_REFERER, now_text(), DEFAULT_MT_CODE),
        )

    def _legacy_settings_exist(self, legacy: Dict[str, Any]) -> bool:
        fields = [
            "username",
            "password",
            "totpsecret",
            "m_team_auth",
            "m_team_did",
            "proxy",
            "crontab",
            "timeout",
            "cookie_mode",
            "skip_cache",
            "tgbot_token",
            "tgbot_chat_id",
            "tgbot_proxy",
        ]
        return any(str(legacy.get(field, "")).strip() for field in fields)

    def _migrate_legacy_task_settings(self) -> None:
        count_row = self.kv.fetchone("SELECT COUNT(*) AS count FROM accounts")
        if count_row and int(count_row["count"]) > 0:
            return

        legacy = self._get_json(LEGACY_TASK_SETTINGS_KEY, {})
        if not legacy or not self._legacy_settings_exist(legacy):
            return

        platform = self.get_platform_by_code(DEFAULT_MT_CODE)
        if not platform:
            return

        account_name = str(legacy.get("username") or "").strip() or "migrated-account"
        account_payload = {
            "name": account_name,
            "platform_id": platform["id"],
            "enabled": True,
            "username": str(legacy.get("username") or "").strip(),
            "password": str(legacy.get("password") or ""),
            "totpsecret": str(legacy.get("totpsecret") or ""),
            "m_team_auth": str(legacy.get("m_team_auth") or ""),
            "m_team_did": str(legacy.get("m_team_did") or "").strip(),
            "proxy": str(legacy.get("proxy") or "").strip(),
            "crontab": str(legacy.get("crontab") or "").strip(),
            "timeout": parse_int(legacy.get("timeout"), "timeout", 60),
            "cookie_mode": str(legacy.get("cookie_mode") or "normal").strip() or "normal",
            "skip_cache": truthy(legacy.get("skip_cache")),
        }
        channel_ids: List[int] = []
        if any(str(legacy.get(field, "")).strip() for field in ("tgbot_token", "tgbot_chat_id", "tgbot_proxy")):
            channel_id = self.save_notification_channel(
                {
                    "name": "migrated-tg",
                    "type": CHANNEL_TYPE_TG,
                    "enabled": True,
                    "tgbot_token": str(legacy.get("tgbot_token") or ""),
                    "tgbot_chat_id": legacy.get("tgbot_chat_id") or 0,
                    "tgbot_proxy": str(legacy.get("tgbot_proxy") or "").strip(),
                }
            )
            channel_ids.append(channel_id)
        self.save_account(account_payload, channel_ids)

    def load_admin_settings(self) -> Dict[str, Any]:
        return self._get_json(ADMIN_SETTINGS_KEY, {})

    def ensure_admin(self, username: str, password: str) -> None:
        current = self.load_admin_settings()
        if current.get("username") and current.get("password_hash"):
            return
        self._put_json(
            ADMIN_SETTINGS_KEY,
            {
                "username": username,
                "password_hash": generate_password_hash(password),
            },
        )

    def verify_admin(self, username: str, password: str) -> bool:
        current = self.load_admin_settings()
        saved_username = current.get("username", "")
        saved_hash = current.get("password_hash", "")
        return bool(saved_username and saved_hash and username == saved_username and check_password_hash(saved_hash, password))

    def update_admin(self, username: str, password: str = "") -> None:
        current = self.load_admin_settings()
        payload = {
            "username": username or current.get("username", "admin"),
            "password_hash": current.get("password_hash", ""),
        }
        if password:
            payload["password_hash"] = generate_password_hash(password)
        self._put_json(ADMIN_SETTINGS_KEY, payload)

    def load_runtime_state(self) -> Dict[str, Any]:
        return self._get_json(RUNTIME_STATE_KEY, {})

    def save_runtime_state(self, state: Dict[str, Any]) -> None:
        self._put_json(RUNTIME_STATE_KEY, state)

    def list_platforms(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM platforms"
        params: List[Any] = []
        if enabled_only:
            sql += " WHERE enabled = 1"
        sql += " ORDER BY builtin DESC, name ASC, id ASC"
        return self._rows_to_dicts(self.kv.fetchall(sql, tuple(params)))

    def get_platform(self, platform_id: int) -> Dict[str, Any]:
        return self._row_to_dict(self.kv.fetchone("SELECT * FROM platforms WHERE id = ?", (platform_id,)))

    def get_platform_by_code(self, code: str) -> Dict[str, Any]:
        return self._row_to_dict(self.kv.fetchone("SELECT * FROM platforms WHERE code = ?", (code,)))

    def set_platform_enabled(self, platform_id: int, enabled: bool) -> None:
        platform = self.get_platform(platform_id)
        if not platform:
            raise ValueError("平台不存在。")
        self.kv.execute("UPDATE platforms SET enabled = ?, updated_at = ? WHERE id = ?", (1 if enabled else 0, now_text(), platform_id))

    def list_notification_channels(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM notification_channels"
        params: List[Any] = []
        if enabled_only:
            sql += " WHERE enabled = 1"
        sql += " ORDER BY id DESC"
        return self._rows_to_dicts(self.kv.fetchall(sql, tuple(params)))

    def get_notification_channel(self, channel_id: int) -> Dict[str, Any]:
        return self._row_to_dict(self.kv.fetchone("SELECT * FROM notification_channels WHERE id = ?", (channel_id,)))

    def save_notification_channel(self, payload: Dict[str, Any], channel_id: Optional[int] = None) -> int:
        current = self.get_notification_channel(channel_id) if channel_id else {}
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("通知渠道名称不能为空。")
        channel_type = str(payload.get("type") or current.get("type") or CHANNEL_TYPE_TG).strip().lower()
        if channel_type != CHANNEL_TYPE_TG:
            raise ValueError("当前只支持 tg 通知渠道。")

        token = str(payload.get("tgbot_token") or "").strip()
        if not token and current:
            token = str(current.get("tgbot_token") or "")
        chat_id = parse_int(payload.get("tgbot_chat_id"), "Telegram Chat ID", int(current.get("tgbot_chat_id") or 0))
        proxy = str(payload.get("tgbot_proxy") or "").strip()
        enabled = truthy(payload.get("enabled", current.get("enabled", True)))
        stamp = now_text()

        if channel_id and not current:
            raise ValueError("通知渠道不存在。")

        if channel_id:
            self.kv.execute(
                """
                UPDATE notification_channels
                SET name = ?, type = ?, enabled = ?, tgbot_token = ?, tgbot_chat_id = ?, tgbot_proxy = ?, updated_at = ?
                WHERE id = ?
                """,
                (name, channel_type, 1 if enabled else 0, token, chat_id, proxy, stamp, channel_id),
            )
            return channel_id

        cur = self.kv.execute(
            """
            INSERT INTO notification_channels(name, type, enabled, tgbot_token, tgbot_chat_id, tgbot_proxy, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, channel_type, 1 if enabled else 0, token, chat_id, proxy, stamp, stamp),
        )
        return int(cur.lastrowid)

    def set_notification_channel_enabled(self, channel_id: int, enabled: bool) -> None:
        channel = self.get_notification_channel(channel_id)
        if not channel:
            raise ValueError("通知渠道不存在。")
        self.kv.execute(
            "UPDATE notification_channels SET enabled = ?, updated_at = ? WHERE id = ?",
            (1 if enabled else 0, now_text(), channel_id),
        )

    def get_account_notification_ids(self, account_id: int) -> List[int]:
        rows = self.kv.fetchall("SELECT channel_id FROM account_notifications WHERE account_id = ? ORDER BY channel_id ASC", (account_id,))
        return [int(row["channel_id"]) for row in rows]

    def list_account_notification_channels(self, account_id: int, enabled_only: bool = False) -> List[Dict[str, Any]]:
        sql = """
        SELECT nc.*
        FROM notification_channels nc
        INNER JOIN account_notifications an ON an.channel_id = nc.id
        WHERE an.account_id = ?
        """
        params: List[Any] = [account_id]
        if enabled_only:
            sql += " AND nc.enabled = 1"
        sql += " ORDER BY nc.id ASC"
        return self._rows_to_dicts(self.kv.fetchall(sql, tuple(params)))

    def _latest_record_subquery(self) -> str:
        return """
        SELECT er1.*
        FROM execution_records er1
        WHERE er1.id = (
            SELECT er2.id
            FROM execution_records er2
            WHERE er2.account_id = er1.account_id
            ORDER BY er2.started_at DESC, er2.id DESC
            LIMIT 1
        )
        """

    def list_accounts_for_dashboard(self) -> List[Dict[str, Any]]:
        sql = f"""
        SELECT
            a.*,
            p.name AS platform_name,
            p.code AS platform_code,
            p.enabled AS platform_enabled,
            COALESCE(group_concat(nc.name, ', '), '') AS notification_names,
            latest.status AS last_status,
            latest.started_at AS last_started_at,
            latest.finished_at AS last_finished_at,
            latest.result_message AS last_message,
            latest.uploaded AS last_uploaded,
            latest.downloaded AS last_downloaded,
            latest.bonus AS last_bonus,
            latest.last_login AS last_login
        FROM accounts a
        INNER JOIN platforms p ON p.id = a.platform_id
        LEFT JOIN account_notifications an ON an.account_id = a.id
        LEFT JOIN notification_channels nc ON nc.id = an.channel_id
        LEFT JOIN ({self._latest_record_subquery()}) latest ON latest.account_id = a.id
        GROUP BY a.id
        ORDER BY a.id DESC
        """
        return self._rows_to_dicts(self.kv.fetchall(sql))

    def list_enabled_accounts_for_scheduler(self) -> List[Dict[str, Any]]:
        sql = """
        SELECT
            a.*,
            p.name AS platform_name,
            p.code AS platform_code,
            p.api_host AS platform_api_host,
            p.referer AS platform_referer,
            p.enabled AS platform_enabled
        FROM accounts a
        INNER JOIN platforms p ON p.id = a.platform_id
        WHERE a.enabled = 1 AND p.enabled = 1
        ORDER BY a.id ASC
        """
        return self._rows_to_dicts(self.kv.fetchall(sql))

    def get_account(self, account_id: int) -> Dict[str, Any]:
        sql = """
        SELECT
            a.*,
            p.name AS platform_name,
            p.code AS platform_code,
            p.api_host AS platform_api_host,
            p.referer AS platform_referer,
            p.enabled AS platform_enabled
        FROM accounts a
        INNER JOIN platforms p ON p.id = a.platform_id
        WHERE a.id = ?
        """
        return self._row_to_dict(self.kv.fetchone(sql, (account_id,)))

    def get_account_with_platform(self, account_id: int, enabled_only: bool = False) -> Dict[str, Any]:
        sql = """
        SELECT
            a.*,
            p.name AS platform_name,
            p.code AS platform_code,
            p.api_host AS platform_api_host,
            p.referer AS platform_referer,
            p.enabled AS platform_enabled
        FROM accounts a
        INNER JOIN platforms p ON p.id = a.platform_id
        WHERE a.id = ?
        """
        params: List[Any] = [account_id]
        if enabled_only:
            sql += " AND a.enabled = 1 AND p.enabled = 1"
        return self._row_to_dict(self.kv.fetchone(sql, tuple(params)))

    def save_account(self, payload: Dict[str, Any], channel_ids: List[int], account_id: Optional[int] = None) -> int:
        current = self.get_account(account_id) if account_id else {}
        if account_id and not current:
            raise ValueError("登录账户不存在。")

        platform_id = parse_int(payload.get("platform_id"), "平台", int(current.get("platform_id") or 0))
        platform = self.get_platform(platform_id)
        if not platform or not int(platform.get("enabled") or 0):
            raise ValueError("必须选择已启用的平台。")

        valid_channel_ids: List[int] = []
        for raw_id in channel_ids:
            channel_id = int(raw_id)
            channel = self.get_notification_channel(channel_id)
            if not channel or not int(channel.get("enabled") or 0):
                raise ValueError("只能绑定已启用的通知渠道。")
            valid_channel_ids.append(channel_id)

        username = str(payload.get("username") or current.get("username") or "").strip()
        name = str(payload.get("name") or "").strip() or username or current.get("name") or f"account-{int(datetime.now().timestamp())}"
        password = str(payload.get("password") or "")
        totpsecret = str(payload.get("totpsecret") or "")
        m_team_auth = str(payload.get("m_team_auth") or "")
        if current:
            if not password:
                password = str(current.get("password") or "")
            if not totpsecret:
                totpsecret = str(current.get("totpsecret") or "")
            if not m_team_auth:
                m_team_auth = str(current.get("m_team_auth") or "")

        m_team_did = str(payload.get("m_team_did") or "").strip()
        proxy = str(payload.get("proxy") or "").strip()
        crontab_expr = str(payload.get("crontab") or "").strip()
        if crontab_expr and not croniter.is_valid(crontab_expr):
            raise ValueError("CRONTAB 表达式无效。")
        timeout = parse_int(payload.get("timeout"), "超时秒数", int(current.get("timeout") or 60 or 60))
        cookie_mode = str(payload.get("cookie_mode") or current.get("cookie_mode") or "normal").strip() or "normal"
        if cookie_mode not in {"normal", "strict"}:
            cookie_mode = "normal"
        enabled = truthy(payload.get("enabled", current.get("enabled", True)))
        skip_cache = truthy(payload.get("skip_cache", current.get("skip_cache", False)))
        stamp = now_text()

        if account_id:
            self.kv.execute(
                """
                UPDATE accounts
                SET name = ?, platform_id = ?, enabled = ?, username = ?, password = ?, totpsecret = ?,
                    m_team_auth = ?, m_team_did = ?, proxy = ?, crontab = ?, timeout = ?, cookie_mode = ?,
                    skip_cache = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    name,
                    platform_id,
                    1 if enabled else 0,
                    username,
                    password,
                    totpsecret,
                    m_team_auth,
                    m_team_did,
                    proxy,
                    crontab_expr,
                    timeout,
                    cookie_mode,
                    1 if skip_cache else 0,
                    stamp,
                    account_id,
                ),
            )
            saved_id = account_id
        else:
            cur = self.kv.execute(
                """
                INSERT INTO accounts(
                    name, platform_id, enabled, username, password, totpsecret, m_team_auth, m_team_did,
                    proxy, crontab, timeout, cookie_mode, skip_cache, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    platform_id,
                    1 if enabled else 0,
                    username,
                    password,
                    totpsecret,
                    m_team_auth,
                    m_team_did,
                    proxy,
                    crontab_expr,
                    timeout,
                    cookie_mode,
                    1 if skip_cache else 0,
                    stamp,
                    stamp,
                ),
            )
            saved_id = int(cur.lastrowid)

        self.kv.execute("DELETE FROM account_notifications WHERE account_id = ?", (saved_id,))
        if valid_channel_ids:
            self.kv.executemany(
                "INSERT INTO account_notifications(account_id, channel_id) VALUES (?, ?)",
                [(saved_id, channel_id) for channel_id in valid_channel_ids],
            )
        return saved_id

    def set_account_enabled(self, account_id: int, enabled: bool) -> None:
        account = self.get_account(account_id)
        if not account:
            raise ValueError("登录账户不存在。")
        self.kv.execute("UPDATE accounts SET enabled = ?, updated_at = ? WHERE id = ?", (1 if enabled else 0, now_text(), account_id))

    def build_account_config(self, base_config: Config, account: Dict[str, Any]) -> Config:
        cfg = clone_config(base_config)
        cfg.username = str(account.get("username") or "")
        cfg.password = str(account.get("password") or "")
        cfg.totpsecret = str(account.get("totpsecret") or "")
        cfg.proxy = str(account.get("proxy") or "")
        cfg.crontab = str(account.get("crontab") or "")
        cfg.m_team_auth = str(account.get("m_team_auth") or "")
        cfg.m_team_did = str(account.get("m_team_did") or "")
        cfg.timeout = int(account.get("timeout") or base_config.timeout or 60)
        cfg.cookie_mode = str(account.get("cookie_mode") or base_config.cookie_mode or "normal")
        cfg.skip_cache = bool(account.get("skip_cache"))
        cfg.api_host = str(account.get("platform_api_host") or DEFAULT_MT_API_HOST)
        cfg.referer = str(account.get("platform_referer") or DEFAULT_MT_REFERER)
        cfg.db_path = base_config.db_path
        cfg.tgbot_token = ""
        cfg.tgbot_chat_id = 0
        cfg.tgbot_proxy = ""
        return cfg

    def create_execution_record(self, account: Dict[str, Any], trigger_mode: str, result: TaskResult) -> int:
        status = "success" if result.success else "error"
        cur = self.kv.execute(
            """
            INSERT INTO execution_records(
                account_id, platform_id, trigger_mode, status, result_message, started_at, finished_at,
                run_username, uploaded, downloaded, bonus, last_login, last_browse, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(account["id"]),
                int(account["platform_id"]),
                trigger_mode,
                status,
                result.message,
                result.started_at,
                result.finished_at,
                result.username,
                result.uploaded,
                result.downloaded,
                result.bonus,
                result.last_login,
                result.last_browse,
                now_text(),
            ),
        )
        return int(cur.lastrowid)

    def list_execution_records(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        sql = """
        SELECT
            er.*,
            a.name AS account_name,
            a.username AS account_username,
            p.name AS platform_name,
            p.code AS platform_code
        FROM execution_records er
        INNER JOIN accounts a ON a.id = er.account_id
        INNER JOIN platforms p ON p.id = er.platform_id
        """
        where: List[str] = []
        params: List[Any] = []

        account_id = str(filters.get("account_id") or "").strip()
        if account_id:
            where.append("er.account_id = ?")
            params.append(parse_int(account_id, "账户"))

        platform_id = str(filters.get("platform_id") or "").strip()
        if platform_id:
            where.append("er.platform_id = ?")
            params.append(parse_int(platform_id, "平台"))

        status = str(filters.get("status") or "").strip()
        if status in {"success", "error"}:
            where.append("er.status = ?")
            params.append(status)

        started_from = parse_datetime_filter(str(filters.get("started_from") or "").strip(), "开始时间")
        if started_from:
            where.append("er.started_at >= ?")
            params.append(started_from)

        started_to = parse_datetime_filter(str(filters.get("started_to") or "").strip(), "结束时间")
        if started_to:
            where.append("er.started_at <= ?")
            params.append(started_to)

        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY er.started_at DESC, er.id DESC LIMIT 200"
        return self._rows_to_dicts(self.kv.fetchall(sql, tuple(params)))


class NotificationDispatcher:
    def dispatch(self, account: Dict[str, Any], channels: List[Dict[str, Any]], result: TaskResult) -> None:
        if not channels:
            return
        message = self._build_message(account, result)
        for channel in channels:
            if str(channel.get("type")) != CHANNEL_TYPE_TG:
                continue
            token = str(channel.get("tgbot_token") or "")
            chat_id = int(channel.get("tgbot_chat_id") or 0)
            if not token or not chat_id:
                continue
            tg_api = f"https://api.telegram.org/bot{token}/sendMessage"
            proxies = self._build_proxies(str(channel.get("tgbot_proxy") or ""))
            try:
                resp = std_requests.post(
                    tg_api,
                    data={"chat_id": str(chat_id), "text": message},
                    proxies=proxies,
                    timeout=10,
                )
                log_info(f"Telegram channel={channel.get('name')} status={resp.status_code} body={resp.text}")
            except Exception as exc:
                log_info(f"Telegram channel={channel.get('name')} failed: {exc}")

    def _build_message(self, account: Dict[str, Any], result: TaskResult) -> str:
        title = "刷新成功" if result.success else "刷新失败"
        lines = [
            f"[{title}] 账户 {account.get('name')}",
            f"平台: {account.get('platform_code')}",
            f"结果: {result.message}",
            f"开始时间: {result.started_at}",
            f"结束时间: {result.finished_at}",
        ]
        if result.username:
            lines.append(f"站点账号: {result.username}")
        if result.uploaded:
            lines.append(f"上传量: {result.uploaded}")
        if result.downloaded:
            lines.append(f"下载量: {result.downloaded}")
        if result.bonus:
            lines.append(f"魔力值: {result.bonus}")
        if result.last_login:
            lines.append(f"最后登录: {result.last_login}")
        if result.last_browse:
            lines.append(f"最后浏览: {result.last_browse}")
        return "\n".join(lines)

    def _build_proxies(self, proxy: str) -> Optional[Dict[str, str]]:
        if not proxy:
            return None
        return {"http": proxy, "https": proxy}


class BackgroundScheduler:
    def __init__(self, store: SettingsStore, base_config: Config):
        self.store = store
        self.base_config = clone_config(base_config)
        self.lock = threading.Lock()
        self.wakeup = threading.Event()
        self.manual_queue: List[int] = []
        self.dispatcher = NotificationDispatcher()
        self.thread = threading.Thread(target=self._loop, name="mtlogin-scheduler", daemon=True)
        self.state = {
            "status": "idle",
            "scheduler_status": "idle",
            "running": False,
            "schedule_message": "No scheduled accounts",
            "next_run_at": "",
            "last_run_mode": "",
            "last_started_at": "",
            "last_finished_at": "",
            "last_message": "",
            "last_username": "",
            "last_uploaded": "",
            "last_downloaded": "",
            "last_bonus": "",
            "last_login": "",
            "last_browse": "",
            "last_account_name": "",
            "last_platform_name": "",
        }
        self.state.update(self.store.load_runtime_state())

    def start(self) -> None:
        self.thread.start()

    def reload(self) -> None:
        self.wakeup.set()

    def trigger_account(self, account_id: int) -> None:
        with self.lock:
            if account_id not in self.manual_queue:
                self.manual_queue.append(account_id)
        self.wakeup.set()

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            return dict(self.state)

    def _set_state(self, **kwargs: Any) -> None:
        with self.lock:
            self.state.update(kwargs)
            current = dict(self.state)
        self.store.save_runtime_state(current)

    def _pop_manual_trigger(self) -> Optional[int]:
        with self.lock:
            if not self.manual_queue:
                return None
            return self.manual_queue.pop(0)

    def _execute_account(self, account_id: int, mode: str) -> None:
        account = self.store.get_account_with_platform(account_id, enabled_only=True)
        if not account:
            self._set_state(
                status="error",
                scheduler_status="idle",
                running=False,
                last_run_mode=mode,
                last_message="目标账户不存在，或账户/平台未启用。",
            )
            return

        self._set_state(
            running=True,
            status="running",
            scheduler_status="running",
            schedule_message=f"Account {account['name']} is running ({mode})",
            next_run_at="",
            last_account_name=account["name"],
            last_platform_name=account["platform_code"],
        )

        cfg = self.store.build_account_config(self.base_config, account)
        if not (cfg.username and cfg.password) and not cfg.m_team_auth:
            now = now_text()
            result = TaskResult(
                success=False,
                message="账户未配置用户名密码或 M-Team Auth Token",
                started_at=now,
                finished_at=now,
            )
        else:
            result = JobServer(cfg).run_once(send_notifications=False)

        self.store.create_execution_record(account, mode, result)
        channels = self.store.list_account_notification_channels(account_id, enabled_only=True)
        self.dispatcher.dispatch(account, channels, result)
        self._set_state(
            running=False,
            status="success" if result.success else "error",
            scheduler_status="idle",
            last_run_mode=mode,
            last_started_at=result.started_at,
            last_finished_at=result.finished_at,
            last_message=result.message,
            last_username=result.username,
            last_uploaded=result.uploaded,
            last_downloaded=result.downloaded,
            last_bonus=result.bonus,
            last_login=result.last_login,
            last_browse=result.last_browse,
            last_account_name=account["name"],
            last_platform_name=account["platform_code"],
        )

    def _list_scheduled_accounts(self) -> List[tuple[Dict[str, Any], datetime]]:
        scheduled: List[tuple[Dict[str, Any], datetime]] = []
        current_time = datetime.now()
        for account in self.store.list_enabled_accounts_for_scheduler():
            crontab_expr = str(account.get("crontab") or "").strip()
            if not crontab_expr:
                continue
            if not croniter.is_valid(crontab_expr):
                log_info(f"Skip invalid CRONTAB for account={account['name']}: {crontab_expr}")
                continue
            next_run = croniter(crontab_expr, current_time).get_next(datetime)
            scheduled.append((account, next_run))
        scheduled.sort(key=lambda item: item[1])
        return scheduled

    def _loop(self) -> None:
        while True:
            manual_id = self._pop_manual_trigger()
            if manual_id is not None:
                self._execute_account(manual_id, "manual")
                continue

            scheduled = self._list_scheduled_accounts()
            if not scheduled:
                self._set_state(
                    scheduler_status="idle",
                    running=False,
                    next_run_at="",
                    schedule_message="No scheduled accounts",
                )
                self.wakeup.wait()
                self.wakeup.clear()
                continue

            next_account, next_run = scheduled[0]
            next_run_text = next_run.strftime("%Y-%m-%d %H:%M:%S")
            self._set_state(
                scheduler_status="waiting",
                running=False,
                next_run_at=next_run_text,
                schedule_message=f"Waiting for {next_account['name']} at {next_run_text}",
            )

            wait_seconds = max(0, (next_run - datetime.now()).total_seconds())
            triggered = self.wakeup.wait(timeout=wait_seconds)
            self.wakeup.clear()
            if triggered:
                continue

            due_before = next_run + timedelta(seconds=1)
            for account, run_at in scheduled:
                if run_at <= due_before:
                    self._execute_account(int(account["id"]), "scheduled")


def tail_log(path: str, limit: int = 200) -> str:
    if not path or not os.path.exists(path):
        return "Log file not created yet."
    with open(path, "r", encoding="utf-8", errors="replace") as fp:
        lines = fp.readlines()
    return "".join(lines[-limit:]) or "Log file is empty."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="mtlogin web admin")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    parser.add_argument("--db-path", default=os.getenv("DB_PATH", "./mtlogin.db"))
    parser.add_argument("--log-file", default=os.getenv("LOG_FILE", "./mtlogin.log"))
    parser.add_argument("--admin-username", default=os.getenv("ADMIN_USERNAME", "admin"))
    parser.add_argument("--admin-password", default=os.getenv("ADMIN_PASSWORD", "admin123456"))
    parser.add_argument("--secret-key", default=os.getenv("SECRET_KEY", secrets.token_hex(32)))
    return parser.parse_args()


def create_app(args: argparse.Namespace) -> Flask:
    mtlogin.LOG_FILE_PATH = args.log_file
    base_config = load_config()
    base_config.db_path = args.db_path

    store = SettingsStore(args.db_path)
    store.ensure_admin(args.admin_username, args.admin_password)
    scheduler = BackgroundScheduler(store, base_config)
    scheduler.start()

    app = Flask(__name__)
    app.secret_key = args.secret_key
    app.config["STORE"] = store
    app.config["SCHEDULER"] = scheduler
    app.config["BASE_CONFIG"] = base_config
    app.config["LOG_FILE_PATH"] = args.log_file

    def login_required(view):
        @wraps(view)
        def wrapped(*view_args, **view_kwargs):
            if not session.get("admin_username"):
                return redirect(url_for("login"))
            return view(*view_args, **view_kwargs)

        return wrapped

    def page_redirect(endpoint: str, **kwargs: Any):
        params = {key: value for key, value in kwargs.items() if value not in (None, "", [])}
        return redirect(url_for(endpoint, **params))

    def build_history_filters() -> Dict[str, str]:
        return {
            "account_id": request.args.get("account_id", "").strip(),
            "platform_id": request.args.get("platform_id", "").strip(),
            "status": request.args.get("status", "").strip(),
            "started_from": request.args.get("started_from", "").strip(),
            "started_to": request.args.get("started_to", "").strip(),
        }

    def build_admin_context(active_page: str, title: str, description: str, **extra: Any) -> Dict[str, Any]:
        admin_settings = store.load_admin_settings()
        state = scheduler.snapshot()
        nav_items = []
        for item in ADMIN_NAV_ITEMS:
            nav_items.append({**item, "active": item["page"] == active_page})

        context = {
            "active_page": active_page,
            "page_title": title,
            "page_description": description,
            "admin_username": admin_settings.get("username", "admin"),
            "nav_items": nav_items,
            "state": state,
            "state_cards": [
                {"label": "调度状态", "value": state.get("scheduler_status") or "idle"},
                {"label": "调度说明", "value": state.get("schedule_message") or "未设置"},
                {"label": "下次执行", "value": state.get("next_run_at") or "未计划"},
                {"label": "最近结果", "value": state.get("last_message") or "暂无执行记录"},
            ],
        }
        context.update(extra)
        return context

    def build_accounts_view_models() -> List[Dict[str, Any]]:
        accounts = store.list_accounts_for_dashboard()
        for account in accounts:
            account["next_run_at"] = next_run_text(account.get("crontab"))
        return accounts

    @app.route("/")
    def index():
        if session.get("admin_username"):
            return redirect(url_for("accounts_page"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            if store.verify_admin(username, password):
                session["admin_username"] = username
                flash("登录成功。", "success")
                return redirect(url_for("accounts_page"))
            flash("用户名或密码错误。", "error")
        return render_template("login.html")

    @app.get("/logout")
    @login_required
    def logout():
        session.clear()
        flash("已退出登录。", "success")
        return redirect(url_for("login"))

    @app.get("/dashboard")
    @login_required
    def dashboard():
        return redirect(url_for("accounts_page"))

    @app.get("/accounts")
    @login_required
    def accounts_page():
        edit_account_id = request.args.get("edit_account", "").strip()
        edit_account = store.get_account(safe_int(edit_account_id)) if edit_account_id else {}
        selected_channel_ids = store.get_account_notification_ids(int(edit_account["id"])) if edit_account else []
        enabled_platforms = store.list_platforms(enabled_only=True)
        accounts = build_accounts_view_models()
        return render_template(
            "accounts.html",
            **build_admin_context(
                "accounts",
                "账户管理",
                "集中维护登录账户、调度计划、通知绑定和最近执行摘要。",
                accounts=accounts,
                channels=store.list_notification_channels(),
                enabled_platforms=enabled_platforms,
                edit_account=edit_account,
                account_secret_status={
                    "password": bool(edit_account.get("password")),
                    "totpsecret": bool(edit_account.get("totpsecret")),
                    "m_team_auth": bool(edit_account.get("m_team_auth")),
                },
                selected_channel_ids=selected_channel_ids,
                default_platform_id=(enabled_platforms[0]["id"] if enabled_platforms else 0),
                default_timeout=base_config.timeout,
                default_cookie_mode=base_config.cookie_mode,
            ),
        )

    @app.get("/platforms")
    @login_required
    def platforms_page():
        return render_template(
            "platforms.html",
            **build_admin_context(
                "platforms",
                "平台配置",
                "查看当前可用平台及其固定 API 配置，控制平台启用状态。",
                platforms=store.list_platforms(),
            ),
        )

    @app.get("/notifications")
    @login_required
    def notifications_page():
        edit_channel_id = request.args.get("edit_channel", "").strip()
        edit_channel = store.get_notification_channel(safe_int(edit_channel_id)) if edit_channel_id else {}
        return render_template(
            "notifications.html",
            **build_admin_context(
                "notifications",
                "通知管理",
                "维护 Telegram 通知渠道，并将其绑定到不同登录账户。",
                channels=store.list_notification_channels(),
                edit_channel=edit_channel,
                channel_secret_status={"tgbot_token": bool(edit_channel.get("tgbot_token"))},
            ),
        )

    @app.get("/history")
    @login_required
    def history_page():
        history_filters = build_history_filters()
        try:
            history_records = store.list_execution_records(history_filters)
        except ValueError as exc:
            flash(str(exc), "error")
            history_records = store.list_execution_records({})
        return render_template(
            "history.html",
            **build_admin_context(
                "history",
                "执行记录",
                "按账户、平台、状态和时间范围筛选执行结果与关键指标。",
                accounts=build_accounts_view_models(),
                platforms=store.list_platforms(),
                history_records=history_records,
                history_filters=history_filters,
            ),
        )

    @app.get("/settings")
    @login_required
    def settings_page():
        return render_template(
            "settings.html",
            **build_admin_context(
                "settings",
                "系统设置",
                "维护管理员账号，并查看当前服务运行环境与最近日志。",
                log_tail=tail_log(args.log_file),
                runtime_info={
                    "host": args.host,
                    "port": args.port,
                    "db_path": args.db_path,
                    "log_file": args.log_file,
                },
            ),
        )

    @app.post("/platforms/<int:platform_id>/toggle")
    @login_required
    def toggle_platform(platform_id: int):
        try:
            enabled = request.form.get("enabled") == "1"
            store.set_platform_enabled(platform_id, enabled)
            scheduler.reload()
            flash("平台状态已更新。", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("platforms_page"))

    @app.post("/notifications/save")
    @login_required
    def save_notification():
        channel_id_text = request.form.get("channel_id", "").strip()
        channel_id = parse_int(channel_id_text, "通知渠道", 0) if channel_id_text else None
        payload = {
            "name": request.form.get("name", "").strip(),
            "type": request.form.get("type", CHANNEL_TYPE_TG).strip(),
            "enabled": request.form.get("enabled") == "on",
            "tgbot_token": request.form.get("tgbot_token", ""),
            "tgbot_chat_id": request.form.get("tgbot_chat_id", "").strip(),
            "tgbot_proxy": request.form.get("tgbot_proxy", "").strip(),
        }
        try:
            saved_id = store.save_notification_channel(payload, channel_id)
            flash("通知渠道已保存。", "success")
            scheduler.reload()
            return page_redirect("notifications_page", edit_channel=saved_id)
        except ValueError as exc:
            flash(str(exc), "error")
            return page_redirect("notifications_page", edit_channel=channel_id_text)

    @app.post("/notifications/<int:channel_id>/toggle")
    @login_required
    def toggle_notification(channel_id: int):
        try:
            enabled = request.form.get("enabled") == "1"
            store.set_notification_channel_enabled(channel_id, enabled)
            scheduler.reload()
            flash("通知渠道状态已更新。", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("notifications_page"))

    @app.post("/accounts/save")
    @login_required
    def save_account():
        account_id_text = request.form.get("account_id", "").strip()
        account_id = parse_int(account_id_text, "登录账户", 0) if account_id_text else None
        payload = {
            "name": request.form.get("name", "").strip(),
            "platform_id": request.form.get("platform_id", "").strip(),
            "enabled": request.form.get("enabled") == "on",
            "username": request.form.get("username", "").strip(),
            "password": request.form.get("password", ""),
            "totpsecret": request.form.get("totpsecret", ""),
            "proxy": request.form.get("proxy", "").strip(),
            "crontab": request.form.get("crontab", "").strip(),
            "m_team_auth": request.form.get("m_team_auth", ""),
            "m_team_did": request.form.get("m_team_did", "").strip(),
            "timeout": request.form.get("timeout", "").strip(),
            "cookie_mode": request.form.get("cookie_mode", "").strip(),
            "skip_cache": request.form.get("skip_cache") == "on",
        }
        selected_channel_ids = request.form.getlist("notification_channel_ids")
        try:
            saved_id = store.save_account(payload, [parse_int(value, "通知渠道") for value in selected_channel_ids], account_id)
            scheduler.reload()
            flash("登录账户已保存。", "success")
            return page_redirect("accounts_page", edit_account=saved_id)
        except ValueError as exc:
            flash(str(exc), "error")
            return page_redirect("accounts_page", edit_account=account_id_text)

    @app.post("/accounts/<int:account_id>/toggle")
    @login_required
    def toggle_account(account_id: int):
        try:
            enabled = request.form.get("enabled") == "1"
            store.set_account_enabled(account_id, enabled)
            scheduler.reload()
            flash("登录账户状态已更新。", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("accounts_page"))

    @app.post("/accounts/<int:account_id>/run")
    @login_required
    def run_account(account_id: int):
        account = store.get_account_with_platform(account_id, enabled_only=True)
        if not account:
            flash("只能执行已启用且平台可用的账户。", "error")
            return redirect(url_for("accounts_page"))
        scheduler.trigger_account(account_id)
        flash(f"已提交账户 {account['name']} 的立即执行请求。", "success")
        return redirect(url_for("accounts_page"))

    @app.post("/admin")
    @login_required
    def update_admin():
        current_username = store.load_admin_settings().get("username", "admin")
        new_username = request.form.get("admin_username", "").strip() or current_username
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not store.verify_admin(current_username, current_password):
            flash("当前密码不正确。", "error")
            return redirect(url_for("settings_page"))
        if new_password and new_password != confirm_password:
            flash("两次输入的新密码不一致。", "error")
            return redirect(url_for("settings_page"))

        store.update_admin(new_username, new_password)
        session["admin_username"] = new_username
        flash("管理员账号已更新。", "success")
        return redirect(url_for("settings_page"))

    return app


def main() -> None:
    args = parse_args()
    mtlogin.LOG_FILE_PATH = args.log_file
    log_info(f"Starting web admin on http://{args.host}:{args.port}")
    app = create_app(args)
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
