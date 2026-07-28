# راهنمای شروع NetAI Manager

## ۱. کلون و نصب

```bash
git clone https://github.com/Alirezahjf/NetAI-Manager.git
cd NetAI-Manager
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install "soropy[ws]>=1.3.6"
cp .env.example .env
```

## ۲. تنظیم `.env`

حداقل موارد:

- `SECRET_KEY`
- برای تلگرام: `TELEGRAM_API_ID` و `TELEGRAM_API_HASH` (از my.telegram.org)
- برای AI محلی: Ollama را اجرا کنید (`ollama serve`) و مدل را بکشید (`ollama pull llama3.2`)

## ۳. اجرای سرور

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- داشبورد ساده: http://localhost:8000
- Swagger: http://localhost:8000/docs

## ۴. اتصال حساب (مثال سروش)

```http
POST /api/accounts/connect
Content-Type: application/json

{
  "platform": "soroush",
  "account_id": "09123456789",
  "credentials": {
    "phone": "09123456789",
    "backend": "websocket"
  }
}
```

در حالت تعاملی ترمینال، کد پیامک را وارد کنید. برای production یک `code_callback` یا endpoint جدا برای دریافت کد پیاده کنید.

## ۵. لیست چت‌ها

```http
GET /api/chats/soroush/09123456789?limit=20
```

## ۶. ارسال پیام

```http
POST /api/messages/send
Content-Type: application/json

{
  "platform": "soroush",
  "account_id": "09123456789",
  "chat_id": "@username_or_name",
  "text": "سلام از NetAI Manager"
}
```

## ۷. پاسخ هوشمند با AI

```http
POST /api/ai/reply
Content-Type: application/json

{
  "message_text": "سلام، ساعت کاری‌تون چنده؟",
  "platform": "telegram",
  "extra_instructions": "مودب و کوتاه جواب بده"
}
```

## نکات

- فقط روی حساب‌های خودتان کار کنید.
- sessionها را commit نکنید.
- برای روبیکا/روبینو فعلاً اسکلت آماده است؛ پیاده‌سازی کامل نیاز به روش مجاز دارد.
