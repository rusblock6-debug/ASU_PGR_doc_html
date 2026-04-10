from fastapi import HTTPException

from app.schemas.settings import VariableCreateRequest
from app.utils.initial_reading_secrets import get_vars_from_template



async def create_secrets_for_vehicle_id_service(vehicle_id: int, request: VariableCreateRequest):
    try:
        # Получаем переменные из запроса
        variables = request.variables

        # Валидация vehicle_id
        if vehicle_id <= 0:
            raise HTTPException(status_code=400, detail="Vehicle ID должен быть положительным числом")

        # Валидация переменных
        if not variables:
            raise HTTPException(status_code=400, detail="Список переменных не может быть пустым")

        defined_vars, empty_vars = get_vars_from_template()

        # Проверяем, все ли нужные переменные (пустые в файле) указаны
        empty_vars_set = set(empty_vars) if isinstance(empty_vars, list) else {empty_vars}
        provided_vars_set = set(variables.keys())

        # Находим недостающие переменные
        missing_vars = empty_vars_set - provided_vars_set

        if missing_vars:
            raise HTTPException(
                status_code=400,
                detail=f"Отсутствуют обязательные переменные: {', '.join(sorted(missing_vars))}. "
                       f"Необходимо указать все переменные, которые отсутствуют в шаблоне."
            )

        # Проверяем, что в запросе не переданы лишние переменные (не из списка пустых)
        extra_vars = provided_vars_set - empty_vars_set
        if extra_vars:
            raise HTTPException(
                status_code=400,
                detail=f"Переменные {', '.join(sorted(extra_vars))} не являются обязательными "
                       f"(не из списка пустых переменных в шаблоне). "
                       f"Допустимые переменные: {', '.join(sorted(empty_vars_set))}"
            )

        # Соединяем указанные переменные из файла с переменными из запроса
        # Переменные из файла (с значениями) + переменные из запроса (для пустых)
        combined_variables = defined_vars.copy()  # Копируем переменные с значениями из файла
        combined_variables.update(variables)  # Обновляем значениями из запроса для пустых переменных

        return combined_variables

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")
