# پلتفرم‌های ایرانی (از ozv_grams)

## بله (Bale)

- احراز هویت: شماره + کد پیامک (protobuf / HTTP2 مثل ozv_grams)
- سشن: `jwt` + `user_id`
- وابستگی: کتابخانه `balethon` موجود در ریپوی [ozv_grams](https://github.com/Alirezahjf/ozv_grams)

```http
POST /api/accounts/connect
{
  "platform": "bale",
  "account_id": "0912...",
  "credentials": { "phone": "0912..." }
}
```

سپس با کد:

```json
{ "phone": "0912...", "code": "12345", "transaction_hash": "..." }
```

یا سشن ذخیره‌شده:

```json
{ "jwt": "...", "user_id": 123, "name": "..." }
```

## روبیکا (Rubika)

- کتابخانه: **pyrubi**
- سشن: `auth` + `private_key` (+ اطلاعات user)

```json
{ "phone": "0912..." }
```

سپس:

```json
{ "phone": "0912...", "code": "...", "phone_code_hash": "..." }
```

## روبینو (Rubino)

- احراز هویت جدا ندارد
- از **همان auth روبیکا** استفاده می‌کند (rubinobot)

```json
{
  "platform": "rubino",
  "account_id": "my-rubino",
  "credentials": { "auth": "AUTH_FROM_RUBIKA_SESSION" }
}
```

متدهای خاص: follow پروفایل از طریق لایه سرویس/API بعدی.

## وابستگی‌ها

```bash
pip install pyrubi rubinobot protobuf httpx[http2]
# balethon: از ozv_grams کپی یا PYTHONPATH
```

## امنیت

هرگز `jwt` / `auth` / `private_key` را در گیت commit نکنید.
