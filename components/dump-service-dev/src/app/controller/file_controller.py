# ruff: noqa: D100, D101
from src.app.model import File
from src.app.repository import FileRepository
from src.app.type import SyncStatus
from src.core.controller import SQLAlchemyController
from src.core.dto.scheme.response.pagination import PaginationResponse


class FileController(SQLAlchemyController[File]):
    def __init__(
        self,
        file_repository: FileRepository,
        exclude_fields: list[str],
    ):
        super().__init__(
            model=File,
            repository=file_repository,
            exclude_fields=exclude_fields,
        )
        self.file_repository = file_repository

    async def get_unsync_files(self) -> PaginationResponse[File]:
        """Получить файлы, которые нужно засинкать."""
        files = await self.get_by(
            field="sync_status",
            value=SyncStatus.CREATED,
            limit=10,
        )

        return files
