import logging
from pathlib import Path
from typing import List

import redis.asyncio as redis
import yaml

from app.models.schemas import AutorepubConfig
from app.models.types import AutorepubConfigType
from app.settings import settings

logger = logging.getLogger("autorepub.config")


class AutorepubConfigManager:
    """Manages autorepub configurations and their activation state."""

    CONFIG_IS_ACTIVE_PREFIX = "autorepub:is_active"
    "Prefix for redis key of configs activity flag `{CONFIG_IS_ACTIVE_PREFIX}:{config_name}`"
    INSTANCES_SUSPENSION_KEY: str = "autorepub:suspension"
    "Key for redis set of suspended instance ids"

    def __init__(self, redis_client: redis.Redis) -> None:
        """Initialize config manager."""
        self.redis: redis.Redis = redis_client
        self.configs: dict[str, AutorepubConfig] = {}
        self.active_configs: set[str] = set()
        self.temporary_configs: set[str] = set()

        self.suspended_instances: set[str] = set()


    # ─────────────────────────────────────────────────────────────────────────
    # Load configs from external source
    # ─────────────────────────────────────────────────────────────────────────

    async def load(self) -> None:
        """Load YAML configs and initialize from Redis state."""

        # Load YAML configs
        yaml_configs = self.load_yaml_configs()
        self.configs.update({
            cfg.name: cfg
            for cfg in yaml_configs
        })

        # Auto activate configs which:
        # - have active flag in redis
        # - have autostart flag in yaml and no inactive flag in redis
        for cfg in self.configs.values():
            is_active = await self.get_autorepub_active(cfg.name)
            if (cfg.autostart and is_active is None) or is_active:
                await self.set_autorepub_active(cfg.name)
                self.active_configs.add(cfg.name)
                logger.info(f"Activated config: {cfg.name}")

        # Load suspended instances from redis
        await self.load_suspended_instances()
        logger.debug(f"Loaded suspended instances: {self.suspended_instances}")

    def load_yaml_configs(self, config_dir: str = "configs") -> List[AutorepubConfig]:
        """
        Load autorepub configurations from YAML files.

        Args:
            config_dir: Directory containing YAML config files

        Returns:
            List of AutorepubConfig objects
        """

        configs = []
        config_path = Path(__file__).parent / config_dir

        if not config_path.exists():
            logger.warning(f"Autorepub config directory {config_dir} does not exist, skipping")
            return configs

        if not config_path.is_dir():
            logger.warning(f"Autorepub config path {config_dir} is not a directory, skipping")
            return configs

        yaml_files = sorted([f for f in config_path.glob("*.yaml")] + [f for f in config_path.glob("*.yml")])
        if not yaml_files:
            logger.warning(f"No YAML files found in {config_dir}")
            return configs

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, "r") as f:
                    data = yaml.safe_load(f)

                    if not data:
                        logger.warning(f"Empty YAML file: {yaml_file.name}")
                        continue

                    config = AutorepubConfig(name=yaml_file.stem, **data)
                    if not self.is_config_applicable(config):
                        continue

                    configs.append(config)
                    logger.info(f"Loaded applicable autorepub config {yaml_file.name}")

            except yaml.YAMLError as e:
                logger.error(f"Failed to parse YAML file {yaml_file.name}: {e}")

            except Exception:
                logger.exception(f"Failed to load config from {yaml_file.name}")

        logger.info(f"Loaded {len(configs)} applicable autorepub config(s) from {config_path}")
        return configs

    def is_config_applicable(self, config: AutorepubConfig) -> bool:
        if config.source_instance_id != settings.instance_id:
            logger.info(
                f"Autorepub config {config.name} is NOT applicable to this instance_id={settings.instance_id} - "
                f"source_instance_id={config.source_instance_id} does not match it"
            )
            return False
        if settings.instance_id in config.target_instances_list:
            logger.info(
                f"Autorepub config {config.name} is NOT applicable to this instance_id={settings.instance_id} - "
                f"one of target_instances={config.target_instances} matches it"
            )
            return False
        if not config.target_instances_list:
            logger.info(
                f"Autorepub config {config.name} is NOT applicable to this instance_id={settings.instance_id} - "
                f"target_instances is empty"
            )
            return False
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Temporary config api
    # ─────────────────────────────────────────────────────────────────────────

    def get_temporary_config(self, name: str) -> AutorepubConfig | None:
        """Get a specific temporary config by name."""
        if name not in self.temporary_configs:
            return
        return self.configs.get(name)

    def add_temporary_config(self, config: AutorepubConfig) -> bool:
        """Add a temporary config.

        Returns:
            Config True if added successfully, False if config already exists
        """

        if config.name in self.configs:
            return False

        self.configs[config.name] = config
        self.temporary_configs.add(config.name)
        logger.info(f"Added temporary autorepub config: {config.name}")
        return True

    async def delete_temporary_config(self, name: str) -> bool:
        """Remove a temporary config.

        Returns:
            True if config was removed, False if not found
        """

        if name not in self.temporary_configs:
            return False

        await self.delete_autorepub_active(name)
        self.configs.pop(name)
        logger.info(f"Removed temporary autorepub config: {name}")
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Config api
    # ─────────────────────────────────────────────────────────────────────────

    async def activate_config(self, name: str) -> bool:
        """Activate a config (set Redis key).

        Returns:
            True if config was activated, False if config not found
        """
        if name not in self.configs:
            return False

        # Set Redis key
        await self.set_autorepub_active(name)
        self.active_configs.add(name)
        logger.info(f"Activated config: {name}")
        return True

    async def deactivate_config(self, name: str) -> bool:
        """Deactivate a config (delete Redis key).

        Returns:
            True if config was deactivated, False if config not found
        """
        if name not in self.configs:
            return False

        # Set Redis key to inactive
        await self.set_autorepub_inactive(name)
        self.active_configs.discard(name)
        logger.info(f"Deactivated config: {name}")
        return True

    def is_config_active(self, name: str) -> bool:
        """Check if config is active.

        Returns:
            True if config is active, False otherwise
        """
        if name not in self.configs:
            return False

        return name in self.active_configs

    def get_configs(
        self,
        type_: AutorepubConfigType | None = None,
        is_active: bool | None = None
    ) -> List[AutorepubConfig]:
        """Get all configs.

        Returns:
            List of active AutorepubConfig objects

        TODO: cache active configs list (group by type?)
        """

        def type_check(cfg: AutorepubConfig) -> bool:
            return cfg.type == type_

        def activity_check(cfg: AutorepubConfig) -> bool:
            return self.is_config_active(cfg.name) == is_active

        checks = []
        if type_ is not None:
            checks.append(type_check)
        if is_active is not None:
            checks.append(activity_check)

        configs = [
            config
            for config in self.configs.values()
            if all([check(config) for check in checks])
        ]
        return configs

    def get_config(self, name: str) -> AutorepubConfig | None:
        """Get a specific config by name."""
        return self.configs.get(name)

    # ─────────────────────────────────────────────────────────────────────────
    # Redis operations (configs)
    # ─────────────────────────────────────────────────────────────────────────

    async def get_autorepub_active(self, name: str) -> bool | None:
        """Get autorepub activation value for a config.

        Returns:
            True if active, False if not, and None if key doesn't exist
        """

        key = f"{self.CONFIG_IS_ACTIVE_PREFIX}:{name}"
        result = await self.redis.get(key)
        if result is None:
            return None
        result = result.decode() if isinstance(result, bytes) else str(result)
        return result == "1"

    async def set_autorepub_active(self, name: str) -> None:
        """Set autorepub activation key to "1"."""

        key = f"{self.CONFIG_IS_ACTIVE_PREFIX}:{name}"
        await self.redis.set(key, "1")

    async def set_autorepub_inactive(self, name: str) -> None:
        """Set autorepub activation key to "0"."""

        key = f"{self.CONFIG_IS_ACTIVE_PREFIX}:{name}"
        await self.redis.set(key, "0")

    async def delete_autorepub_active(self, name: str) -> None:
        """Delete autorepub activation key."""

        key = f"{self.CONFIG_IS_ACTIVE_PREFIX}:{name}"
        await self.redis.delete(key)

    # ─────────────────────────────────────────────────────────────────────────
    # Instance suspension api + redis operations (wifi-service integration)
    # ─────────────────────────────────────────────────────────────────────────

    async def load_suspended_instances(self) -> None:
        instances_bytes = await self.redis.smembers(self.INSTANCES_SUSPENSION_KEY)  # type: ignore
        self.suspended_instances.update({ib.decode() for ib in instances_bytes})

    async def suspend_instances(self, instance_ids: list[str]) -> list[str]:
        await self.redis.sadd(self.INSTANCES_SUSPENSION_KEY, *instance_ids)  # type: ignore
        suspended = []
        for instance_id in instance_ids:
            if instance_id not in self.suspended_instances:
                self.suspended_instances.add(instance_id)
                suspended.append(instance_id)
        return suspended

    async def resume_instances(self, instance_ids: list[str]) -> list[str]:
        await self.redis.srem(self.INSTANCES_SUSPENSION_KEY, *instance_ids)  # type: ignore
        resumed = []
        for instance_id in instance_ids:
            if instance_id in self.suspended_instances:
                self.suspended_instances.discard(instance_id)
                resumed.append(instance_id)
        return resumed
