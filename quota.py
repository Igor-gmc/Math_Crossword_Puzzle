# quota.py — клиент квот платформы
import httpx

QUOTA_URL = "http://steforge-cabinet-api:8000/api/v1/internal/quota/consume"
QUOTA_CHECK_URL = "http://steforge-cabinet-api:8000/api/v1/internal/quota/check"


def consume_quota(request, app_slug, action="default"):
    """
    Списать одну единицу квоты. Вызывать перед выполнением ценного действия.
    Возвращает (allowed, data).
    """
    resp = httpx.post(QUOTA_URL, json={
        "app_slug": app_slug,
        "action": action,
    }, cookies={
        "access_token": request.cookies.get("access_token", ""),
    }, headers={
        "X-Real-IP": request.headers.get("X-Real-IP", request.remote_addr),
    }, timeout=3.0)
    data = resp.json()
    return data["allowed"], data


def check_quota(request, app_slug, action="default"):
    """
    Проверить квоту без списания. Для отображения 'Осталось: N'.
    """
    resp = httpx.post(QUOTA_CHECK_URL, json={
        "app_slug": app_slug,
        "action": action,
    }, cookies={
        "access_token": request.cookies.get("access_token", ""),
    }, headers={
        "X-Real-IP": request.headers.get("X-Real-IP", request.remote_addr),
    }, timeout=3.0)
    data = resp.json()
    return data
