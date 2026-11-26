# ติดตั้งและรันบนเครื่อง

## เตรียม Python 3.12

เปิด Terminal ในโฟลเดอร์โปรเจกต์ เลือกคำสั่งตามเครื่อง

**Windows PowerShell**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

**macOS หรือ Linux**

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
```

## ตั้ง Supabase

1. สร้างโปรเจกต์ในองค์กรแผน **Free** หรือเลือกโปรเจกต์ทดสอบที่อนุญาตให้ใช้
2. เปิด **SQL Editor** วางเนื้อหาทั้งหมดจาก `schema.sql` แล้วกด **Run** สำหรับฐานที่ใช้ schema รุ่นเก่า สคริปต์จะเพิ่มช่องผู้รับผิดชอบและปรับ FK โดยเก็บข้อมูลเดิมไว้
3. ใน **Authentication** เปิด Email provider และ **Confirm email** กำหนดรหัสผ่านขั้นต่ำ 8 ตัวอักษร
4. ตั้ง **Authentication → URL Configuration → Site URL** เป็น URL ของแอป สำหรับเครื่องทดสอบใช้ `http://localhost:8501` เมื่อมี URL จริงแล้วให้ตั้ง Site URL เป็น HTTPS ของเว็บนั้น
5. ใน **Connect** หรือ **Project Settings → API Keys** คัดลอก Project URL และ Publishable key เปิด `.streamlit/secrets.toml.example` แล้วบันทึกสำเนาเป็น `.streamlit/secrets.toml` ใส่ค่าของโปรเจกต์ตามตัวอย่าง

```toml
SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "YOUR_PUBLISHABLE_OR_ANON_KEY"
```

Supabase SMTP ค่าเริ่มต้นส่งอีเมลได้เฉพาะที่อยู่ของสมาชิกทีมโครงการและมีขีดจำกัดการส่ง ถ้าจะให้นักศึกษาหรืออาจารย์สมัครด้วยอีเมลนอกทีม ให้ตั้งค่า SMTP ที่คุณได้รับอนุญาตให้ใช้และอยู่ในโควตาฟรีก่อนเปิดรับสมัคร ใช้กล่องอีเมลทดสอบที่รับจดหมายได้จริงใน cloud และใช้ Mailpit สำหรับข้อมูลสมมติบนเครื่อง ดูการตั้งค่าและข้อจำกัดที่ [คู่มือ Supabase SMTP](https://supabase.com/docs/guides/auth/auth-smtp)

## เปิดเว็บและทดสอบ

Windows ใช้ `.\.venv\Scripts\python.exe -m streamlit run app.py` ส่วน macOS/Linux ใช้ `.venv/bin/python -m streamlit run app.py` เปิด [localhost:8501](http://localhost:8501) แล้วตรวจว่าหน้าเข้าสู่ระบบแสดงครบ

ติดตั้ง pytest ใน environment เดิมแล้วรัน `python -m pytest -q` จากโฟลเดอร์โปรเจกต์ สำหรับการทดสอบพร้อมฐานข้อมูลและเบราว์เซอร์ให้ใช้ขั้นตอนใน [รายงานทดสอบ](TEST_REPORT.md)
