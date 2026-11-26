"""Run against a disposable local Supabase stack with Mailpit and Streamlit."""
import os
import time
import tomllib
from html.parser import HTMLParser
from pathlib import Path
from uuid import uuid4

import pytest

SETTINGS = os.environ.get("OFFICE_E2E_SECRETS")
pytestmark = pytest.mark.skipif(not SETTINGS, reason="requires a disposable local Supabase and Streamlit")


class ConfirmationLink(HTMLParser):
    url = None

    def handle_starttag(self, tag, attrs):
        href = dict(attrs).get("href", "")
        if tag == "a" and "/auth/v1/verify?" in href:
            self.url = href


def confirm_email(httpx, email, mailpit):
    for _ in range(40):
        response = httpx.get(f"{mailpit}/api/v1/search", params={"query": f"to:{email}"})
        response.raise_for_status()
        messages = response.json()["messages"]
        if messages:
            message = httpx.get(f"{mailpit}/api/v1/message/{messages[0]['ID']}")
            message.raise_for_status()
            link = ConfirmationLink()
            link.feed(message.json()["HTML"])
            assert link.url
            assert httpx.get(link.url).status_code in (302, 303)
            return
        time.sleep(0.25)
    pytest.fail("No confirmation email reached Mailpit")


def sign_in(page, email, password):
    page.get_by_label("อีเมล", exact=True).fill(email)
    page.get_by_label("รหัสผ่าน", exact=True).fill(password)
    page.get_by_role("button", name="เข้าสู่ระบบ", exact=True).click()


def visit(page, section):
    sidebar = page.get_by_test_id("stSidebar")
    if not sidebar.get_by_text(section, exact=True).is_visible():
        page.get_by_test_id("stSidebarCollapsedControl").click()
    sidebar.get_by_text(section, exact=True).click()
    # The heading confirms that Streamlit processed the menu change.
    heading = {"ภาพรวม": "ภาพรวมสำนักงาน", "แจ้งเตือน": "แจ้งเตือนกำหนดส่ง",
               "ประวัติ": "ประวัติการทำงาน"}.get(section, section)
    page.get_by_role("heading", name=heading, exact=True).wait_for()


def assert_isolation(url, key, email_a, email_b, password, project, document, task, path, body):
    import httpx
    from postgrest.exceptions import APIError
    from storage3.exceptions import StorageApiError
    from supabase import create_client

    anonymous, a, b = (create_client(url, key) for _ in range(3))
    a.auth.sign_in_with_password({"email": email_a, "password": password})
    b.auth.sign_in_with_password({"email": email_b, "password": password})
    for table, identifier, change in (
        ("projects", project, {"assignee": "บัญชี B"}),
        ("documents", document, {"title": "บัญชี B"}),
        ("tasks", task, {"title": "บัญชี B"}),
    ):
        with pytest.raises(APIError):
            anonymous.table(table).select("id").eq("id", identifier).execute()
        assert b.table(table).select("id").eq("id", identifier).execute().data == []
        assert b.table(table).update(change).eq("id", identifier).execute().data == []
        assert b.table(table).delete().eq("id", identifier).execute().data == []
        assert a.table(table).select("id").eq("id", identifier).execute().data == [{"id": identifier}]

    with pytest.raises(APIError):
        b.table("tasks").insert({"project_id": project, "title": "งานข้ามบัญชี"}).execute()
    with pytest.raises(APIError):
        a.table("activity_logs").insert({"action": "กิจกรรมปลอม"}).execute()
    assert b.table("activity_logs").select("id").execute().data == []
    with pytest.raises(APIError):
        anonymous.table("activity_logs").select("id").execute()
    with pytest.raises(APIError) as rejection:
        a.table("projects").delete().eq("id", project).execute()
    assert rejection.value.code == "23503"

    bucket = "office-docs"
    for client in (b, anonymous):
        storage = client.storage.from_(bucket)
        with pytest.raises(StorageApiError):
            storage.download(path)
        with pytest.raises(StorageApiError):
            storage.create_signed_url(path, 30)
        if client is b:
            assert storage.remove([path]) == []
    assert a.storage.from_(bucket).download(path) == body
    public = httpx.get(f"{url}/storage/v1/object/public/{bucket}/{path}")
    assert public.status_code in {400, 401, 403, 404}
    return a


def test_local_auth_crud_isolation_and_responsive_ui():
    import httpx
    from playwright.sync_api import expect, sync_playwright

    config = tomllib.loads(Path(SETTINGS).read_text())
    url, key = config["SUPABASE_URL"], config["SUPABASE_PUBLISHABLE_KEY"]
    assert url.startswith(("http://127.0.0.1:", "http://localhost:"))
    app_url = os.environ.get("OFFICE_E2E_APP", "http://127.0.0.1:8501")
    mailpit = os.environ.get("OFFICE_E2E_MAILPIT", "http://127.0.0.1:54324")
    code = uuid4().hex[:10]
    email_a, email_b = [f"office-{account}-{code}@example.com" for account in ("a", "b")]
    password = uuid4().hex
    assert httpx.get(f"{app_url}/_stcore/health").status_code == 200

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        desktop = browser.new_context(color_scheme="light", viewport={"width": 1440, "height": 900})
        mobile = browser.new_context(color_scheme="dark", viewport={"width": 390, "height": 844},
                                     is_mobile=True, has_touch=True, accept_downloads=True)
        page, second = desktop.new_page(), mobile.new_page()
        errors = []
        for tab in (page, second):
            tab.set_default_timeout(15_000)
            tab.on("pageerror", lambda error: errors.append(str(error)))
        for tab, email in ((page, email_a), (second, email_b)):
            tab.goto(app_url)
            expect(tab.get_by_role("heading", name="Smart Office Memory")).to_be_visible()
            expect(tab.get_by_text("เมนูหลัก", exact=True)).to_have_count(0)
            tab.get_by_role("tab", name="สมัครบัญชี").click()
            tab.get_by_label("อีเมลสำหรับสมัคร").fill(email)
            tab.get_by_label("ตั้งรหัสผ่าน", exact=False).fill(password)
            tab.get_by_text("ฉันจะใช้เฉพาะข้อมูลสมมติ").click()
            tab.get_by_role("button", name="สมัครบัญชี", exact=True).click()
            expect(tab.get_by_text("เปิดลิงก์ยืนยันในอีเมล แล้วกลับมาเข้าสู่ระบบ")).to_be_visible()
            tab.get_by_role("tab", name="เข้าสู่ระบบ").click()
            sign_in(tab, email, password)
            expect(tab.get_by_text("เข้าสู่ระบบไม่สำเร็จ", exact=False)).to_be_visible()
            confirm_email(httpx, email, mailpit)
            sign_in(tab, email, password)
            expect(tab.get_by_role("heading", name="ภาพรวมสำนักงาน")).to_be_visible()
        print("PASS startup, anonymous gate, registration, email confirmation, login")

        project_name = f"โครงการทดลอง {code}"
        visit(page, "โครงการ")
        page.get_by_label("ชื่อโครงการ", exact=True).fill(project_name)
        page.get_by_label("รายละเอียด", exact=True).fill("รายละเอียดตัวอย่าง")
        page.get_by_label("ผู้รับผิดชอบ", exact=True).fill("นักศึกษาสมมติ")
        page.get_by_role("button", name="เพิ่มโครงการ", exact=True).click()
        expect(page.get_by_text("เพิ่มโครงการแล้ว")).to_be_visible()
        edit_project = page.get_by_test_id("stForm").filter(has_text="บันทึกโครงการ")
        edit_project.get_by_label("รายละเอียด", exact=True).fill("ปรับรายละเอียด")
        edit_project.get_by_role("button", name="บันทึกโครงการ").click()
        expect(page.get_by_text("บันทึกโครงการแล้ว")).to_be_visible()

        visit(page, "ติดตามงาน")
        task_title = f"งานทดลอง {code}"
        page.get_by_label("ชื่องาน", exact=True).fill(task_title)
        page.get_by_label("ผู้รับผิดชอบ", exact=True).fill("ผู้ช่วยสมมติ")
        page.get_by_role("button", name="เพิ่มงาน", exact=True).click()
        expect(page.get_by_text("เพิ่มงานแล้ว")).to_be_visible()
        edit_task = page.get_by_test_id("stForm").filter(has_text="บันทึกงาน")
        edit_task.get_by_label("ชื่องาน", exact=True).fill("งานฉบับแก้ไข")
        edit_task.get_by_role("button", name="บันทึกงาน").click()
        expect(page.get_by_text("บันทึกงานแล้ว")).to_be_visible()

        visit(page, "เอกสาร")
        body = "เอกสารสำหรับทดสอบระบบ".encode()
        page.get_by_label("ชื่อเอกสาร", exact=True).fill(f"บันทึกทดลอง {code}")
        page.get_by_role("combobox", name="โครงการที่เกี่ยวข้อง").click()
        page.get_by_text(project_name, exact=True).click()
        page.locator('input[type="file"]').set_input_files(
            {"name": "เอกสารทดลอง.txt", "mimeType": "text/plain", "buffer": body}
        )
        page.get_by_role("button", name="อัปโหลดเอกสาร", exact=True).click()
        expect(page.get_by_text("บันทึกเอกสารแล้ว", exact=True)).to_be_visible()
        search = page.get_by_label("ค้นหาชื่อเอกสาร")
        search.fill("ผลการค้นหาที่ไม่มี")
        search.press("Enter")
        expect(page.get_by_text("ไม่พบเอกสารที่ตรงกับคำค้น")).to_be_visible()
        search.fill(code)
        search.press("Enter")
        edit_document = page.get_by_test_id("stForm").filter(has_text="บันทึกเอกสาร")
        edit_document.get_by_label("ชื่อเอกสาร", exact=True).fill(f"รายงานปรับปรุง {code}")
        edit_document.get_by_role("button", name="บันทึกเอกสาร", exact=True).click()
        expect(page.get_by_text("บันทึกข้อมูลเอกสารแล้ว")).to_be_visible()
        page.get_by_role("button", name="เตรียมดาวน์โหลด").click()
        link = page.get_by_role("link", name="ดาวน์โหลดไฟล์ต้นฉบับ")
        response = desktop.request.get(link.get_attribute("href"))
        assert response.ok
        assert response.body() == body
        assert "attachment" in response.headers["content-disposition"]
        print("PASS project/task edit, TXT upload, search, metadata edit, signed download")

        from supabase import create_client

        a = create_client(url, key)
        a.auth.sign_in_with_password({"email": email_a, "password": password})
        project = a.table("projects").select("id,description").single().execute().data
        document = a.table("documents").select("id,storage_path,project_id").single().execute().data
        task = a.table("tasks").select("id,title").single().execute().data
        assert project["description"] == "ปรับรายละเอียด"
        assert task["title"] == "งานฉบับแก้ไข"
        assert document["project_id"] == project["id"]
        a = assert_isolation(url, key, email_a, email_b, password, project["id"], document["id"],
                             task["id"], document["storage_path"], body)
        print("PASS direct API RLS, private bucket, cross-account object access and project FK")

        visit(page, "ภาพรวม")
        assert page.get_by_test_id("stMetricValue").all_text_contents() == ["1", "1", "1", "1", "1", "0"]
        assert second.get_by_test_id("stMetricValue").all_text_contents() == ["0"] * 6
        expect(page.get_by_role("heading", name="กิจกรรมล่าสุด")).to_be_visible()
        assert len(a.table("activity_logs").select("id").execute().data) == 6
        assert page.locator("body").evaluate("(element) => getComputedStyle(element).backgroundColor") == "rgb(252, 249, 250)"
        assert second.locator("body").evaluate("(element) => getComputedStyle(element).backgroundColor") == "rgb(23, 20, 26)"
        assert second.evaluate("document.documentElement.scrollWidth === innerWidth")
        sidebar = page.get_by_test_id("stSidebar")
        sidebar.get_by_role("button", name="ออกจากระบบ").click()
        expect(page.get_by_role("heading", name="Smart Office Memory")).to_be_visible()
        sign_in(page, email_a, password)
        expect(page.get_by_role("heading", name="ภาพรวมสำนักงาน")).to_be_visible()
        assert page.get_by_test_id("stMetricValue").all_text_contents()[:3] == ["1", "1", "1"]
        visit(page, "ประวัติ")
        assert page.get_by_test_id("stDataFrame").count() == 1
        print("PASS dashboard accuracy, activity, desktop light, mobile dark, logout and persistence")

        visit(page, "ติดตามงาน")
        page.get_by_text("ลบงาน", exact=True).click()
        delete = page.get_by_role("button", name="ลบงานถาวร")
        expect(delete).to_be_disabled()
        page.get_by_text("ยืนยันการลบงาน", exact=True).click()
        delete.click()
        expect(page.get_by_text("ลบงานแล้ว")).to_be_visible()

        visit(page, "เอกสาร")
        page.get_by_text("ลบเอกสาร", exact=True).click()
        delete = page.get_by_role("button", name="ลบเอกสารถาวร")
        expect(delete).to_be_disabled()
        page.get_by_text("ยืนยันการลบไฟล์และข้อมูลเอกสาร", exact=True).click()
        delete.click()
        expect(page.get_by_text("ลบเอกสารแล้ว")).to_be_visible()

        visit(page, "โครงการ")
        page.get_by_text("ลบโครงการ", exact=True).click()
        delete = page.get_by_role("button", name="ลบโครงการถาวร")
        expect(delete).to_be_disabled()
        page.get_by_text("ยืนยันการลบโครงการและงานในโครงการ", exact=True).click()
        delete.click()
        expect(page.get_by_text("ลบโครงการแล้ว")).to_be_visible()
        assert a.table("projects").select("id").execute().data == []
        assert a.table("documents").select("id").execute().data == []
        assert a.table("tasks").select("id").execute().data == []
        assert not errors
        print("PASS delete confirmations and persisted removals")
        browser.close()
