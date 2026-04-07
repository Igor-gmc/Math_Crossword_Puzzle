# Математический кроссворд

Веб-приложение для генерации математических кроссвордов. Уравнения вида `A ± B = C` размещаются в сетке по принципу классического кроссворда — пересекаясь общими цифрами. Готовый кроссворд можно распечатать или скачать как PDF.

## Возможности

- Генерация сетки из 10–50 уравнений с операциями `+`, `-`, `×`
- Настройка диапазона чисел (от 1 до 100)
- Управление сложностью: процент скрытых клеток (10–80%)
- Просмотр ответов прямо в браузере
- Экспорт в PDF (формат A4)
- Печать из браузера
- Система квот: ограничение количества генераций (5 для анонимных, 50 для зарегистрированных)
- Кулдаун 3 секунды между генерациями

## Скриншот

![Математический кроссворд](docs/screenshot.png)

## Быстрый старт

```bash
# Через Docker
docker compose up -d

# Или локально
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Приложение будет доступно по адресу: **http://localhost:5000**

## Структура проекта

```
Math_Crossword_Puzzle/
├── app.py                    # Flask-приложение, HTTP-маршруты
├── crossword.py              # Алгоритм генерации кроссворда
├── quota.py                  # Клиент квот платформы
├── requirements.txt          # Зависимости Python
├── Dockerfile
├── docker-compose.yml        # Локальная разработка
├── docker-compose.prod.yml   # Деплой на VPS (steforge.com)
├── templates/
│   └── index.html            # HTML-разметка
└── static/
    ├── style.css             # Стили
    ├── app.js                # Клиентская логика
    └── vendor/               # Локальные копии библиотек
        ├── dom-to-image-more.min.js
        └── jspdf.umd.min.js
```

## API

### `GET /health`

Проверка состояния приложения. Используется Traefik и Docker healthcheck.

```json
{"status": "ok"}
```

### `POST /generate`

Генерирует кроссворд. Принимает JSON:

| Поле            | Тип      | Диапазон  | По умолчанию | Описание                          |
|-----------------|----------|-----------|--------------|-----------------------------------|
| `count`         | int      | 5–50      | 15           | Целевое количество уравнений      |
| `num_range`     | int      | 1–100     | 20           | Максимальное значение чисел в уравнении |
| `operations`    | string[] | +, -, *   | ["+", "-"]   | Разрешённые операции              |
| `fill_percent`  | int      | 10–80     | 50           | Процент видимых цифровых клеток   |

Пример запроса:

```json
{
  "count": 20,
  "num_range": 30,
  "operations": ["+", "-", "*"],
  "fill_percent": 60
}
```

Пример ответа (успех):

```json
{
  "cells": [
    { "row": 0, "col": 0, "value": "5", "is_number": true, "is_hidden": false }
  ],
  "equations": [
    { "equation": "5 + 3 = 8", "row": 0, "col": 0, "direction": "H" }
  ],
  "bounds": { "rows": 14, "cols": 19 },
  "total_equations": 20,
  "remaining": 42
}
```

Пример ответа (лимит исчерпан, HTTP 429):

```json
{
  "error": "limit_exceeded",
  "remaining": 0,
  "limit": 50,
  "is_authenticated": true,
  "resets_in": 52340
}
```

## Квоты

На платформе `sys.steforge.com` действует система квот:

| Тип пользователя     | Лимит | Сброс                          |
|----------------------|-------|--------------------------------|
| Анонимный            | 5     | Через 24 ч после первого действия |
| Зарегистрированный   | 50    | Через 24 ч после первого действия |

Локально (без платформы) квоты не применяются — запросы к quota API оборачиваются в `try/except` и пропускаются при недоступности.

## Алгоритм

1. Генерируется пул уравнений для заданных операций и диапазона чисел.
2. Первое уравнение размещается горизонтально в начале координат.
3. Каждое следующее уравнение ищет пересечения с уже размещёнными по совпадающим числам.
4. Проверяются ограничения: сетка вписывается в лист A4 (21×28 клеток), уравнения не сливаются и не перекрываются.
5. После размещения алгоритм скрывает часть цифровых клеток согласно `fill_percent`, гарантируя, что в каждом уравнении есть хотя бы одна скрытая и одна видимая цифра.

## Технологии

| Компонент  | Стек                                     |
|------------|------------------------------------------|
| Backend    | Python 3.12, Flask 3.1.0, Gunicorn, httpx |
| Frontend   | Vanilla JS, HTML/CSS                      |
| PDF        | jsPDF 2.5.1, dom-to-image-more 3.4.0     |
| Deploy     | Docker, docker-compose                    |
| Платформа  | sys.steforge.com (Traefik, ForwardAuth, квоты) |

## Деплой

### Локальная разработка

```bash
# Через Docker
docker compose up -d

# Или напрямую Python
python app.py
```

Приложение будет доступно по адресу: **http://localhost:5000**

### Продакшен (VPS sys.steforge.com)

Приложение разворачивается на платформе через `docker-compose.prod.yml` с интеграцией:
- **Traefik** — HTTPS, Let's Encrypt, маршрутизация по субдомену `math-crossword.sys.steforge.com`
- **ForwardAuth** — авторизация через Keycloak / platform-api
- **Healthcheck** — `GET /health` для мониторинга и маршрутизации
- **Gunicorn** — WSGI-сервер (2 воркера)

Переменные окружения для продакшена:

| Переменная | Описание |
|------------|----------|
| `APP_ENV` | `production` |
| `PLATFORM_API_URL` | `http://platform-api:8000` |
| `SERVICE_TOKEN` | Shared secret для platform-api |
| `APP_SLUG` | `math-crossword` |
| `CALLER_MVP` | `math-crossword` |

```bash
# Запустить на VPS
docker compose -f docker-compose.prod.yml up -d --build

# Логи
docker logs Math_Crossword_Puzzle -f
```
