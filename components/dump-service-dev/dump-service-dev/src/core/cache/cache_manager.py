"""CacheManager для работы с cache."""

# ruff: noqa: D101
# mypy: disable-error-code="no-untyped-def,type-arg,union-attr,no-untyped-call,misc"
import inspect
from collections.abc import Callable
from functools import wraps

from loguru import logger

from src.core.cache.client.redis_cache_client import RedisCacheClient
from src.core.cache.key_maker import FunctionKeyMaker
from src.core.cache.ttl import TTL
from src.core.config import get_settings
from src.core.dto.scheme.cache.param import CacheInvalidateParams

settings = get_settings()


class CacheManager(FunctionKeyMaker, RedisCacheClient):
    def __init__(self):
        super().__init__()
        self.redis_url: str | None = None
        self.project_name: str = settings.PROJECT_INFO.get_project_name()

    def init(self, redis_url: str) -> None:
        """Init cache."""
        self._set_project_name(self.project_name)
        self.redis_url = redis_url
        RedisCacheClient.__init__(self, redis_url)

    def cached(self, ttl: int = TTL.time()) -> Callable:
        """Декоратор для кэширования."""

        def _cached(function: Callable):
            """Декоратор для кэширования."""

            @wraps(function)
            async def __cached(*args, **kwargs):
                """Функция-обертка для кэширования."""
                if not self.redis_url or not self.project_name:
                    raise Exception("key_maker или project_name не объявлены")

                key = await self.make_key(*args, **kwargs, function=function)
                cached_response = await self.get(key=key)
                if cached_response:
                    logger.info(f"CACHED: ключ: {key}")
                    return cached_response

                response = await function(*args, **kwargs)
                await self.set(value=response, key=key, ttl=ttl)
                return response

            return __cached

        return _cached

    def invalidate(self, *params: CacheInvalidateParams):
        """Декоратор инвалидации кэширования."""

        def _invalidate(function: Callable):
            """Декоратор инвалидации кэширования."""

            @wraps(function)
            async def __invalidate(*args, **kwargs):
                """Функция-обертка для инвалидации кэширования."""
                if not self.redis_url or not self.project_name:
                    raise Exception("key_maker или project_name не объявлены")

                function_result = await function(*args, **kwargs)
                for cache_invalidate_param in params:
                    for dependency_func in cache_invalidate_param.functions:
                        key_mask = await self.make_invalid_mask_key(dependency_func)

                        if cache_invalidate_param.params is None:
                            logger.info(
                                f"INVALID CACHE WITHOUT PARAMS: с маской ключа {key_mask}",
                            )
                            await self.delete_by_invalid_key(invalid_mask_key=key_mask)

                        else:
                            dependency_params: list[str] = []
                            bound_args = inspect.signature(function).bind(
                                *args,
                                **kwargs,
                            )
                            bound_args.apply_defaults()
                            wrapped_function_params = bound_args.arguments
                            for dependency_param in cache_invalidate_param.params:
                                if not dependency_param.caching_func_param:
                                    dependency_param.caching_func_param = (
                                        dependency_param.wrapped_func_param
                                    )

                                caching_param_name = dependency_param.caching_func_param.split(".")[
                                    -1
                                ]

                                wrapped_param_names = dependency_param.wrapped_func_param.split(".")
                                wrapped_param_value = wrapped_function_params.get(
                                    wrapped_param_names[0],
                                )

                                if wrapped_param_names[0] in wrapped_function_params:
                                    for key in wrapped_param_names[1:]:
                                        wrapped_param_value = getattr(
                                            wrapped_param_value,
                                            key,
                                        )

                                    dependency_params.append(
                                        self.make_function_param(
                                            name=caching_param_name,
                                            value=wrapped_param_value,
                                        ),
                                    )

                            logger.info(
                                f"INVALID CACHE WITH PARAMS: с маской ключа {key_mask}; "
                                f"с параметрами {dependency_params}",
                            )
                            await self.delete_by_invalid_key(
                                invalid_mask_key=key_mask,
                                params=dependency_params,
                            )

                return function_result

            return __invalidate

        return _invalidate


Cache = CacheManager()
