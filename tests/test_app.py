from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app import fetch_rows, public_supabase_key, store_session, task_groups, valid_email


@pytest.mark.parametrize(("email", "valid"), [
    ("name@example.com", True), ("name@example", False), ("one@@example.com", False),
    ("two names@example.com", False), ("", False),
])
def test_email_validation(email, valid):
    assert valid_email(email) == valid


def test_rejects_privileged_keys():
    assert public_supabase_key("sb_publishable_sample")
    assert not public_supabase_key("sb_secret_sample")
    assert public_supabase_key("header.eyJyb2xlIjoiYW5vbiJ9.signature")
    assert not public_supabase_key("header.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.signature")


def test_session_needs_verified_email():
    session = SimpleNamespace(access_token="fake-access", refresh_token="fake-refresh")
    response = SimpleNamespace(session=session, user=SimpleNamespace(email_confirmed_at=None))
    with patch("app.st.session_state", {}) as state:
        assert not store_session(response)
        assert state == {}
        response.user.email_confirmed_at = "2026-01-01T00:00:00Z"
        assert store_session(response)
        assert state["auth_tokens"] == ("fake-access", "fake-refresh")


def test_deadlines_use_inclusive_three_days_and_exclude_closed_tasks():
    statuses = ["รอดำเนินการ"] * 5 + ["เสร็จแล้ว", "ยกเลิก"]
    deadlines = ["2026-11-25", "2026-11-26", "2026-11-29", "2026-11-30", None,
                 "2026-11-25", "2026-11-26"]
    tasks = [{"status": status, "due_date": due} for status, due in zip(statuses, deadlines)]
    assert task_groups(tasks, date(2026, 11, 26)) == ([tasks[0]], [tasks[1]], [tasks[2]])


def test_fetch_rows_includes_more_than_two_pages():
    from unittest.mock import Mock

    client = Mock()
    query = client.table.return_value.select.return_value.order.return_value.limit.return_value
    all_rows = [{"id": identifier} for identifier in range(205, 0, -1)]
    query.lt.return_value = query
    query.execute.side_effect = [SimpleNamespace(data=all_rows[i:i + 100]) for i in (0, 100, 200)]
    assert fetch_rows(client, "tasks", "id") == all_rows
    assert [call.args for call in query.lt.call_args_list] == [("id", 106), ("id", 6)]
