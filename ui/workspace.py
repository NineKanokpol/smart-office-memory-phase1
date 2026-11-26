"""Presentation helpers for the Smart Office workspace."""
from collections import Counter
from datetime import date
from html import escape
from pathlib import Path

import streamlit as st

STYLE = Path(__file__).with_name("liquid-glass.css")
NAVIGATION = {
    "ภาพรวม": ("แดชบอร์ด", "space_dashboard"),
    "เอกสาร": ("เอกสารสำนักงาน", "description"),
    "โครงการ": ("จัดการโครงการ", "folder_open"),
    "ติดตามงาน": ("ติดตามงาน", "task_alt"),
    "ประวัติ": ("ประวัติการใช้งาน", "history"),
    "ตั้งค่า": ("ตั้งค่า", "settings"),
}


def apply_theme():
    st.html(STYLE)
    if st.session_state.get("solid_surfaces"):
        st.html('<span class="office-solid" hidden></span>')


def navigate(section):
    st.session_state["section"] = section


def brand(mark_only=False):
    wordmark = "" if mark_only else "<div><strong>Smart Office</strong><small>MEMORY</small></div>"
    st.html(f"""
        <div class="office-brand">
            <span class="office-mark" aria-hidden="true"><i></i><i></i><i></i></span>
            {wordmark}
        </div>
    """)


def sidebar(section):
    brand()
    st.caption("พื้นที่ทำงาน")
    for page, (label, icon) in NAVIGATION.items():
        st.button(label, icon=f":material/{icon}:", type="primary" if page == section else "tertiary",
                  key=f"sidebar_{page}", width="stretch", on_click=navigate, args=(page,))
    st.divider()
    st.markdown("**บัญชีสำนักงาน**")


def toolbar(section, now):
    name = NAVIGATION.get(section, ("แจ้งเตือนกำหนดส่ง", ""))[0]
    with st.container(key="office_toolbar", horizontal=True, vertical_alignment="center"):
        st.html(f'<span class="office-crumb">พื้นที่ทำงาน <span aria-hidden="true">/</span> <strong>{name}</strong></span>',
                width="content")
        st.space("stretch")
        st.html(f'<time class="office-time" datetime="{now.isoformat()}">{now:%d/%m/%Y · %H:%M} น. ICT</time>',
                width="content")
        st.button("แจ้งเตือน", icon=":material/notifications:", type="tertiary",
                  key="office_notifications", on_click=navigate, args=("แจ้งเตือน",))
        st.button("ธีมและบัญชี", icon=":material/contrast:", type="tertiary",
                  key="office_preferences", on_click=navigate, args=("ตั้งค่า",))


def settings(user):
    st.title("ตั้งค่า")
    with st.container(border=True):
        st.subheader("ผู้ใช้งาน")
        st.text(user.email or "บัญชีทดลอง")
    with st.container(border=True):
        st.subheader("การแสดงผล")
        st.caption("เปิดเมนู ⋮ แล้วเลือก System, Light หรือ Dark ในกลุ่ม Theme")
        st.toggle("ใช้พื้นผิวทึบและลดความโปร่งใส", key="solid_surfaces")


def project_statistics(tasks):
    totals = Counter()
    completed = Counter()
    for task in tasks:
        if task["status"] == "ยกเลิก":
            continue
        project_id = task["project_id"]
        totals[project_id] += 1
        completed[project_id] += task["status"] == "เสร็จแล้ว"
    return totals, completed


def progress_markup(label, value, total):
    percent = round(100 * value / total) if total else 0
    return (f'<div class="office-progress"><div><span>{escape(label)}</span>'
            f'<strong>{percent}%</strong></div><progress aria-label="{escape(label)}" '
            f'max="100" value="{percent}">{percent}%</progress></div>')


def project_overview(projects, tasks, statuses):
    if not projects:
        st.caption("ยังไม่มีโครงการสำหรับสรุปความคืบหน้า")
        return
    counts = Counter(project["status"] for project in projects)
    colors = ("var(--office-accent)", "var(--office-highlight)", "var(--office-complete)", "var(--office-track)")
    segments, legend, offset = [], [], 0
    for status, color in zip(statuses, colors):
        count = counts[status]
        if count:
            end = offset + count * 100 / len(projects)
            segments.append(f"{color} {offset}% {end}%")
            offset = end
        legend.append(f'<li><i style="background:{color}" aria-hidden="true"></i>{escape(status)}<strong>{count}</strong></li>')
    ring = f'conic-gradient({", ".join(segments)})' if len(segments) > 1 else (segments[0].split(" ")[0] if segments else "var(--office-track)")
    totals, completed = project_statistics(tasks)
    bars = ''.join(progress_markup(p["name"], completed[p["id"]], totals[p["id"]]) for p in projects[:4])
    st.html(f"""
        <div class="office-chart">
            <div class="office-distribution">
                <div class="office-ring" style="background:{ring}" aria-hidden="true">
                    <div><strong>{len(projects)}</strong><small>โครงการ</small></div>
                </div><ul aria-label="สถานะโครงการ">{''.join(legend)}</ul>
            </div>
            <div class="office-bars">{bars}</div>
        </div>
    """)
    st.caption("ความคืบหน้าคิดจากงานเสร็จแล้วเทียบกับงานทั้งหมดของแต่ละโครงการ โดยไม่นับงานที่ยกเลิก")


def project_cards(projects, tasks):
    totals, completed = project_statistics(tasks)
    cards = []
    for project in projects[:6]:
        project_id = project["id"]
        done, total = completed[project_id], totals[project_id]
        percent = round(100 * done / total) if total else 0
        progress = progress_markup("ความคืบหน้า", done, total)
        cards.append(f"""
            <article class="office-project">
                <span class="office-chip">{escape(project["status"])}</span>
                <h3>{escape(project["name"])}</h3>
                <p>{escape(project["assignee"] or "ยังไม่มีผู้รับผิดชอบ")}</p>
                <div class="office-card-progress">
                    <i class="office-mini-ring" style="--done:{percent}%" aria-hidden="true"></i>
                    {progress}
                </div>
            </article>
        """)
    st.html(f'<div class="office-projects">{"".join(cards)}</div>')


def task_list(tasks, project_names, today):
    rows = []
    for task in tasks:
        status = task["status"]
        deadline = date.fromisoformat(task["due_date"]) if task["due_date"] else None
        priority = ""
        if deadline and status not in {"เสร็จแล้ว", "ยกเลิก"}:
            if deadline < today:
                priority = "เกินกำหนด"
            elif deadline == today:
                priority = "ครบกำหนดวันนี้"
        project = project_names.get(task["project_id"], "–")
        assignee = task["assignee"] or "ยังไม่มีผู้รับผิดชอบ"
        due = deadline.strftime("%d/%m/%Y") if deadline else "ไม่กำหนดวันส่ง"
        rows.append(f"""
            <li>
                <div><strong>{escape(task["title"])}</strong>
                     <small>{escape(project)} · {escape(assignee)}</small></div>
                <div class="office-task-status"><small>{due}</small>
                    <span class="office-chip">{escape(status)}</span>
                    {f'<span class="office-chip office-urgent">{priority}</span>' if priority else ''}
                </div>
            </li>
        """)
    st.html(f'<ul class="office-task-list" aria-label="รายการงาน">{"".join(rows)}</ul>')
