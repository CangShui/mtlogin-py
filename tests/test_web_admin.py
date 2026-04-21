import argparse
import json
import sys
import tempfile
import types
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch


class _FakeCroniter:
    def __init__(self, expr: str, current_time):
        self.expr = expr
        self.current_time = current_time

    @staticmethod
    def is_valid(expr: str) -> bool:
        text = str(expr or "").strip()
        return bool(text) and len(text.split()) == 5 and "invalid" not in text

    def get_next(self, _cls):
        return self.current_time + timedelta(hours=1)


requests_stub = types.ModuleType("requests")
requests_stub.RequestException = Exception
requests_stub.post = lambda *args, **kwargs: None
sys.modules.setdefault("requests", requests_stub)

pyotp_stub = types.ModuleType("pyotp")


class _FakeTOTP:
    def __init__(self, *_args, **_kwargs):
        pass

    def now(self) -> str:
        return "000000"


pyotp_stub.TOTP = _FakeTOTP
sys.modules.setdefault("pyotp", pyotp_stub)

curl_cffi_stub = types.ModuleType("curl_cffi")
curl_cffi_stub.requests = types.SimpleNamespace(Session=lambda *args, **kwargs: None)
sys.modules.setdefault("curl_cffi", curl_cffi_stub)

croniter_stub = types.ModuleType("croniter")
croniter_stub.croniter = _FakeCroniter
sys.modules.setdefault("croniter", croniter_stub)

import app as web_app
from mtlogin import KVStore, TaskResult, load_config


class WebAdminTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        base = Path(self.tempdir.name)
        self.db_path = str(base / "test.db")
        self.log_path = str(base / "test.log")
        self.frontend_dist = base / "frontend-dist"
        self.frontend_dist.mkdir()
        (self.frontend_dist / "index.html").write_text("<!doctype html><html><body><div id='app'>MTLogin Vue Admin</div></body></html>", encoding="utf-8")
        (self.frontend_dist / "assets").mkdir()
        (self.frontend_dist / "assets" / "app.js").write_text("console.log('mtlogin');", encoding="utf-8")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def make_test_client(self, authenticated: bool = True):
        args = argparse.Namespace(
            host="127.0.0.1",
            port=8765,
            db_path=self.db_path,
            log_file=self.log_path,
            frontend_dist=str(self.frontend_dist),
            admin_username="admin",
            admin_password="admin123456",
            secret_key="test-secret",
        )
        with patch.object(web_app.BackgroundScheduler, "start", return_value=None):
            flask_app = web_app.create_app(args)
        flask_app.config["TESTING"] = True
        client = flask_app.test_client()
        if authenticated:
            with client.session_transaction() as session:
                session["admin_username"] = "admin"
        return flask_app, client

    def test_legacy_settings_migrate_to_account_and_tg_channel(self) -> None:
        legacy_store = KVStore(self.db_path)
        legacy_store.put(
            web_app.LEGACY_TASK_SETTINGS_KEY,
            json.dumps(
                {
                    "username": "legacy-user",
                    "password": "legacy-pass",
                    "crontab": "2 */2 * * *",
                    "tgbot_token": "123456:token",
                    "tgbot_chat_id": -10001,
                    "tgbot_proxy": "http://127.0.0.1:7890",
                },
                ensure_ascii=False,
            ),
        )

        store = web_app.SettingsStore(self.db_path)
        platforms = store.list_platforms()
        channels = store.list_notification_channels()
        accounts = store.list_accounts_for_dashboard()

        self.assertEqual(1, len(platforms))
        self.assertEqual(web_app.DEFAULT_MT_CODE, platforms[0]["code"])
        self.assertEqual(1, len(channels))
        self.assertEqual(1, len(accounts))
        self.assertEqual("legacy-user", accounts[0]["name"])
        self.assertEqual([channels[0]["id"]], store.get_account_notification_ids(accounts[0]["id"]))

    def test_disabled_notification_channel_cannot_bind_account(self) -> None:
        store = web_app.SettingsStore(self.db_path)
        platform = store.get_platform_by_code(web_app.DEFAULT_MT_CODE)
        channel_id = store.save_notification_channel(
            {
                "name": "Disabled TG",
                "type": "tg",
                "enabled": False,
                "tgbot_token": "123456:token",
                "tgbot_chat_id": -10002,
            }
        )

        with self.assertRaisesRegex(ValueError, "已启用的通知渠道"):
            store.save_account(
                {
                    "name": "main-account",
                    "platform_id": platform["id"],
                    "enabled": True,
                    "username": "u1",
                    "password": "p1",
                    "timeout": 60,
                    "cookie_mode": "normal",
                },
                [channel_id],
            )

    def test_scheduler_execute_account_writes_history(self) -> None:
        store = web_app.SettingsStore(self.db_path)
        platform = store.get_platform_by_code(web_app.DEFAULT_MT_CODE)
        account_id = store.save_account(
            {
                "name": "scheduled-account",
                "platform_id": platform["id"],
                "enabled": True,
                "username": "u2",
                "password": "p2",
                "timeout": 60,
                "cookie_mode": "normal",
            },
            [],
        )

        base_config = load_config()
        base_config.db_path = self.db_path
        scheduler = web_app.BackgroundScheduler(store, base_config)
        fake_result = TaskResult(
            success=True,
            message="Task execution succeeded",
            started_at="2026-04-21 10:00:00",
            finished_at="2026-04-21 10:00:05",
            username="u2",
            uploaded="10 GB",
            downloaded="20 GB",
            bonus="12345",
            last_login="2026-04-21 09:59:59",
            last_browse="2026-04-21 10:00:01",
        )

        with patch("app.JobServer") as mock_job_server, patch.object(scheduler.dispatcher, "dispatch") as mock_dispatch:
            mock_job_server.return_value.run_once.return_value = fake_result
            scheduler._execute_account(account_id, "manual")

        mock_job_server.return_value.run_once.assert_called_once_with(send_notifications=False)
        mock_dispatch.assert_called_once()

        records = store.list_execution_records({})
        self.assertEqual(1, len(records))
        self.assertEqual("manual", records[0]["trigger_mode"])
        self.assertEqual("success", records[0]["status"])
        self.assertEqual("scheduled-account", records[0]["account_name"])
        self.assertEqual("u2", records[0]["run_username"])

    def test_execution_history_filters_and_ordering(self) -> None:
        store = web_app.SettingsStore(self.db_path)
        platform = store.get_platform_by_code(web_app.DEFAULT_MT_CODE)
        account_a = store.save_account(
            {
                "name": "account-a",
                "platform_id": platform["id"],
                "enabled": True,
                "username": "a",
                "password": "pa",
            },
            [],
        )
        account_b = store.save_account(
            {
                "name": "account-b",
                "platform_id": platform["id"],
                "enabled": True,
                "username": "b",
                "password": "pb",
            },
            [],
        )

        store.create_execution_record(
            store.get_account(account_a),
            "scheduled",
            TaskResult(
                success=False,
                message="bad token",
                started_at="2026-04-20 08:00:00",
                finished_at="2026-04-20 08:00:03",
            ),
        )
        store.create_execution_record(
            store.get_account(account_b),
            "manual",
            TaskResult(
                success=True,
                message="ok",
                started_at="2026-04-21 09:00:00",
                finished_at="2026-04-21 09:00:03",
                username="b",
            ),
        )

        all_records = store.list_execution_records({})
        self.assertEqual(2, len(all_records))
        self.assertEqual("account-b", all_records[0]["account_name"])

        filtered = store.list_execution_records(
            {
                "account_id": str(account_a),
                "status": "error",
                "started_from": "2026-04-20T00:00",
                "started_to": "2026-04-20T23:59",
            }
        )
        self.assertEqual(1, len(filtered))
        self.assertEqual("account-a", filtered[0]["account_name"])
        self.assertEqual("error", filtered[0]["status"])

    def test_spa_routes_and_static_assets_are_served(self) -> None:
        _app, client = self.make_test_client(authenticated=False)

        for path in ["/", "/login", "/accounts", "/platforms", "/notifications", "/history", "/settings"]:
            response = client.get(path)
            body = response.get_data(as_text=True)
            self.assertEqual(200, response.status_code)
            self.assertIn("MTLogin Vue Admin", body)
            response.close()

        asset_response = client.get("/static/admin/assets/app.js")
        self.assertEqual(200, asset_response.status_code)
        self.assertIn("mtlogin", asset_response.get_data(as_text=True))
        asset_response.close()

    def test_unauthenticated_api_returns_json_401(self) -> None:
        _app, client = self.make_test_client(authenticated=False)

        for path in ["/api/admin/session/me", "/api/admin/accounts", "/api/admin/settings"]:
            response = client.get(path)
            payload = response.get_json()
            self.assertEqual(401, response.status_code)
            self.assertEqual(401, payload["code"])
            self.assertIn("未登录", payload["message"])

    def test_session_login_bootstrap_and_logout_flow(self) -> None:
        _app, client = self.make_test_client(authenticated=False)

        bad_response = client.post("/api/admin/session/login", json={"username": "admin", "password": "bad"})
        self.assertEqual(401, bad_response.status_code)
        self.assertEqual(401, bad_response.get_json()["code"])

        login_response = client.post("/api/admin/session/login", json={"username": "admin", "password": "admin123456"})
        self.assertEqual(200, login_response.status_code)
        self.assertEqual("admin", login_response.get_json()["data"]["username"])

        me_response = client.get("/api/admin/session/me")
        self.assertEqual(200, me_response.status_code)
        self.assertEqual(["admin"], me_response.get_json()["data"]["roles"])

        bootstrap_response = client.get("/api/admin/bootstrap")
        bootstrap_data = bootstrap_response.get_json()["data"]
        self.assertEqual(200, bootstrap_response.status_code)
        self.assertIn("stateCards", bootstrap_data)
        self.assertEqual("admin", bootstrap_data["currentUser"]["username"])

        logout_response = client.post("/api/admin/session/logout")
        self.assertEqual(200, logout_response.status_code)
        self.assertEqual(401, client.get("/api/admin/session/me").status_code)

    def test_json_admin_mutations_queries_and_settings(self) -> None:
        flask_app, client = self.make_test_client()
        store = flask_app.config["STORE"]
        platform = store.get_platform_by_code(web_app.DEFAULT_MT_CODE)

        channel_response = client.post(
            "/api/admin/notifications",
            json={
                "name": "Ops TG",
                "type": "tg",
                "enabled": True,
                "tgbot_token": "123456:token",
                "tgbot_chat_id": -10001,
                "tgbot_proxy": "http://127.0.0.1:7890",
            },
        )
        channel_payload = channel_response.get_json()
        self.assertEqual(200, channel_response.status_code)
        self.assertTrue(channel_payload["data"]["has_tgbot_token"])
        channel_id = channel_payload["data"]["id"]

        account_response = client.post(
            "/api/admin/accounts",
            json={
                "name": "main-account",
                "platform_id": platform["id"],
                "enabled": True,
                "username": "u1",
                "password": "p1",
                "crontab": "2 */2 * * *",
                "timeout": 60,
                "cookie_mode": "normal",
                "notification_channel_ids": [channel_id],
            },
        )
        account_payload = account_response.get_json()
        self.assertEqual(200, account_response.status_code)
        self.assertEqual("登录账户已保存。", account_payload["message"])
        account_id = account_payload["data"]["id"]

        toggle_response = client.post(f"/api/admin/accounts/{account_id}/toggle", json={"enabled": False})
        self.assertEqual(200, toggle_response.status_code)
        self.assertFalse(toggle_response.get_json()["data"]["enabled"])

        client.post(f"/api/admin/accounts/{account_id}/toggle", json={"enabled": True})

        with patch.object(flask_app.config["SCHEDULER"], "trigger_account") as mock_trigger:
            run_response = client.post(f"/api/admin/accounts/{account_id}/run")
        self.assertEqual(200, run_response.status_code)
        mock_trigger.assert_called_once_with(account_id)

        settings_response = client.get("/api/admin/settings")
        settings_payload = settings_response.get_json()["data"]
        self.assertEqual(200, settings_response.status_code)
        self.assertEqual("admin", settings_payload["adminUsername"])
        self.assertEqual(str(self.frontend_dist), settings_payload["runtimeInfo"]["frontend_dist"])

        update_response = client.post(
            "/api/admin/settings/admin",
            json={
                "admin_username": "ops-admin",
                "current_password": "admin123456",
                "new_password": "new-pass",
                "confirm_password": "new-pass",
            },
        )
        self.assertEqual(200, update_response.status_code)
        self.assertEqual("ops-admin", update_response.get_json()["data"]["username"])

        me_response = client.get("/api/admin/session/me")
        self.assertEqual("ops-admin", me_response.get_json()["data"]["username"])

    def test_account_api_shows_latest_metrics_and_next_run(self) -> None:
        flask_app, client = self.make_test_client()
        store = flask_app.config["STORE"]
        platform = store.get_platform_by_code(web_app.DEFAULT_MT_CODE)
        account_id = store.save_account(
            {
                "name": "metrics-account",
                "platform_id": platform["id"],
                "enabled": True,
                "username": "u2",
                "password": "p2",
                "crontab": "2 */2 * * *",
                "timeout": 60,
                "cookie_mode": "normal",
            },
            [],
        )
        store.create_execution_record(
            store.get_account(account_id),
            "manual",
            TaskResult(
                success=True,
                message="ok",
                started_at="2026-04-21 10:00:00",
                finished_at="2026-04-21 10:00:05",
                username="u2",
                uploaded="10 GB",
                downloaded="20 GB",
                bonus="12345",
                last_login="2026-04-21 09:59:59",
            ),
        )

        response = client.get("/api/admin/accounts")
        payload = response.get_json()["data"]
        account = next(item for item in payload["items"] if item["id"] == account_id)

        self.assertEqual(200, response.status_code)
        self.assertEqual("10 GB", account["last_uploaded"])
        self.assertEqual("20 GB", account["last_downloaded"])
        self.assertEqual("12345", account["last_bonus"])
        self.assertEqual("2026-04-21 09:59:59", account["last_login"])
        self.assertTrue(account["next_run_at"])

    def test_history_api_supports_filters(self) -> None:
        flask_app, client = self.make_test_client()
        store = flask_app.config["STORE"]
        platform = store.get_platform_by_code(web_app.DEFAULT_MT_CODE)
        account_id = store.save_account(
            {
                "name": "history-account",
                "platform_id": platform["id"],
                "enabled": True,
                "username": "history",
                "password": "history-pass",
            },
            [],
        )
        store.create_execution_record(
            store.get_account(account_id),
            "manual",
            TaskResult(
                success=False,
                message="network timeout",
                started_at="2026-04-21 08:00:00",
                finished_at="2026-04-21 08:00:03",
            ),
        )

        response = client.get(
            "/api/admin/history",
            query_string={
                "account_id": str(account_id),
                "status": "error",
                "started_from": "2026-04-21T00:00",
                "started_to": "2026-04-21T23:59",
            },
        )
        payload = response.get_json()["data"]

        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(payload["items"]))
        self.assertEqual("network timeout", payload["items"][0]["result_message"])


if __name__ == "__main__":
    unittest.main()
