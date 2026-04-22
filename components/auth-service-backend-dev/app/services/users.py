from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user_model import User
from app.models.role_model import Role
from app.models.permission_model import Permission
from app.models.associations import role_permissions



async def get_user_roles_and_permissions(db: AsyncSession, user_id: int):
    """
    Получает роли и разрешения для пользователя по его ID.

    Args:
        db: Сессия SQLAlchemy
        user_id: Идентификатор пользователя

    Returns:
        Словарь с информацией о пользователе, его роли и разрешениях.
        Возвращает словарь с ключом 'role' и значением None, если у пользователя нет роли.
    """
    query = (
        select(
            User.id, User.username,
            Role.id.label('role_id'),
            Role.name.label('role_name'),
            Permission.id.label('permission_id'),
            Permission.name.label('permission_name'),
            role_permissions.c.can_view,
            role_permissions.c.can_edit
        )
        .outerjoin(Role, User.role_id == Role.id)
        .outerjoin(role_permissions, Role.id == role_permissions.c.role_id)
        .outerjoin(Permission, role_permissions.c.permission_id == Permission.id)
        .where(User.id == user_id)
    )

    try:
        result_proxy = await db.execute(query)
        result_rows = result_proxy.fetchall()
    except Exception as e:
        raise

    if not result_rows:
        # Пользователь с таким ID не найден
        return None

    # Обработка результата
    user_data = {
        'id': result_rows[0].id,
        'username': result_rows[0].username,
        'role': None
    }


    if result_rows[0].role_id is not None:
        user_data['role'] = {
            'id': result_rows[0].role_id,
            'name': result_rows[0].role_name,
            'permissions': []
        }

        for row in result_rows:
            if row.role_id is not None and row.permission_id is not None:
                permission_info = {
                    'id': row.permission_id,
                    'name': row.permission_name,
                    'can_view': row.can_view,
                    'can_edit': row.can_edit
                }
                # Убедимся, что 'role' уже инициализирован как словарь
                if user_data['role'] is not None:
                    user_data['role']['permissions'].append(permission_info)

    return user_data
