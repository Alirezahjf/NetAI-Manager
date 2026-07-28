# NetAI Manager

**سیستم حرفه‌ای مدیریت یکپارچه شبکه‌های مجازی با هوش مصنوعی**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

NetAI Manager یک پلتفرم مرکزی است که حساب‌های شما را در چندین پیام‌رسان و سرویس به هم متصل می‌کند و با لایه هوش مصنوعی، مدیریت چت‌ها، پاسخ‌گویی، زمان‌بندی و تحلیل را انجام می‌دهد.

> [!IMPORTANT]
> این پروژه فقط برای حساب‌هایی طراحی شده که **مالک آن‌ها هستید** یا **مجوز صریح** دارید. استفاده غیرمجاز از حساب دیگران، نقض قوانین پلتفرم‌ها و قوانین کشور است. همیشه شرایط استفاده (ToS) هر سرویس را رعایت کنید.

---

## پلتفرم‌های پشتیبانی‌شده (نسخه فعلی)

| پلتفرم | وضعیت | روش اتصال | یادداشت |
|--------|--------|-----------|----------|
| **Telegram** | آماده اسکلت | Telethon / Pyrogram | MTProto رسمی |
| **بله (Bale)** | آماده اسکلت | Balethon / API بله | از پروژه ozv_grams الهام گرفته |
| **روبیکا (Rubika)** | آماده اسکلت | Adapter اختصاصی | نیاز به پیاده‌سازی کامل |
| **روبینو (Rubino)** | آماده اسکلت | Adapter اختصاصی | سرویس مرتبط با روبیکا |
| **سروش پلاس (Soroush)** | یکپارچه‌سازی قوی | **SoroPy** (پروژه خودتان) | Selenium + WebSocket/MTProto |
| **ایمیل (Email)** | آماده اسکلت | IMAP / SMTP / Gmail API | |
| **یوتیوب (YouTube)** | آماده اسکلت | YouTube Data API v3 | نظرات، کامنت، آنالیتیکس |

---

## معماری کلی

```text
┌─────────────────────────────────────────────────────────────┐
│                     Web Dashboard / API                      │
│                      (FastAPI + UI)                          │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                    Core Services Layer                       │
│  AccountManager  │  EventBus  │  AI Engine  │  Scheduler     │
└────────────────────────────┬────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Telegram    │    │    Bale      │    │   Soroush    │
│  Adapter     │    │   Adapter    │    │  (SoroPy)    │
└──────────────┘    └──────────────┘    └──────────────┘
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Rubika     │    │   Rubino     │    │  Email/YT    │
│  Adapter     │    │  Adapter     │    │  Adapters    │
└──────────────┘    └──────────────┘    └──────────────┘
```

همه پلتفرم‌ها از یک **رابط مشترک** (`BasePlatform`) پیروی می‌کنند تا API یکسان داشته باشید:

- `login` / `logout`
- `get_chats` / `get_messages`
- `send_message` / `reply` / `send_media`
- `on_new_message` (رویدادهای realtime)
- `get_me` / وضعیت اتصال

---

## ویژگی‌های کلیدی

- **مدیریت چندحسابی** برای هر پلتفرم
- **لایه هوش مصنوعی** با پشتیبانی از:
  - Ollama (محلی و بدون API key)
  - OpenAI و سازگارها (OpenAI-compatible)
  - Gemini / Claude (قابل گسترش)
- **پاسخ خودکار هوشمند** بر اساس قوانین + AI
- **رویداد مرکزی (EventBus)** برای هماهنگی بین پلتفرم‌ها
- **API کامل REST + WebSocket** برای داشبورد وب
- **امنیت**: sessionها محلی، `.env` برای کلیدها، بدون commit کردن credential
- **یکپارچه‌سازی مستقیم با پروژه‌های شما**:
  - [SoroPy](https://github.com/Alirezahjf/soropy) برای سروش پلاس
  - [ozv_grams](https://github.com/Alirezahjf/ozv_grams) برای الگوهای عضوگیری و بله

---

## نصب سریع

```bash
git clone https://github.com/Alirezahjf/NetAI-Manager.git
cd NetAI-Manager

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt

# نصب SoroPy با پشتیبانی WebSocket (برای سروش)
pip install "soropy[ws]>=1.3.6"

cp .env.example .env
# سپس فایل .env را ویرایش کنید
```

اجرای سرور:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

سپس بروید به: `http://localhost:8000` و مستندات API: `http://localhost:8000/docs`

---

## ساختار پروژه

```text
NetAI-Manager/
├── app/
│   ├── main.py                 # نقطه ورود FastAPI
│   ├── config.py               # تنظیمات از .env
│   ├── api/
│   │   └── routes/             # مسیرهای REST
│   ├── core/
│   │   ├── account_manager.py  # مدیریت حساب‌ها
│   │   ├── ai_engine.py        # موتور هوش مصنوعی
│   │   └── event_bus.py        # رویداد مرکزی
│   ├── platforms/
│   │   ├── base.py             # رابط مشترک
│   │   ├── telegram.py
│   │   ├── bale.py
│   │   ├── rubika.py
│   │   ├── rubino.py
│   │   ├── soroush.py          # مبتنی بر SoroPy
│   │   ├── email_platform.py
│   │   └── youtube.py
│   ├── models/                 # مدل‌های داده
│   └── services/               # سرویس‌های کسب‌وکار
├── static/                     # فایل‌های استاتیک داشبورد
├── templates/                  # قالب‌های وب (در صورت نیاز)
├── docs/                       # مستندات بیشتر
├── .env.example
├── requirements.txt
└── README.md
```

---

## تنظیمات محیطی (`.env`)

نمونه‌ها در `.env.example` آمده‌اند. مهم‌ترین‌ها:

```env
# عمومی
APP_NAME=NetAI-Manager
SECRET_KEY=change-me-to-a-long-random-string
DEBUG=true

# AI
AI_PROVIDER=ollama          # ollama | openai | openai-compatible
AI_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
OPENAI_API_KEY=
OPENAI_BASE_URL=

# Telegram
TELEGRAM_API_ID=
TELEGRAM_API_HASH=

# YouTube
YOUTUBE_API_KEY=

# Email
SMTP_HOST=
SMTP_PORT=587
IMAP_HOST=
EMAIL_USER=
EMAIL_PASSWORD=
```

---

## نقشه راه (Roadmap)

### فاز ۱ (فعلی – اسکلت حرفه‌ای)
- [x] معماری ماژولار و رابط BasePlatform
- [x] FastAPI + مستندات خودکار
- [x] AccountManager و EventBus
- [x] AI Engine پایه (Ollama / OpenAI-compatible)
- [x] Adapter سروش مبتنی بر SoroPy
- [x] اسکلت بقیه پلتفرم‌ها

### فاز ۲
- [ ] تکمیل کامل Telegram با Telethon
- [ ] تکمیل Bale با Balethon
- [ ] داشبورد وب واقعی (چت‌ها، ارسال، وضعیت حساب‌ها)
- [ ] پاسخ خودکار AI با فیلتر PV/گروه
- [ ] زمان‌بندی ارسال و کمپین امن

### فاز ۳
- [ ] Rubika / Rubino کامل
- [ ] آنالیتیکس و گزارش‌گیری
- [ ] WebSocket realtime برای داشبورد
- [ ] پشتیبانی چندکاربره با احراز هویت

---

## هشدارهای امنیتی و قانونی

1. **هرگز** شماره، session، API key یا فایل `.session` را در گیت commit نکنید.
2. از حساب‌های آزمایشی برای تست استفاده کنید.
3. ارسال انبوه بدون رضایت، اسپم محسوب می‌شود و منجر به مسدودی حساب می‌شود.
4. برای سروش از backend رسمی/مجاز و قوانین SoroPy پیروی کنید.
5. این ابزار برای اتوماسیون **حساب‌های خودتان** است، نه دسترسی غیرمجاز به حساب دیگران.

---

## وابستگی به پروژه‌های شما

- **SoroPy**: هسته اصلی اتصال به سروش پلاس  
  `pip install "soropy[ws]>=1.3.6"`  
  ریپو: https://github.com/Alirezahjf/soropy

- **ozv_grams**: الگوها و تجربه کار با بله و عضوگیری هوشمند  
  ریپو: https://github.com/Alirezahjf/ozv_grams

---

## مشارکت و توسعه

این نسخه اولیه یک **پایه حرفه‌ای و قابل گسترش** است.  
برای ادامه توسعه هر پلتفرم، کافی است Adapter مربوطه را کامل کنید و تست‌های واقعی با حساب آزمایشی بنویسید.

---

**ساخته‌شده برای مدیریت هوشمند و یکپارچه شبکه‌های مجازی — نسخه ۰.۱.۰**
