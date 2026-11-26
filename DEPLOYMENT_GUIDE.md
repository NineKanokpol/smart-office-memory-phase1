# เผยแพร่บน Streamlit Community Cloud

## เตรียม GitHub และ Supabase

- ใช้ repository ชื่อ `smart-office-memory-phase1` และ branch `main` ตรวจว่ามี `app.py`, `requirements.txt`, `schema.sql` และ `.streamlit/config.toml`
- ก่อน commit ตรวจ `git status --short` และ `git diff --cached --stat` ให้แน่ใจว่าไม่มีไฟล์ `.env`, `secrets.toml`, รหัสผ่าน หรือเอกสารจริง
- ทำ [คู่มือติดตั้ง](SETUP_GUIDE.md) ใน Supabase องค์กรแผน **Free** และตรวจ bucket `office-docs` ว่าเป็น Private
- ใช้การยืนยันอีเมล ถ้าจะรับผู้สมัครนอกทีม Supabase ให้ทดสอบการส่งจดหมายผ่าน custom SMTP ภายในโควตาฟรี

## สร้างแอป

1. ลงชื่อเข้า [Streamlit Community Cloud](https://share.streamlit.io/) และเชื่อมบัญชี GitHub ที่มีสิทธิ์ใน repository
2. เลือก **Create app → Deploy a public app from GitHub** กรอกชื่อ repository, branch `main` และ main file `app.py`
3. ตั้ง **Advanced settings** ให้ใช้ Python **3.12** แล้วใส่ `SUPABASE_URL` และ `SUPABASE_PUBLISHABLE_KEY` ในช่อง **Secrets** ด้วยรูปแบบ TOML
4. เมื่อผลทดสอบความปลอดภัยผ่านตาม [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md) ให้กด **Deploy** เปิด **Manage app** เพื่อตรวจ logs และตรวจ visibility ในการตั้งค่าแอป
5. ตั้ง Supabase **Site URL** เป็น URL HTTPS ที่ได้ เปิดแอปด้วย Incognito แล้วทำรายการทดสอบ Public E2E ใน [TEST_REPORT.md](TEST_REPORT.md) ก่อนส่ง URL ให้อาจารย์

ถ้าหน้าเว็บขึ้นข้อความเกี่ยวกับ Supabase ให้ตรวจชื่อ secret ทั้งสอง ค่า Project URL และผลรัน `schema.sql` ถ้าหน้าแอปหลับ ให้กดปลุกจากหน้าเว็บ ตรวจ Supabase Dashboard ด้วยหากโปรเจกต์พัก

## ค่าใช้จ่าย

Stack นี้ออกแบบให้ใช้ได้ที่ **$0** ในโควตาฟรี Supabase Free มีฐานข้อมูล 500 MB ต่อโปรเจกต์และ Storage 1 GB Streamlit Community Cloud ใช้ทรัพยากรร่วมและพักแอปเมื่อไม่มีการเข้าชม 12 ชั่วโมง Supabase Free อาจพักเมื่อมีการใช้งานต่ำประมาณหนึ่งสัปดาห์ ตรวจโควตาของผู้ให้บริการ SMTP ที่เลือกแยกต่างหากก่อนตั้งค่า [Supabase Pricing](https://supabase.com/pricing) · [Supabase Project Pausing](https://supabase.com/docs/guides/platform/free-project-pausing) · [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app)
