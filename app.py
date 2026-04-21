#!/usr/bin/env python3
import argparse
import json
import os
import secrets
import threading
from datetime import datetime
from functools import wraps
from typing import Any, Dict

import mtlogin
from croniter import croniter
from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from mtlogin import Config, JobServer, KVStore, TaskResult, clone_config, load_config, log_info

TASK_SETTINGS_KEY = "web:task_settings"
ADMIN_SETTINGS_KEY = "web:admin_settings"
RUNTIME_STATE_KEY = "web:runtime_state"

SECRET_FIELDS = {"password", "totpsecret", "m_team_auth", "tgbot_token"}
INT_FIELDS = {"tgbot_chat_id", "timeout"}
BOOL_FIELDS = {"skip_cache"}
TASK_FIELDS = [
    "username",
    "password",
    "totpsecret",
    "m_team_auth",
    "m_team_did",
    "proxy",
    "crontab",
    "tgbot_token",
    "tgbot_chat_id",
    "tgbot_proxy",
    "api_host",
    "referer",
    "timeout",
    "cookie_mode",
    "skip_cache",
]


class SettingsStore:
    def __init__(self, db_path: str):
        self.kv = KVStore(db_path)

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

    def load_task_settings(self) -> Dict[str, Any]:
        return self._get_json(TASK_SETTINGS_KEY, {})

    def save_task_settings(self, settings: Dict[str, Any]) -> None:
        clean = {key: settings[key] for key in TASK_FIELDS if key in settings}
        self._put_json(TASK_SETTINGS_KEY, clean)

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


class BackgroundScheduler:
    def __init__(self, store: SettingsStore, base_config: Config):
        self.store = store
        self.base_config = clone_config(base_config)
        self.lock = threading.Lock()
        self.wakeup = threading.Event()
        self.pending_manual = False
        self.thread = threading.Thread(target=self._loop, name="mtlogin-scheduler", daemon=True)
        self.state = {
            "status": "idle",
            "scheduler_status": "idle",
            "running": False,
            "schedule_message": "No schedule configured",
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
        }
        self.state.update(self.store.load_runtime_state())

    def start(self) -> None:
        self.thread.start()

    def reload(self) -> None:
        self.wakeup.set()

    def trigger_now(self) -> None:
        with self.lock:
            self.pending_manual = True
        self.wakeup.set()

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            return dict(self.state)

    def _set_state(self, **kwargs: Any) -> None:
        with self.lock:
            self.state.update(kwargs)
            current = dict(self.state)
        self.store.save_runtime_state(current)

    def _consume_manual_trigger(self) -> bool:
        with self.lock:
            if not self.pending_manual:
                return False
            self.pending_manual = False
            return True

    def _build_config(self) -> Config:
        cfg = clone_config(self.base_config)
        stored = self.store.load_task_settings()
        for field in TASK_FIELDS:
            if field not in stored:
                continue
            value = stored[field]
            if field in INT_FIELDS:
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    value = 0
            elif field in BOOL_FIELDS:
                value = bool(value)
            setattr(cfg, field, value)
        cfg.db_path = self.base_config.db_path
        return cfg

    def _execute(self, mode: str) -> None:
        cfg = self._build_config()
        self._set_state(
            running=True,
            status="running",
            scheduler_status="running",
            schedule_message=f"Task is running ({mode})",
            next_run_at="",
        )
        if not (cfg.username and cfg.password) and not cfg.m_team_auth:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result = TaskResult(
                success=False,
                message="M-Team account is not configured yet",
                started_at=now,
                finished_at=now,
            )
        else:
            result = JobServer(cfg).run_once()
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
        )

    def _loop(self) -> None:
        while True:
            if self._consume_manual_trigger():
                self._execute("manual")
                continue

            settings = self.store.load_task_settings()
            crontab_expr = str(settings.get("crontab", "") or "").strip()
            if not crontab_expr:
                self._set_state(scheduler_status="idle", running=False, next_run_at="", schedule_message="No schedule configured")
                self.wakeup.wait()
                self.wakeup.clear()
                continue

            if not croniter.is_valid(crontab_expr):
                self._set_state(
                    scheduler_status="error",
                    running=False,
                    next_run_at="",
                    schedule_message=f"Invalid CRONTAB: {crontab_expr}",
                )
                self.wakeup.wait(timeout=60)
                self.wakeup.clear()
                continue

            next_run = croniter(crontab_expr, datetime.now()).get_next(datetime)
            next_run_text = next_run.strftime("%Y-%m-%d %H:%M:%S")
            self._set_state(
                scheduler_status="waiting",
                running=False,
                next_run_at=next_run_text,
                schedule_message=f"Waiting for {next_run_text}",
            )
            wait_seconds = max(0, (next_run - datetime.now()).total_seconds())
            triggered = self.wakeup.wait(timeout=wait_seconds)
            self.wakeup.clear()
            if triggered:
                continue
            self._execute("scheduled")


def tail_log(path: str, limit: int = 200) -> str:
    if not path or not os.path.exists(path):
        return "Log file not created yet."
    with open(path, "r", encoding="utf-8", errors="replace") as fp:
        lines = fp.readlines()
    return "".join(lines[-limit:]) or "Log file is empty."


def build_display_settings(base_config: Config, stored: Dict[str, Any]) -> Dict[str, Any]:
    merged = {field: getattr(base_config, field) for field in TASK_FIELDS}
    merged.update(stored)
    return merged


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

    @app.route("/")
    def index():
        if session.get("admin_username"):
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            if store.verify_admin(username, password):
                session["admin_username"] = username
                flash("登录成功。", "success")
                return redirect(url_for("dashboard"))
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
        stored = store.load_task_settings()
        settings = build_display_settings(base_config, stored)
        state = scheduler.snapshot()
        admin_settings = store.load_admin_settings()
        secret_status = {
            "password": bool(stored.get("password") or base_config.password),
            "totpsecret": bool(stored.get("totpsecret") or base_config.totpsecret),
            "m_team_auth": bool(stored.get("m_team_auth") or base_config.m_team_auth),
            "tgbot_token": bool(stored.get("tgbot_token") or base_config.tgbot_token),
        }
        return render_template(
            "dashboard.html",
            settings=settings,
            state=state,
            log_tail=tail_log(args.log_file),
            admin_username=admin_settings.get("username", "admin"),
            secret_status=secret_status,
        )

    @app.post("/settings")
    @login_required
    def save_settings():
        current = store.load_task_settings()
        updated = dict(current)
        for field in TASK_FIELDS:
            if field in BOOL_FIELDS:
                updated[field] = request.form.get(field) == "on"
                continue
            raw = request.form.get(field, "")
            value = raw.strip()
            if field in SECRET_FIELDS:
                if value:
                    updated[field] = value
                continue
            if field in INT_FIELDS:
                if not value:
                    updated[field] = 0
                else:
                    try:
                        updated[field] = int(value)
                    except ValueError:
                        flash(f"{field} 必须是整数。", "error")
                        return redirect(url_for("dashboard"))
                continue
            updated[field] = value

        if updated.get("crontab") and not croniter.is_valid(updated["crontab"]):
            flash("CRONTAB 表达式无效。", "error")
            return redirect(url_for("dashboard"))
        if updated.get("cookie_mode") not in ("normal", "strict"):
            updated["cookie_mode"] = "normal"

        store.save_task_settings(updated)
        scheduler.reload()
        flash("任务配置已保存。", "success")
        return redirect(url_for("dashboard"))

    @app.post("/run")
    @login_required
    def run_now():
        scheduler.trigger_now()
        flash("已提交立即执行请求。", "success")
        return redirect(url_for("dashboard"))

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
            return redirect(url_for("dashboard"))
        if new_password and new_password != confirm_password:
            flash("两次输入的新密码不一致。", "error")
            return redirect(url_for("dashboard"))

        store.update_admin(new_username, new_password)
        session["admin_username"] = new_username
        flash("管理员账号已更新。", "success")
        return redirect(url_for("dashboard"))

    return app


def main() -> None:
    args = parse_args()
    mtlogin.LOG_FILE_PATH = args.log_file
    log_info(f"Starting web admin on http://{args.host}:{args.port}")
    app = create_app(args)
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
