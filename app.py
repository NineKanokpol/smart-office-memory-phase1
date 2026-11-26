"""Smart Office Memory Phase 1. Supabase owns all persistent state."""
from __future__ import annotations

import base64
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4
from zoneinfo import ZoneInfo

import streamlit as st
from postgrest.exceptions import APIError
from supabase import create_client

from file_utils import extract_document
from ui import workspace

APP_NAME = "Smart Office Memory | Phase 1"
BUCKET = "office-docs"
BANGKOK = ZoneInfo("Asia/Bangkok")
TASK_STATUSES = ["รอดำเนินการ", "กำลังดำเนินการ", "เสร็จแล้ว", "ยกเลิก"]
PROJECT_STATUSES = ["รอเริ่ม", "กำลังดำเนินการ", "เสร็จแล้ว", "ยกเลิก"]
CLOSED_STATUSES = {"เสร็จแล้ว", "ยกเลิก"}
PAGE_SIZE = 100

st.set_page_config(page_title=APP_NAME, layout="wide")


def public_supabase_key(key: str) -> bool:
    if key.startswith("sb_publishable_"):
        return True
    try:
        header, payload, signature = key.split(".")
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        return bool(header and signature and isinstance(claims, dict) and claims.get("role") == "anon")
    except (ValueError, TypeError):
        return False


def start_client():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_PUBLISHABLE_KEY"]
        endpoint = urlsplit(url)
        local = endpoint.scheme == "http" and endpoint.hostname in {"localhost", "127.0.0.1"}
        if not (local or endpoint.scheme == "https") or not endpoint.hostname:
            raise ValueError("Invalid Supabase URL")
        if not public_supabase_key(key):
            raise ValueError("Expected a publishable or anon key")
        client = create_client(url, key)
    except Exception:
        st.error("ตั้งค่า Supabase URL และ Publishable Key ในไฟล์ secrets.toml ตามคู่มือติดตั้ง")
        st.stop()

    # A new client per rerun prevents sharing authenticated clients across users.
    tokens = st.session_state.get("auth_tokens")
    if tokens:
        try:
            response = client.auth.set_session(*tokens)
            if store_session(response):
                return client, response.user
        except Exception:
            pass
        st.session_state.clear()
        st.info("เซสชันหมดอายุ กรุณาเข้าสู่ระบบอีกครั้ง")
        client = create_client(url, key)
    return client, None


def store_session(response) -> bool:
    if not (response.session and response.user and response.user.email_confirmed_at):
        return False
    st.session_state["auth_tokens"] = (
        response.session.access_token, response.session.refresh_token,
    )
    return True


def valid_email(email: str) -> bool:
    return len(email) <= 254 and bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email))


def login_screen(client):
    with st.container(key="office_login", width=490):
        workspace.brand(mark_only=True)
        login_panel(client)


def login_panel(client):
    st.title("Smart Office Memory")
    st.caption("ระบบสำนักงานดิจิทัลสำหรับจัดการโครงการ เอกสาร และงาน")
    st.caption("พื้นที่สาธิตสำหรับบัญชีและเอกสารสมมติ")
    login, signup = st.tabs(["เข้าสู่ระบบ", "สมัครบัญชี"])
    with login:
        with st.form("login_form", clear_on_submit=True):
            email = st.text_input("อีเมล", max_chars=254)
            password = st.text_input("รหัสผ่าน", type="password", max_chars=128)
            submit_login = st.form_submit_button("เข้าสู่ระบบ", type="primary", width="stretch")
        if submit_login:
            email = email.strip()
            if not valid_email(email) or not password:
                st.warning("กรอกอีเมลและรหัสผ่านให้ครบ")
            else:
                try:
                    with st.spinner("กำลังเข้าสู่ระบบ"):
                        response = client.auth.sign_in_with_password({"email": email, "password": password})
                    if store_session(response):
                        st.rerun()
                    st.warning("ยืนยันอีเมลก่อนเข้าสู่ระบบ")
                except Exception:
                    st.error("เข้าสู่ระบบไม่สำเร็จ ตรวจสอบอีเมล รหัสผ่าน และการยืนยันอีเมล")

    with signup:
        st.caption("ใช้อีเมลทดลองที่รับลิงก์ยืนยันได้ การส่งอีเมลขึ้นอยู่กับผู้ให้บริการของโครงการ")
        with st.form("signup_form", clear_on_submit=True):
            email = st.text_input("อีเมลสำหรับสมัคร", max_chars=254)
            password = st.text_input("ตั้งรหัสผ่าน (อย่างน้อย 8 ตัวอักษร)", type="password", max_chars=128)
            consent = st.checkbox("ฉันจะใช้เฉพาะข้อมูลสมมติ")
            submit_signup = st.form_submit_button("สมัครบัญชี", type="primary", width="stretch")
        if submit_signup:
            email = email.strip()
            if not valid_email(email) or len(password) < 8 or not consent:
                st.warning("กรอกอีเมลที่ถูกต้อง รหัสผ่านอย่างน้อย 8 ตัวอักษร และยืนยันการใช้ข้อมูลสมมติ")
            else:
                try:
                    with st.spinner("กำลังส่งคำขอสมัครบัญชี"):
                        client.auth.sign_up({"email": email, "password": password})
                    st.info("เปิดลิงก์ยืนยันในอีเมล แล้วกลับมาเข้าสู่ระบบ")
                except Exception:
                    st.error("สมัครไม่สำเร็จ ตรวจสอบอีเมลและลองใหม่ภายหลัง")


def fetch_rows(client, table, columns):
    rows = []
    cursor = None
    while True:
        query = client.table(table).select(columns).order("id", desc=True).limit(PAGE_SIZE)
        if cursor is not None:
            query = query.lt("id", cursor)
        batch = query.execute().data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            return rows
        cursor = batch[-1]["id"]


def task_groups(tasks, today):
    """Partition unfinished tasks with due dates using Bangkok calendar dates."""
    overdue, due_today, upcoming = [], [], []
    for task in tasks:
        if task["status"] in CLOSED_STATUSES or not task.get("due_date"):
            continue
        deadline = date.fromisoformat(task["due_date"])
        if deadline < today:
            overdue.append(task)
        elif deadline == today:
            due_today.append(task)
        elif deadline <= today + timedelta(days=3):
            upcoming.append(task)
    return overdue, due_today, upcoming


def task_table(tasks, project_names):
    today = datetime.now(BANGKOK).date().isoformat()
    st.dataframe([
        {"งาน": task["title"], "โครงการ": project_names.get(task["project_id"], "–"),
         "ผู้รับผิดชอบ": task["assignee"] or "–", "กำหนดส่ง": task["due_date"],
         "สถานะ": task["status"],
         "ความเร่งด่วน": ("เกินกำหนด" if task["due_date"] < today else "ครบกำหนดวันนี้")
         if task["due_date"] and task["due_date"] <= today and task["status"] not in CLOSED_STATUSES else "–"}
        for task in tasks
    ], hide_index=True, width="stretch")


def show_activity(client, limit):
    logs = client.table("activity_logs").select(
        "action,details,created_at"
    ).order("id", desc=True).limit(limit).execute().data or []
    if not logs:
        st.info("ยังไม่มีกิจกรรม")
        return
    st.dataframe([
        {"เวลา (ไทย)": datetime.fromisoformat(log["created_at"]).astimezone(BANGKOK).strftime("%d/%m/%Y %H:%M"),
         "กิจกรรม": log["action"], "รายละเอียด": log["details"]}
        for log in logs
    ], hide_index=True, width="stretch")


def dashboard(client, projects, docs, tasks, project_names):
    st.title("ภาพรวมสำนักงาน")
    now = datetime.now(BANGKOK)
    overdue, due_today, upcoming = task_groups(tasks, now.date())
    deadlines = sorted(due_today + upcoming, key=lambda task: task["due_date"])
    closed = sum(task["status"] == "เสร็จแล้ว" for task in tasks)
    active = sum(task["status"] not in CLOSED_STATUSES for task in tasks)
    metrics = [
        ("เอกสารทั้งหมด", len(docs), "description"),
        ("โครงการทั้งหมด", len(projects), "folder_open"),
        ("งานที่ยังไม่เสร็จ", active, "pending_actions"),
        ("งานเสร็จแล้ว", closed, "task_alt"),
        ("งานทั้งหมด", len(tasks), "checklist"),
        ("ใกล้ครบกำหนด", len(deadlines), "calendar_today"),
        ("เกินกำหนด", len(overdue), "event_busy"),
    ]
    with st.container(key="office_kpis"):
        for col, (label, value, icon) in zip(st.columns(4), metrics[:4]):
            col.metric(label, value, icon=f":material/{icon}:")
        with st.container(key="office_kpi_secondary"):
            for col, (label, value, icon) in zip(st.columns(3), metrics[4:]):
                col.metric(label, value, icon=f":material/{icon}:")
    with st.container(horizontal=True, gap="small"):
        for label, icon, target in [
            ("จัดการโครงการ", "create_new_folder", "โครงการ"),
            ("เปิดเอกสาร", "upload_file", "เอกสาร"),
            ("ดูงานทั้งหมด", "checklist", "ติดตามงาน"),
        ]:
            st.button(label, icon=f":material/{icon}:", key=f"quick_{target}",
                      on_click=workspace.navigate, args=(target,))
    with st.container(key="office_panel", border=True):
        st.subheader("ความคืบหน้าโครงการ")
        workspace.project_overview(projects, tasks, PROJECT_STATUSES)
    with st.container(key="office_deadlines", border=True):
        st.subheader("งานใกล้ครบกำหนด")
        st.caption("วันนี้และภายใน 3 วัน")
        if deadlines:
            workspace.task_list(deadlines[:8], project_names, now.date())
        else:
            st.caption("ไม่มีงานใกล้ครบกำหนด")
        if overdue:
            st.markdown("**งานเกินกำหนด**")
            workspace.task_list(sorted(overdue, key=lambda task: task["due_date"])[:8], project_names, now.date())
    left, right = st.columns(2)
    with left:
        st.subheader("เอกสารล่าสุด")
        if docs:
            st.dataframe([{"เอกสาร": doc["title"], "ประเภท": doc["file_type"].lstrip(".").upper()}
                          for doc in docs[:5]], hide_index=True, width="stretch")
        else:
            st.caption("ยังไม่มีเอกสาร")
    with right:
        st.subheader("กิจกรรมล่าสุด")
        show_activity(client, 6)
    if tasks:
        with st.expander("งานล่าสุด"):
            task_table(tasks[:30], project_names)


def finish(message):
    st.session_state["notice"] = message
    st.rerun()


def apply_change(query, message):
    if not query.execute().data:
        st.warning("รายการนี้ไม่มีแล้ว กรุณาเปิดหน้าใหม่")
        return
    finish(message)


def projects_page(client, projects, docs, tasks):
    st.title("โครงการ")
    if projects:
        workspace.project_cards(projects, tasks)
    with st.form("new_project"):
        st.subheader("เพิ่มโครงการ")
        name = st.text_input("ชื่อโครงการ", max_chars=150)
        description = st.text_area("รายละเอียด", max_chars=2000)
        assignee = st.text_input("ผู้รับผิดชอบ", max_chars=100)
        status = st.selectbox("สถานะโครงการ", PROJECT_STATUSES, index=1)
        if st.form_submit_button("เพิ่มโครงการ", type="primary"):
            if name.strip():
                apply_change(client.table("projects").insert({
                    "name": name.strip(), "description": description.strip(),
                    "assignee": assignee.strip(), "status": status,
                }), "เพิ่มโครงการแล้ว")
            else:
                st.warning("กรอกชื่อโครงการ")
    if not projects:
        st.info("ยังไม่มีโครงการ")
        return

    st.subheader("โครงการทั้งหมด")
    st.dataframe([
        {"โครงการ": item["name"], "ผู้รับผิดชอบ": item["assignee"] or "–",
         "สถานะ": item["status"], "รายละเอียด": item["description"]}
        for item in projects
    ], hide_index=True, width="stretch")
    by_id = {item["id"]: item for item in projects}
    selected = st.selectbox("เลือกโครงการเพื่อดูหรือแก้ไข", list(by_id),
                            format_func=lambda identifier: f"{by_id[identifier]['name']} (#{identifier})")
    item = by_id[selected]
    with st.form(f"edit_project_{selected}"):
        name = st.text_input("ชื่อโครงการ", value=item["name"], max_chars=150)
        description = st.text_area("รายละเอียด", value=item["description"], max_chars=2000)
        assignee = st.text_input("ผู้รับผิดชอบ", value=item["assignee"], max_chars=100)
        status = st.selectbox("สถานะโครงการ", PROJECT_STATUSES, index=PROJECT_STATUSES.index(item["status"])
                              if item["status"] in PROJECT_STATUSES else 0)
        if st.form_submit_button("บันทึกโครงการ", type="primary"):
            if name.strip():
                apply_change(client.table("projects").update({
                    "name": name.strip(), "description": description.strip(),
                    "assignee": assignee.strip(), "status": status,
                }).eq("id", selected), "บันทึกโครงการแล้ว")
            else:
                st.warning("กรอกชื่อโครงการ")

    linked = [doc["title"] for doc in docs if doc["project_id"] == selected]
    st.subheader("เอกสารที่เกี่ยวข้อง")
    if linked:
        st.dataframe([{"ชื่อเอกสาร": title} for title in linked], hide_index=True, width="stretch")
    else:
        st.caption("ยังไม่มีเอกสารที่เชื่อมกับโครงการ")
    with st.expander("ลบโครงการ"):
        st.caption("งานในโครงการจะถูกลบด้วย ย้ายหรือลบเอกสารที่เกี่ยวข้องก่อน")
        confirm = st.checkbox("ยืนยันการลบโครงการและงานในโครงการ", key=f"delete_project_{selected}")
        if st.button("ลบโครงการถาวร", disabled=not confirm):
            try:
                apply_change(client.table("projects").delete().eq("id", selected), "ลบโครงการแล้ว")
            except APIError as error:
                if error.code != "23503":
                    raise
                st.warning("โครงการยังมีเอกสารผูกอยู่ ย้ายหรือลบเอกสารก่อน")


def task_fields(project_names, item=None):
    projects = list(project_names)
    index = 0
    due = datetime.now(BANGKOK).date()
    status = TASK_STATUSES[0]
    if item:
        index = projects.index(item["project_id"])
        due = date.fromisoformat(item["due_date"]) if item["due_date"] else None
        if item["status"] in TASK_STATUSES:
            status = item["status"]
    project_id = st.selectbox("โครงการ", projects, index=index, format_func=project_names.__getitem__)
    title = st.text_input("ชื่องาน", value=item["title"] if item else "", max_chars=150)
    assignee = st.text_input("ผู้รับผิดชอบ", value=item["assignee"] if item else "", max_chars=100)
    status = st.selectbox("สถานะงาน", TASK_STATUSES, index=TASK_STATUSES.index(status))
    deadline = st.date_input("กำหนดส่ง", value=due, min_value=date(1, 1, 1), max_value=date(9999, 12, 31),
                             format="DD/MM/YYYY")
    return {"project_id": project_id, "title": title.strip(), "assignee": assignee.strip(),
            "status": status, "due_date": deadline.isoformat() if deadline else None}


def tasks_page(client, project_names, tasks):
    st.title("ติดตามงาน")
    if not project_names:
        st.info("สร้างโครงการก่อนเพิ่มงาน")
        return
    with st.form("new_task"):
        st.subheader("เพิ่มงาน")
        fields = task_fields(project_names)
        if st.form_submit_button("เพิ่มงาน", type="primary"):
            if fields["title"]:
                apply_change(client.table("tasks").insert(fields), "เพิ่มงานแล้ว")
            else:
                st.warning("กรอกชื่องาน")
    if not tasks:
        st.info("ยังไม่มีงาน")
        return
    st.subheader("งานทั้งหมด")
    project_filter = st.selectbox("กรองตามโครงการ", [None, *project_names],
                                  format_func=lambda key: "ทุกโครงการ" if key is None else project_names[key])
    visible_tasks = [task for task in tasks if project_filter is None or task["project_id"] == project_filter]
    if not visible_tasks:
        st.info("ยังไม่มีงานในโครงการนี้")
        return
    workspace.task_list(visible_tasks, project_names, datetime.now(BANGKOK).date())
    tasks = visible_tasks
    by_id = {task["id"]: task for task in tasks}
    selected = st.selectbox("เลือกงานเพื่อดูหรือแก้ไข", list(by_id),
                            format_func=lambda identifier: f"{by_id[identifier]['title']} (#{identifier})")
    if by_id[selected]["project_id"] not in project_names:
        st.info("ข้อมูลโครงการเปลี่ยนแล้ว กรุณาเปิดหน้าใหม่")
        return
    with st.form(f"edit_task_{selected}"):
        fields = task_fields(project_names, by_id[selected])
        if st.form_submit_button("บันทึกงาน", type="primary"):
            if fields["title"]:
                apply_change(client.table("tasks").update(fields).eq("id", selected), "บันทึกงานแล้ว")
            else:
                st.warning("กรอกชื่องาน")
    with st.expander("ลบงาน"):
        confirm = st.checkbox("ยืนยันการลบงาน", key=f"delete_task_{selected}")
        if st.button("ลบงานถาวร", disabled=not confirm):
            apply_change(client.table("tasks").delete().eq("id", selected), "ลบงานแล้ว")


def upload_document(client, user_id, title, project_id, filename, payload):
    try:
        content, mime = extract_document(filename, payload)
    except ValueError as error:
        st.warning(str(error))
        return
    filename = Path(filename).name
    ext = Path(filename).suffix.lower()
    storage_path = f"{user_id}/{uuid4().hex}{ext}"
    bucket = client.storage.from_(BUCKET)
    bucket.upload(storage_path, payload, {"content-type": mime, "upsert": "false"})
    try:
        client.table("documents").insert({
            "project_id": project_id, "title": title, "original_name": filename[:200],
            "file_type": ext, "storage_path": storage_path, "content": content,
        }).execute()
    except APIError as error:
        # Only compensate a confirmed database rejection. A transport failure can
        # happen after commit and deleting the object then would break the row.
        if (error.code or "").startswith(("22", "23", "42")):
            bucket.remove([storage_path])
        raise
    finish("บันทึกเอกสารแล้ว" if content.strip() else "บันทึกเอกสารแล้ว ไฟล์นี้ไม่มีข้อความที่อ่านได้")


@st.dialog("อัปโหลดเอกสาร", width="medium")
def document_upload_dialog(client, user_id, options):
    with st.form("upload_document", clear_on_submit=True):
        title = st.text_input("ชื่อเอกสาร", max_chars=150)
        project = st.selectbox("โครงการที่เกี่ยวข้อง", list(options), format_func=options.__getitem__)
        uploaded = st.file_uploader("ไฟล์ PDF, DOCX หรือ TXT ขนาดไม่เกิน 3 MB", type=["pdf", "docx", "txt"])
        if st.form_submit_button("อัปโหลดเอกสาร", type="primary"):
            if not title.strip() or uploaded is None:
                st.warning("กรอกชื่อเอกสารและเลือกไฟล์")
            else:
                with st.spinner("กำลังตรวจไฟล์และอัปโหลด"):
                    try:
                        upload_document(client, user_id, title.strip(), project, uploaded.name, uploaded.getvalue())
                    except Exception:
                        st.error("อัปโหลดไม่สำเร็จ กรุณาลองอีกครั้ง")


def documents_page(client, user_id, project_names, docs):
    st.title("เอกสาร")
    options = {None: "ไม่ผูกกับโครงการ", **project_names}
    if st.button("อัปโหลดเอกสาร", icon=":material/upload_file:", type="primary"):
        document_upload_dialog(client, user_id, options)
    if not docs:
        st.info("ยังไม่มีเอกสาร")
        return
    with st.container(horizontal=True, key="document_filters"):
        keyword = st.text_input("ค้นหาชื่อเอกสาร").strip().casefold()
        format_filter = st.selectbox("ประเภทไฟล์", ["ทั้งหมด", ".pdf", ".docx", ".txt"],
                                     format_func=lambda value: value.lstrip(".").upper() if value.startswith(".") else value)
    filtered = [doc for doc in docs if keyword in doc["title"].casefold()
                and (format_filter == "ทั้งหมด" or doc["file_type"] == format_filter)]
    if not filtered:
        st.info("ไม่พบเอกสารที่ตรงกับคำค้น")
        return
    st.dataframe([
        {"ชื่อเอกสาร": doc["title"], "ไฟล์": doc["original_name"],
         "ประเภท": doc["file_type"], "โครงการ": options.get(doc["project_id"], "–")}
        for doc in filtered
    ], hide_index=True, width="stretch")
    by_id = {doc["id"]: doc for doc in filtered}
    selected = st.selectbox("เลือกเอกสารเพื่อดูหรือแก้ไข", list(by_id),
                            format_func=lambda identifier: f"{by_id[identifier]['title']} (#{identifier})")
    doc = by_id[selected]
    st.badge(doc["file_type"].lstrip(".").upper(), icon=":material/description:")
    with st.form(f"edit_document_{selected}"):
        title = st.text_input("ชื่อเอกสาร", value=doc["title"], max_chars=150)
        project = st.selectbox("โครงการที่เกี่ยวข้อง", list(options), format_func=options.__getitem__,
                               index=list(options).index(doc["project_id"]) if doc["project_id"] in options else 0)
        if st.form_submit_button("บันทึกเอกสาร", type="primary"):
            if title.strip():
                apply_change(client.table("documents").update({"title": title.strip(), "project_id": project})
                             .eq("id", selected), "บันทึกข้อมูลเอกสารแล้ว")
            else:
                st.warning("กรอกชื่อเอกสาร")
    if st.toggle("แสดงตัวอย่างข้อความ", key=f"preview_{selected}"):
        rows = client.table("documents").select("content").eq("id", selected).execute().data
        content = rows[0]["content"][:4000] if rows else ""
        if content:
            st.text_area("ข้อความจากต้นฉบับ", value=content, height=170, disabled=True)
        else:
            st.caption("ไฟล์นี้ไม่มีข้อความที่อ่านได้")

    bucket = client.storage.from_(BUCKET)
    if st.button("เตรียมดาวน์โหลด", key=f"download_{selected}"):
        try:
            signed = bucket.create_signed_url(doc["storage_path"], 60, {"download": doc["original_name"]})
            st.link_button("ดาวน์โหลดไฟล์ต้นฉบับ", signed["signedURL"], type="primary")
            st.caption("ลิงก์ใช้ได้ 60 วินาที")
        except Exception:
            st.error("เปิดไฟล์ต้นฉบับไม่สำเร็จ กรุณาลองใหม่")
    with st.expander("ลบเอกสาร", key=f"office_delete_document_{selected}"):
        confirm = st.checkbox("ยืนยันการลบไฟล์และข้อมูลเอกสาร", key=f"delete_document_{selected}")
        if st.button("ลบเอกสารถาวร", disabled=not confirm):
            with st.spinner("กำลังลบไฟล์และข้อมูลเอกสาร"):
                # Keep the row available for retry if the Storage operation fails.
                bucket.remove([doc["storage_path"]])
                apply_change(client.table("documents").delete().eq("id", selected), "ลบเอกสารแล้ว")


def reminder_page(tasks, project_names):
    st.title("แจ้งเตือนกำหนดส่ง")
    labels = ("เกินกำหนด", "ครบกำหนดวันนี้", "ภายใน 3 วัน")
    groups = task_groups(tasks, datetime.now(BANGKOK).date())
    for column, label, group in zip(st.columns(3), labels, groups):
        column.metric(label, len(group), border=True)
    for label, group in zip(labels, groups):
        st.subheader(label)
        if group:
            task_table(sorted(group, key=lambda task: task["due_date"]), project_names)
        else:
            st.caption("ไม่มีงานในกลุ่มนี้")


def main():
    workspace.apply_theme()
    client, user = start_client()
    if user is None:
        login_screen(client)
        return

    section = st.session_state.get("section", "ภาพรวม")
    with st.sidebar:
        workspace.sidebar(section)
        if st.button("ออกจากระบบ", icon=":material/logout:", width="stretch"):
            try:
                client.auth.sign_out({"scope": "local"})
            except Exception:
                pass
            st.session_state.clear()
            st.rerun()

    workspace.toolbar(section, datetime.now(BANGKOK))
    notice = st.session_state.pop("notice", None)
    if notice:
        st.success(notice)
    try:
        if section == "ตั้งค่า":
            workspace.settings(user)
            return
        if section == "ประวัติ":
            st.title("ประวัติการทำงาน")
            show_activity(client, 100)
            return
        with st.spinner("กำลังโหลดข้อมูลสำนักงาน"):
            projects = fetch_rows(client, "projects", "id,name,description,assignee,status")
            project_names = {project["id"]: project["name"] for project in projects}
            if section in {"ภาพรวม", "โครงการ", "เอกสาร"}:
                docs = fetch_rows(client, "documents", "id,project_id,title,original_name,file_type,storage_path")
            if section in {"ภาพรวม", "โครงการ", "ติดตามงาน", "แจ้งเตือน"}:
                tasks = fetch_rows(client, "tasks", "id,project_id,title,assignee,due_date,status")
        if section == "ภาพรวม":
            dashboard(client, projects, docs, tasks, project_names)
        elif section == "โครงการ":
            projects_page(client, projects, docs, tasks)
        elif section == "ติดตามงาน":
            tasks_page(client, project_names, tasks)
        elif section == "เอกสาร":
            documents_page(client, str(user.id), project_names, docs)
        else:
            reminder_page(tasks, project_names)
    except Exception:
        st.error("ทำรายการไม่สำเร็จ กรุณาลองอีกครั้ง หากยังพบปัญหาให้ตรวจสอบการตั้งค่า Supabase")


if __name__ == "__main__":
    main()
