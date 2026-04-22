"""Слушатели для SQLAlchemy Exception."""

from asyncpg import (
    CheckViolationError,
    ForeignKeyViolationError,
    NotNullViolationError,
    UniqueViolationError,
)
from fastapi import FastAPI, Request
from fastapi.responses import UJSONResponse
from loguru import logger
from sqlalchemy.exc import IntegrityError

from src.core.dto.scheme.response.error import ErrorResponse
from src.core.dto.type.logger import LogSeverity


def init_ujson_for_sqlalchemy_exception(
    app_: FastAPI,
    loguru_logger: bool = False,
) -> None:
    """Инициализация слушателя для SQLAlchemy Exceptions."""

    def resolve_sqlalchemy_exception(
        request: Request,
        exc: IntegrityError,
    ) -> tuple[int, str, str]:
        status_code = 500
        detail = "An error occurred when performing a database request."
        severity = LogSeverity.error

        try:
            cause = getattr(exc.orig, "__cause__", None)

            # 1) UNIQUE VIOLATION
            if isinstance(cause, UniqueViolationError):
                status_code = 409
                severity = LogSeverity.info

                # Postgres detail: "Key (field)=(value) already exists."
                raw = getattr(cause, "detail", None)
                constraint = getattr(cause, "constraint_name", None)
                if raw:
                    detail = raw
                elif constraint:
                    detail = f"Unique constraint violated: {constraint}."
                else:
                    detail = "Duplicate key value violates unique constraint."

            # 2) FOREIGN KEY VIOLATION
            elif isinstance(cause, ForeignKeyViolationError):
                status_code = 404
                severity = LogSeverity.info

                # raw detail: "Key (child_id)=(123) is not present in table \"parent\"."
                fk_detail = getattr(cause, "detail", None)
                if fk_detail:
                    detail = fk_detail
                else:
                    table = getattr(cause, "table_name", "<related table>")
                    column = getattr(cause, "column_name", "<foreign key>")
                    detail = f"Related record not found: {table}.{column}"

            # 3) NOT NULL VIOLATION
            elif isinstance(cause, NotNullViolationError):
                status_code = 400
                severity = LogSeverity.info

                # detail: "null value in column \"name\" violates not-null constraint"
                col = getattr(cause, "column_name", None)
                if col:
                    detail = f"Missing required value for column '{col}'."
                else:
                    detail = "A NOT NULL constraint failed."

            # 4) CHECK VIOLATION
            elif isinstance(cause, CheckViolationError):
                status_code = 400
                severity = LogSeverity.info

                # detail includes check expression or constraint name
                raw = getattr(cause, "detail", None)
                constraint = getattr(cause, "constraint_name", None)
                if raw:
                    detail = raw
                elif constraint:
                    detail = f"Check constraint failed: {constraint}."
                else:
                    detail = "A check constraint failed."

            # 5) OTHER INTEGRITY ERROR
            else:
                # Попробуем достать текст из DETAIL: … в исходном сообщении
                msg = exc._message()
                if "DETAIL:" in msg:
                    detail = msg.split("DETAIL:")[1].strip()
                else:
                    # Если есть код SQLSTATE — можно включить его
                    pgcode = getattr(cause, "sqlstate", None) or getattr(
                        cause,
                        "pgcode",
                        None,
                    )
                    if pgcode:
                        detail = f"Database integrity error (SQLSTATE {pgcode})."
                    else:
                        detail = msg

        except Exception as internal_exc:
            # если что-то пошло не так при разборе — логируем, но возвращаем общее сообщение
            logger.exception(internal_exc)
            status_code = 500
            severity = LogSeverity.error
            detail = "Internal error while parsing database exception."

        # Заменяем кавычки, чтобы JSON не портилась
        return status_code, detail.replace('"', "'"), severity

    @app_.exception_handler(IntegrityError)
    async def exception_handler(request: Request, exc: IntegrityError) -> UJSONResponse:
        status_code, detail, severity = resolve_sqlalchemy_exception(
            request=request,
            exc=exc,
        )
        if loguru_logger:
            ctx = getattr(request.state, "log_context", {})
            logger_with_ctx = logger.bind(**ctx)
            if status_code >= 500:
                logger_with_ctx.exception(exc)
            else:
                logger_with_ctx.log(severity, detail)
        return UJSONResponse(
            status_code=status_code,
            content=ErrorResponse(error_code=status_code, detail=detail).model_dump(),
        )
