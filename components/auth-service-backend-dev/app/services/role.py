from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from sqlalchemy import select, insert, func, update, delete
from sqlalchemy.orm import selectinload

from app.api.exceptions.role import RoleWithNameExists
from app.models.role_model import Role
from app.models.permission_model import Permission
from app.models.associations import role_permissions
from app.schemas.role_schema import RoleCreate, RoleUpdate


async def create_role_rows(
        db: AsyncSession,
        role_data: RoleCreate
):
    # Проверяем существование роли
    result = await db.execute(select(Role).filter(Role.name == role_data.name))
    existing_role = result.scalar_one_or_none()
    if existing_role:
        raise RoleWithNameExists(existing_role.id, role_data.name)

    # Создаем новую роль
    new_role = Role(
        name=role_data.name,
        description=role_data.description or ""
    )
    db.add(new_role)
    await db.flush()

    # Обрабатываем разрешения
    permissions_list = []

    if role_data.permissions:
        for perm_data in role_data.permissions:
            # Ищем разрешение ПО ИМЕНИ
            permission_result = await db.execute(
                select(Permission).filter(Permission.name == perm_data.name)
            )
            permission = permission_result.scalar_one_or_none()

            # Если разрешение не существует, создаем его
            if not permission:
                permission = Permission(
                    name=perm_data.name,
                )
                db.add(permission)
                await db.flush()

            # Добавляем связь с разрешением
            stmt = insert(role_permissions).values(
                role_id=new_role.id,
                permission_id=permission.id,
                can_view=perm_data.can_view,
                can_edit=perm_data.can_edit,
            )
            await db.execute(stmt)

            # Сохраняем информацию для ответа
            permissions_list.append({
                'name': permission.name,
                'can_view': perm_data.can_view,
                'can_edit': perm_data.can_edit
            })

    await db.commit()

    # Создаем объект для ответа с кастомной структурой
    # Не пытаемся присвоить new_role.permissions, а возвращаем словарь
    result_data = {
        'id': new_role.id,
        'name': new_role.name,
        'description': new_role.description,
        'permissions': permissions_list
    }

    return result_data

async def get_all_roles(
        db: AsyncSession,
        page: Optional[int] = 1,
        size: Optional[int] = 20
) -> dict:
    """Получить все роли с разрешениями и правами доступа с пагинацией"""

    # Сначала получаем все уникальные роли для определения пагинации
    if page is None and size is None:
        # Без пагинации - загружаем все данные
        result = await db.execute(
            select(Role.id, Role.name, Role.description)
            .order_by(Role.id)
        )
        roles_basic = result.all()

        # Теперь для каждой роли получаем разрешения
        roles = []
        for role_row in roles_basic:
            perms_result = await db.execute(
                select(
                    Permission.name.label('permission_name'),
                    Permission.description.label('permission_description'),
                    role_permissions.c.can_view,
                    role_permissions.c.can_edit
                ).select_from(Role)
                .join(role_permissions, Role.id == role_permissions.c.role_id)
                .join(Permission, role_permissions.c.permission_id == Permission.id)
                .where(Role.id == role_row.id)
            )

            permissions = []
            for perm_row in perms_result:
                permissions.append({
                    'name': perm_row.permission_name,  # Изменили ключ с permission_name на name
                    'description': perm_row.permission_description,
                    # Изменили ключ с permission_description на description
                    'can_view': perm_row.can_view,
                    'can_edit': perm_row.can_edit
                })

            roles.append({
                'id': role_row.id,
                'name': role_row.name,
                'description': role_row.description,
                'permissions': permissions
            })

        items_count = len(roles)

        return {
            "total": items_count,
            "page": 1,
            "size": items_count if items_count > 0 else 1,
            "items": roles
        }

    # Пагинация включена
    if page is None:
        page = 1
    if size is None:
        size = 20

    # Подсчёт общего количества ролей
    count_query = select(func.count(Role.id))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Получаем роли для текущей страницы
    offset = (page - 1) * size
    roles_query = select(Role.id, Role.name, Role.description).order_by(Role.id).offset(offset).limit(size)
    roles_result = await db.execute(roles_query)
    roles_basic = roles_result.all()

    # Теперь для каждой роли на странице получаем разрешения
    roles = []
    for role_row in roles_basic:
        perms_result = await db.execute(
            select(
                Permission.name.label('permission_name'),
                Permission.description.label('permission_description'),
                role_permissions.c.can_view,
                role_permissions.c.can_edit
            ).select_from(Role)
            .join(role_permissions, Role.id == role_permissions.c.role_id, isouter=True)
            .join(Permission, role_permissions.c.permission_id == Permission.id, isouter=True)
            .where(Role.id == role_row.id)
        )

        permissions = []
        for perm_row in perms_result:
            if perm_row.permission_name is not None:  # Только существующие разрешения
                permissions.append({
                    'name': perm_row.permission_name,  # Изменили ключ с permission_name на name
                    'description': perm_row.permission_description,
                    # Изменили ключ с permission_description на description
                    'can_view': perm_row.can_view,
                    'can_edit': perm_row.can_edit
                })

        roles.append({
            'id': role_row.id,
            'name': role_row.name,
            'description': role_row.description,
            'permissions': permissions
        })

    return {
        "total": total,
        "page": page,
        "size": size,
        "items": roles
    }


async def get_role_by_id(
        db: AsyncSession,
        role_id: int
):
    """Получить роль по ID с разрешениями и правами доступа"""

    # Получаем основные данные о роли
    role_result = await db.execute(
        select(Role.id, Role.name, Role.description)
        .where(Role.id == role_id)
    )
    role_row = role_result.first()

    if not role_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # Получаем разрешения для этой роли
    perms_result = await db.execute(
        select(
            Permission.name.label('permission_name'),
            Permission.description.label('permission_description'),
            role_permissions.c.can_view,
            role_permissions.c.can_edit
        ).select_from(Role)
        .join(role_permissions, Role.id == role_permissions.c.role_id, isouter=True)
        .join(Permission, role_permissions.c.permission_id == Permission.id, isouter=True)
        .where(Role.id == role_id)
    )

    permissions = []
    for perm_row in perms_result:
        if perm_row.permission_name is not None:  # Только существующие разрешения
            permissions.append({
                'name': perm_row.permission_name,  # Изменили ключ с permission_name на name
                'description': perm_row.permission_description,  # Изменили ключ с permission_description на description
                'can_view': perm_row.can_view,
                'can_edit': perm_row.can_edit
            })

    # Возвращаем роль в нужном формате (без пагинации)
    return {
        'id': role_row.id,
        'name': role_row.name,
        'description': role_row.description,
        'permissions': permissions
    }


async def update_role_row(
        db: AsyncSession,
        role_id: int,
        role_data: RoleUpdate
):
    # Проверяем, существует ли роль
    role_result = await db.execute(select(Role).where(Role.id == role_id))
    existing_role = role_result.scalar_one_or_none()

    if not existing_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # Проверяем, не существует ли уже роль с таким же именем (если имя изменяется)
    if role_data.name and role_data.name != existing_role.name:
        name_check_result = await db.execute(select(Role).filter(Role.name == role_data.name))
        duplicate_role = name_check_result.scalar_one_or_none()
        if duplicate_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role with this name already exists"
            )

    # Обновляем основные данные роли
    update_data = {}
    if role_data.name is not None:
        update_data['name'] = role_data.name
    if role_data.description is not None:
        update_data['description'] = role_data.description or ""

    if update_data:
        stmt = update(Role).where(Role.id == role_id).values(**update_data)
        await db.execute(stmt)

    # Если переданы разрешения, обновляем связи
    if role_data.permissions is not None:
        # Удаляем старые связи разрешений для этой роли
        await db.execute(delete(role_permissions).where(role_permissions.c.role_id == role_id))

        # Добавляем новые связи разрешений
        if role_data.permissions:
            for perm_data in role_data.permissions:
                # ИЩЕМ разрешение ПО ИМЕНИ, а не по ID
                permission_result = await db.execute(
                    select(Permission).filter(Permission.name == perm_data.name)
                )
                permission = permission_result.scalar_one_or_none()

                # Если разрешение не существует, СОЗДАЕМ его
                if not permission:
                    permission = Permission(
                        name=perm_data.name,
                    )
                    db.add(permission)
                    await db.flush()  # Получаем ID нового разрешения

                # Добавляем связь с разрешением
                stmt = insert(role_permissions).values(
                    role_id=role_id,
                    permission_id=permission.id,
                    can_view=perm_data.can_view,
                    can_edit=perm_data.can_edit,
                )
                await db.execute(stmt)

    await db.commit()

    # Загружаем обновленную роль с разрешениями и дополнительной информацией из промежуточной таблицы
    result = await db.execute(
        select(Role, Permission.name.label('permission_name'),
               Permission.description.label('permission_description'),
               role_permissions.c.can_view,
               role_permissions.c.can_edit)
        .select_from(Role)
        .join(role_permissions, Role.id == role_permissions.c.role_id, isouter=True)
        .join(Permission, role_permissions.c.permission_id == Permission.id, isouter=True)
        .where(Role.id == role_id)
    )

    rows = result.all()

    if not rows or all(row.permission_name is None for row in rows):
        # Если нет связей с разрешениями, возвращаем роль без разрешений
        role_result = await db.execute(
            select(Role)
            .where(Role.id == role_id)
        )
        role = role_result.scalar_one()

        # Возвращаем роль в формате, соответствующем схеме ответа
        return {
            'id': role.id,
            'name': role.name,
            'description': role.description,
            'permissions': []
        }

    # Получаем основную информацию о роли из первой строки
    role = rows[0].Role

    # Добавляем к роли информацию о разрешениях с правами доступа
    permissions = [
        {
            'name': row.permission_name,  # Изменили ключ как в других функциях
            'description': row.permission_description,
            'can_view': row.can_view,
            'can_edit': row.can_edit
        }
        for row in rows if row.permission_name is not None  # Исключаем NULL из outer join
    ]

    # Возвращаем роль в формате, соответствующем схеме ответа
    return {
        'id': role.id,
        'name': role.name,
        'description': role.description,
        'permissions': permissions
    }


async def delete_role_row(
        db: AsyncSession,
        role_id: int
):
    """Удалить роль по ID"""

    role_result = await db.execute(select(Role).where(Role.id == role_id))
    existing_role = role_result.scalar_one_or_none()

    if not existing_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    await db.execute(delete(role_permissions).where(role_permissions.c.role_id == role_id))
    await db.execute(delete(Role).where(Role.id == role_id))
    await db.commit()

    return {"message": f"Role '{existing_role.name}' deleted successfully"}
