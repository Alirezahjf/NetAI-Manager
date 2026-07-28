# اتصال به اول AI (AvalAI)

NetAI Manager به‌صورت پیش‌فرض از **AvalAI** به‌عنوان درگاه هوش مصنوعی استفاده می‌کند.

## چرا AvalAI؟

- API سازگار با OpenAI
- یک کلید برای صدها مدل (GPT، Claude، Gemini، Grok، DeepSeek و ...)
- مناسب آپدیت‌های بعدی: فقط نام مدل را عوض می‌کنید

مستندات رسمی: https://docs.avalai.ir  
داشبورد کلید: https://avalai.ir

## تنظیم فقط با یک کلید

در فایل `.env`:

```env
AI_PROVIDER=avalai
AI_MODEL=gpt-4o-mini
AVALAI_API_KEY=کلید_شما_از_داشبورد
AVALAI_BASE_URL=https://api.avalai.ir/v1
```

آینه داخل کشور (اختیاری):

```env
AVALAI_BASE_URL=https://api.avalapis.ir/v1
```

## مثال پایتون (همان منطق داخل موتور)

```python
from openai import OpenAI

client = OpenAI(
    api_key="AVALAI_API_KEY",
    base_url="https://api.avalai.ir/v1",
)

r = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "سلام"}],
)
print(r.choices[0].message.content)
```

## API داخل NetAI

- `POST /api/ai/generate` — تولید متن
- `POST /api/ai/reply` — پاسخ هوشمند به پیام
- `GET /api/ai/models` — لیست مدل‌های در دسترس

برای آپدیت بعدی کافی است `AI_MODEL` را به مدل جدید AvalAI تغییر دهید؛ کد تغییر نمی‌کند.
