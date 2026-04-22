from typing import Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import select, func

from app.schemas.staff_schema import StaffUpdate, StaffUserBase
from app.models.user_model import User
from app.models.staff_model import Staff

async def get_staff_list(
        db: AsyncSession,
        page: Optional[int] = 1,
        size: Optional[int] = 20
) -> dict:
    base_query = select(Staff) \
                 .options(selectinload(Staff.user).selectinload(User.role))

    if page is None and size is None:
        result = await db.execute(base_query)
        staff_objects = result.scalars().all()

        items = []
        for staff_obj in staff_objects:
            user_obj = staff_obj.user
            decrypted_password = user_obj.decrypt_password() if user_obj else None

            item_dict = {
                'staff_id': staff_obj.id,
                'name': staff_obj.name,
                'surname': staff_obj.surname,
                'patronymic': staff_obj.patronymic,
                'birth_date': staff_obj.birth_date,
                'phone': staff_obj.phone,
                'email': staff_obj.email,
                'username': user_obj.username if user_obj else None,
                'password': decrypted_password,
                'position': staff_obj.position,
                'department': staff_obj.department,
                'personnel_number': staff_obj.personnel_number,
                'user_id': staff_obj.user_id,
                'role_id': user_obj.role.id if user_obj and user_obj.role else None,
                'role_name': user_obj.role.name if user_obj and user_obj.role else None,
                'is_active': user_obj.is_active,
            }
            items.append(item_dict)

        items_count = len(items)

        return {
            "total": items_count,
            "page": 1,
            "size": items_count if items_count > 0 else 1,
            "items": items
        }

    # Пагинация включена
    if page is None:
        page = 1
    if size is None:
        size = 20

    count_query = select(func.count(Staff.id))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * size
    paginated_query = base_query.offset(offset).limit(size)

    result = await db.execute(paginated_query)
    staff_objects = result.scalars().all()

    items = []
    for staff_obj in staff_objects:
        user_obj = staff_obj.user # Получаем связанный объект User
        decrypted_password = user_obj.decrypt_password() if user_obj else None

        item_dict = {
            "staff_id": staff_obj.id,
            "name": staff_obj.name,
            "surname": staff_obj.surname,
            "patronymic": staff_obj.patronymic,
            "birth_date": staff_obj.birth_date,
            "phone": staff_obj.phone,
            "email": staff_obj.email,
            "username": user_obj.username if user_obj else None,
            "password": decrypted_password,
            "position": staff_obj.position,
            "department": staff_obj.department,
            "personnel_number": staff_obj.personnel_number,
            "user_id": staff_obj.user_id,
            "role_id": user_obj.role.id if user_obj and user_obj.role else None,
            "role_name": user_obj.role.name if user_obj and user_obj.role else None,
            "is_active": user_obj.is_active,
        }
        items.append(item_dict)

    return {
        "total": total,
        "page": page,
        "size": size,
        "items": items
    }


async def create_staff_row(db: AsyncSession, staff: StaffUserBase) -> int:
    try:
        result = await db.execute(select(User).filter(User.username == staff.username))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(status_code=400, detail=f"User with username {staff.username} already exists")

        new_user = User(username=staff.username, role_id=staff.role_id, is_active=staff.is_active)
        new_user.set_password(staff.password)

        db.add(new_user)
        await db.flush()

        new_staff = Staff(
            name=staff.name,
            surname=staff.surname,
            patronymic=staff.patronymic,
            birth_date=staff.birth_date,
            phone=staff.phone,
            email=staff.email,
            position=staff.position,
            department=staff.department,
            personnel_number=staff.personnel_number,
            user_id=new_user.id
        )

        db.add(new_staff)
        await db.commit()
        await db.refresh(new_staff)
        return new_staff.id

    except IntegrityError as e:
        await db.rollback()
        # Проверяем, какое именно ограничение было нарушено
        if "staff_phone_key" in str(e.orig):
            raise HTTPException(status_code=400, detail=f"Staff member with phone {staff.phone} already exists")
        elif "staff_personnel_number_key" in str(e.orig):
            raise HTTPException(status_code=400,
                                detail=f"Staff member with personnel number {staff.personnel_number} already exists")
        else:
            raise HTTPException(status_code=400, detail="An integrity constraint was violated")

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred while creating staff: {str(e)}")


async def update_staff_by_id(db: AsyncSession, staff: StaffUpdate, staff_id: int) -> None:
    staff_dict = staff.model_dump(exclude_unset=True)
    if not staff_dict:
        raise HTTPException(status_code=400,
                            detail=f"No fields provided for update. At least one field must be specified.")

    # Явно загружаем связанный объект User
    result = await db.execute(
        select(Staff)
        .filter(Staff.id == staff_id)
        .options(selectinload(Staff.user))
    )
    existing_staff = result.scalar_one_or_none()

    if not existing_staff:
        raise HTTPException(
            status_code=404,
            detail=f"Staff with id {staff_id} not found."
        )

    staff_fields = {
        "name", "surname", "patronymic", "birth_date", "phone",
        "email", "position", "department", "personnel_number"
    }

    for field in staff_fields:
        if field in staff_dict:
            setattr(existing_staff, field, staff_dict[field])

    user_fields = {"username", "role_id", "is_active"}

    if existing_staff.user:
        if "username" in staff_dict:
            result = await db.execute(
                select(User)
                .filter(User.username == staff_dict["username"])
                .filter(User.id != existing_staff.user.id)
            )
            existing_user_with_username = result.scalar_one_or_none()

            if existing_user_with_username:
                raise HTTPException(
                    status_code=400,
                    detail=f"Username '{staff_dict['username']}' is already taken by another user."
                )

        for field in user_fields:
            if field in staff_dict:
                setattr(existing_staff.user, field, staff_dict[field])


        if "password" in staff_dict:
            existing_staff.user.set_password(staff_dict["password"])


    await db.commit()
    await db.refresh(existing_staff)
    return


async def get_staff_row_by_id(db: AsyncSession, staff_id: int):

    stmt = select(Staff) \
           .options(selectinload(Staff.user).selectinload(User.role)) \
           .where(Staff.id == staff_id)

    result = await db.execute(stmt)
    staff_obj = result.scalar_one_or_none()

    if not staff_obj:
        raise HTTPException(
            status_code=404,
            detail=f"Staff with id {staff_id} not found."
        )

    # Получаем связанный объект User
    user_obj = staff_obj.user
    decrypted_password = user_obj.decrypt_password() if user_obj else None

    return {
        "staff_id": staff_obj.id,
        "name": staff_obj.name,
        "surname": staff_obj.surname,
        "patronymic": staff_obj.patronymic,
        "birth_date": staff_obj.birth_date,
        "phone": staff_obj.phone,
        "email": staff_obj.email,
        "username": user_obj.username if user_obj else None,
        "password": decrypted_password,
        "position": staff_obj.position,
        "department": staff_obj.department,
        "personnel_number": staff_obj.personnel_number,
        "user_id": staff_obj.user_id,
        "role_id": user_obj.role.id if user_obj and user_obj.role else None,
        "role_name": user_obj.role.name if user_obj and user_obj.role else None,
        "is_active": user_obj.is_active,
    }



async def delete_staff_by_id(db: AsyncSession, staff_id: int) -> None:
    result = await db.execute(
        select(Staff)
        .options(joinedload(Staff.user))
        .filter(Staff.id == staff_id)
    )
    existing_staff = result.scalar_one_or_none()

    if not existing_staff:
        raise HTTPException(
            status_code=404,
            detail=f"Staff with id {staff_id} not found."
        )

    if existing_staff.user:
        await db.delete(existing_staff.user)

    await db.delete(existing_staff)
    await db.commit()
    return


async def get_positions_staff(db: AsyncSession):
    result = await db.execute(
        select(Staff.position).distinct().where(Staff.position.is_not(None))
    )
    result = result.fetchall()
    return [row.position for row in result if row.position is not None]


async def get_department_staff(db: AsyncSession):
    result = await db.execute(
        select(Staff.department).distinct().where(Staff.department.is_not(None))
    )
    result = result.fetchall()
    return [row.department for row in result if row.department is not None]
