import os
import logging
import hvac
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any

from app.utils.initial_reading_secrets import extract_common_variables
from app.config import settings
logger = logging.getLogger(__name__)


class VaultClient:
    TOKEN = settings.VAULT_TOKEN
    BASE_URL = settings.BASE_URL
    TEMPLATE_FILE_PATH = settings.TEMPLATE_FILE_PATH

    @staticmethod
    def init_conn():
        """
        Проверка соединения с vault
        Returns: None
        """

        client = hvac.Client(url=VaultClient.BASE_URL, token=VaultClient.TOKEN)

        if not client.is_authenticated():
            logger.error("Vault authentication failed!")
            raise Exception("Vault authentication failed!")
        return client

    @staticmethod
    def _load_template_sections() -> Dict[str, Any]:
        template_file_path = Path(VaultClient.TEMPLATE_FILE_PATH)
        if not template_file_path.exists():
            raise FileNotFoundError(f"Template file {template_file_path} not found")
        return extract_common_variables(str(template_file_path))

    @staticmethod
    def _render_vehicle_dependant_vars(vehicle_id: int, vars_map: Dict[str, Any]) -> Dict[str, Any]:
        rendered: Dict[str, Any] = {}
        for key, value in (vars_map or {}).items():
            rendered[key] = str(value).replace("{VEHICLE_ID}", str(vehicle_id))
        return rendered

    @staticmethod
    def _merge_with_template(vehicle_id: int, stored_values: Dict[str, Any]) -> Dict[str, Any]:
        sections = VaultClient._load_template_sections()
        common = dict(sections.get("common") or {})
        vehicle_dependant = VaultClient._render_vehicle_dependant_vars(
            vehicle_id,
            sections.get("vehicle_dependant") or {},
        )

        template_owned_keys = set(common.keys()) | set(vehicle_dependant.keys()) | {"VEHICLE_ID"}
        custom_values = {
            key: value
            for key, value in (stored_values or {}).items()
            if key not in template_owned_keys
        }

        merged: Dict[str, Any] = {}
        merged.update(custom_values)
        merged.update(common)
        merged.update(vehicle_dependant)
        merged["VEHICLE_ID"] = str(vehicle_id)
        return merged

    @staticmethod
    def create_new_secrets(vehicle_id: int, new_variables: Dict[str, Any]) -> dict:
        """
        Создает новую конфигурацию для vehicle_id: int
        Объединяет общие переменные из шаблона с новыми переменными
        """
        client = VaultClient.init_conn()
        if not client:
            raise Exception("Vault authentication failed!")
        final_config = VaultClient._merge_with_template(vehicle_id, new_variables.variables)

        try:
            client.secrets.kv.v2.create_or_update_secret(
                path=f"vehicle/{vehicle_id}",
                secret=final_config,
                mount_point='cubbyhole'
            )
            logger.info(f"Secret written successfully")
        except Exception as e:
            logger.error(f"Failed to write secret: {e}")
            raise e


        return final_config


    @staticmethod
    def read_secrets_by_vehicle_id(vehicle_id: int) -> dict:
        """
        Получить конфигурацию для vehicle_id

        Args:
            vehicle_id: int

        Returns:
            dict
        """
        client = VaultClient.init_conn()
        if not client:
            raise Exception("Vault authentication failed!")

        try:
            read_response = client.secrets.kv.v2.read_secret(
                path=f"vehicle/{vehicle_id}",
                mount_point='cubbyhole'
            )
            stored = read_response['data']['data']
            return stored
        except Exception as e:
            raise e


    @staticmethod
    def delete_secrets_by_vehicle_id(vehicle_id: int) -> None:
        """
        Удалить конфигурацию для vehicle_id
        Args:
            vehicle_id: int

        Returns:
            None
        """
        client = VaultClient.init_conn()
        if not client:
            raise Exception("Vault authentication failed!")
        try:
            client.secrets.kv.v2.delete_secret(
                path=f"data/vehicle/{vehicle_id}",
                mount_point='cubbyhole'
            )
            return True
        except Exception as e:
            raise e
