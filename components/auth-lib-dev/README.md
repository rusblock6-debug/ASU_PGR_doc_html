# auth_lib

Библиотека FastAPI для проверки JWT-based permissions.

Предоставляет единый источник правды для permissions (enum `Permission`) и удобные FastAPI-зависимости для проверки доступа по JWT-токену.

## Установка

```bash
uv add git+https://github.com/your-org/auth-lib.git
```

## Использование

### Защита эндпоинта с проверкой разрешений

```python
from fastapi import FastAPI, Depends
from auth_lib import Permission, Action, UserPayload, require_permission

app = FastAPI()

@app.get("/work-orders")
async def get_work_orders(
    user: UserPayload | None = Depends(require_permission(Permission.WORK_ORDER, Action.VIEW)),
):
    if user is None:
        # Внутренний запрос (без X-Source: api-gateway)
        return {"message": "Internal request"}
    return {"message": f"Hello, {user.username}"}
```

`require_permission` проверяет:
1. Заголовок `X-Source` -- если отсутствует или не равен `api-gateway`, запрос считается внутренним и возвращается `None` (без проверки токена)
2. Наличие и валидность JWT-токена (иначе 401)
3. Наличие у пользователя указанного разрешения с нужным действием (иначе 403)

### Получение текущего пользователя без проверки разрешений

```python
from fastapi import FastAPI, Depends
from auth_lib import UserPayload, get_current_user

app = FastAPI()

@app.get("/me")
async def get_me(user: UserPayload | None = Depends(get_current_user)):
    if user is None:
        # Внутренний запрос (без X-Source: api-gateway)
        return {"message": "Internal request"}
    return {"id": user.id, "username": user.username, "role": user.role.name}
```

`get_current_user` проверяет заголовок `X-Source` -- если отсутствует или не равен `api-gateway`, возвращает `None` (внутренний запрос). Для запросов через api-gateway проверяет валидность токена, без проверки конкретных разрешений.

### Обработка ошибок

```python
from fastapi import FastAPI, Depends
from auth_lib import Permission, Action, require_permission

app = FastAPI()

# 401 -- токен отсутствует или невалиден
# 403 -- токен валиден, но нет требуемого разрешения
@app.get("/admin")
async def admin_panel(
    user=Depends(require_permission(Permission.ROLES, Action.EDIT)),
):
    return {"admin": True}
```

Библиотека автоматически возвращает:
- **401 Unauthorized** -- если токен отсутствует, просрочен или имеет невалидную структуру
- **403 Forbidden** -- если токен валиден, но у пользователя нет требуемого разрешения (permission + action)

### Внутренние запросы (service-to-service)

Библиотека различает внешние запросы (через API Gateway) и внутренние (между сервисами) по заголовку `X-Source`.

- Если `X-Source: api-gateway` -- запрос считается внешним, выполняется полная проверка JWT и разрешений
- Если заголовок `X-Source` отсутствует или имеет другое значение -- запрос считается внутренним, зависимости возвращают `None` без проверки токена

```python
from fastapi import FastAPI, Depends
from auth_lib import Permission, Action, UserPayload, require_permission

app = FastAPI()

@app.get("/work-orders")
async def get_work_orders(
    user: UserPayload | None = Depends(require_permission(Permission.WORK_ORDER, Action.VIEW)),
):
    if user is None:
        # Внутренний запрос от другого сервиса
        ...
    else:
        # Запрос от пользователя через api-gateway
        print(f"User: {user.username}")
```

## API Reference

| Объект | Тип | Описание |
|--------|-----|----------|
| `Permission` | `StrEnum` | Enum с 14 значениями разрешений (см. таблицу ниже) |
| `Action` | `StrEnum` | Enum действий: `VIEW`, `EDIT` |
| `UserPayload` | Pydantic model | Модель пользователя с полями `id`, `username`, `role` |
| `RoleSchema` | Pydantic model | Модель роли с именем и списком разрешений |
| `PermissionSchema` | Pydantic model | Модель отдельного разрешения с полями `permission`, `can_view`, `can_edit` |
| `require_permission(permission, action)` | Функция | Возвращает FastAPI-зависимость для проверки разрешения. Возвращает `UserPayload \| None` |
| `get_current_user` | FastAPI dependency | Зависимость, возвращающая `UserPayload \| None` из JWT. `None` для внутренних запросов |

Все объекты доступны через:

```python
from auth_lib import Permission, Action, UserPayload, RoleSchema, PermissionSchema, require_permission, get_current_user
```

## Формат JWT payload

Библиотека ожидает JWT-токен в заголовке `Authorization: Bearer <token>` со следующей структурой payload:

```json
{
  "sub": 1,
  "username": "admin",
  "role": {
    "name": "Администратор",
    "permissions": [
      {"permission": "work_order", "can_view": true, "can_edit": false},
      {"permission": "roles", "can_view": true, "can_edit": true}
    ]
  },
  "exp": 1700000000
}
```

- `sub` -- ID пользователя (int)
- `username` -- имя пользователя (str)
- `role.name` -- название роли (str)
- `role.permissions` -- список разрешений, каждое с `permission` (str), `can_view` (bool), `can_edit` (bool)
- `exp` -- время истечения токена (unix timestamp)

Подпись токена **не проверяется** (`verify_signature=False`) -- предполагается, что токен уже проверен API Gateway. Время истечения (`exp`) **проверяется**.

## Таблица Permission

| Enum | JWT Value |
|------|-----------|
| `Permission.WORK_TIME_MAP` | `work-time-map` |
| `Permission.WORK_ORDER` | `work_order` |
| `Permission.TRIP_EDITOR` | `trip_editor` |
| `Permission.PLACES` | `places` |
| `Permission.SECTIONS` | `sections` |
| `Permission.TAGS` | `tags` |
| `Permission.EQUIPMENT` | `equipment` |
| `Permission.HORIZONS` | `horizons` |
| `Permission.DISPATCH_MAP` | `dispatch_map` |
| `Permission.STATUSES` | `statuses` |
| `Permission.CARGO` | `cargo` |
| `Permission.MAP` | `map` |
| `Permission.STAFF` | `staff` |
| `Permission.ROLES` | `roles` |
