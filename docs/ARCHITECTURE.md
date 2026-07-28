# معماری NetAI Manager

## لایه‌ها

1. **Presentation** – FastAPI routes + صفحه خوش‌آمدگویی
2. **Application / Services** – AccountManager، AIEngine، EventBus
3. **Platform Adapters** – هر پیام‌رسان یک کلاس مشتق از `BasePlatform`
4. **External libs** – SoroPy، Telethon، Balethon، Google API، ...

## قرارداد BasePlatform

هر adapter باید این متدها را پیاده کند:

- `connect(**credentials) -> bool`
- `disconnect()`
- `get_me() -> dict`
- `get_chats(limit) -> list[ChatInfo]`
- `get_messages(chat_id, limit) -> list[MessageInfo]`
- `send_message(chat_id, text, reply_to=None) -> MessageInfo`
- اختیاری: `send_media(...)`

رویداد پیام جدید با `on_message(handler)` ثبت می‌شود و adapter مسئول فراخوانی `_dispatch_message` است.

## یکپارچه‌سازی SoroPy

فایل `app/platforms/soroush.py` به‌صورت مستقیم از پکیج `soropy` استفاده می‌کند.

```bash
pip install "soropy[ws]>=1.3.6"
```

برای لاگین، `phone` و در صورت نیاز `code_callback` را از API بفرستید.

## امنیت

- session و credential فقط روی دیسک محلی و خارج از گیت
- `.env` برای کلیدها
- هیچ endpointی نباید session خام را برگرداند

## توسعه پلتفرم جدید

1. کلاس جدید در `app/platforms/`
2. ارث‌بری از `BasePlatform`
3. ثبت در `PLATFORM_MAP` داخل `accounts.py`
4. افزودن به `PlatformType`
