"""Утилиты сервиса."""

import os

import tomlkit


class ProjectInfo:
    """Класс для получения информации о проекте из pyproject.toml."""

    def __init__(self, main_path: str):
        self.main_path = main_path

    def get_project_name(self) -> str:
        """Получить имя сервиса из pyproject.toml."""
        with open(
            os.path.join(self.main_path, "pyproject.toml"),
            encoding="utf-8",
        ) as toml_file:
            data = tomlkit.parse(toml_file.read())
        return data["project"]["name"]  # type: ignore[return-value,index]

    def get_project_version(self) -> str:
        """Получить версию сервиса из pyproject.toml."""
        with open(
            os.path.join(self.main_path, "pyproject.toml"),
            encoding="utf-8",
        ) as toml_file:
            data = tomlkit.parse(toml_file.read())
        return data["project"]["version"]  # type: ignore[return-value,index]

    def get_project_description(self) -> str:
        """Получить описание сервиса из pyproject.toml."""
        with open(
            os.path.join(self.main_path, "pyproject.toml"),
            encoding="utf-8",
        ) as toml_file:
            data = tomlkit.parse(toml_file.read())
        return data["project"]["description"]  # type: ignore[return-value,index]
