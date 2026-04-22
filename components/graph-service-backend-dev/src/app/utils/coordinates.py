"""Утилиты для работы с координатами"""

import math
import os

from loguru import logger

# Константы для метрической проекции
METERS_PER_DEGREE_LAT = 111_320.0  # метров на градус широты


class CoordinateTransformer:
    """Класс для трансформации GPS координат в Canvas координаты"""

    def __init__(self):
        # Загрузка дефолтного origin point из environment variables
        # Дефолт: центр графа вычислен автоматически (AVG всех узлов из БД)
        self._origin_gps_lat = float(os.getenv("ORIGIN_GPS_LAT", "58.1728"))
        self._origin_gps_lon = float(os.getenv("ORIGIN_GPS_LON", "59.8164"))
        self._origin_canvas_x = float(os.getenv("ORIGIN_CANVAS_X", "0"))
        self._origin_canvas_y = float(os.getenv("ORIGIN_CANVAS_Y", "0"))
        self._origin_canvas_z = float(os.getenv("ORIGIN_CANVAS_Z", "0"))

        # Предварительно вычисляем meters_per_degree_lon для origin point
        self._update_meters_per_degree()

        # Логируем для отладки
        logger.debug(
            f"CoordinateTransformer initialized with Origin Point: "
            f"GPS({self._origin_gps_lat}°, {self._origin_gps_lon}°) → "
            f"Canvas({self._origin_canvas_x}м, {self._origin_canvas_y}м, {self._origin_canvas_z}м)",
        )

    def _update_meters_per_degree(self):
        """Обновить вычисление meters_per_degree_lon"""
        origin_lat_rad = (self._origin_gps_lat * math.pi) / 180
        self.meters_per_degree_lon = METERS_PER_DEGREE_LAT * math.cos(origin_lat_rad)

    def set_origin(
        self,
        gps_lat: float,
        gps_lon: float,
        canvas_x: float = 0,
        canvas_y: float = 0,
        canvas_z: float = -50,
    ):
        """Установить новый origin point"""
        self._origin_gps_lat = gps_lat
        self._origin_gps_lon = gps_lon
        self._origin_canvas_x = canvas_x
        self._origin_canvas_y = canvas_y
        self._origin_canvas_z = canvas_z
        self._update_meters_per_degree()

    def get_origin(self) -> dict:
        """Получить текущий origin point"""
        return {
            "gps_lat": self._origin_gps_lat,
            "gps_lon": self._origin_gps_lon,
            "canvas_x": self._origin_canvas_x,
            "canvas_y": self._origin_canvas_y,
            "canvas_z": self._origin_canvas_z,
        }

    @property
    def origin_gps_lat(self) -> float:
        return self._origin_gps_lat

    @property
    def origin_gps_lon(self) -> float:
        return self._origin_gps_lon

    @property
    def origin_canvas_x(self) -> float:
        return self._origin_canvas_x

    @property
    def origin_canvas_y(self) -> float:
        return self._origin_canvas_y

    @property
    def origin_canvas_z(self) -> float:
        return self._origin_canvas_z

    def gps_to_canvas(self, lat: float, lon: float) -> tuple[float, float]:
        """Трансформация GPS координат (lat/lon в градусах) в Canvas координаты (x/y в метрах)

        Args:
            lat: GPS широта (latitude) в градусах
            lon: GPS долгота (longitude) в градусах

        Returns:
            Tuple[float, float]: Canvas координаты (x, y) в метрах
        """
        # Разница в градусах от опорной точки
        delta_lat = lat - self._origin_gps_lat
        delta_lon = lon - self._origin_gps_lon

        # Конверсия в метры и добавление к canvas координатам опорной точки
        x = self._origin_canvas_x + (delta_lon * self.meters_per_degree_lon)
        # ⚠️ ИНВЕРТИРУЕМ Y: в Canvas Y растёт вниз, в GPS Y (широта) растёт вверх
        y = self._origin_canvas_y - (delta_lat * METERS_PER_DEGREE_LAT)

        return x, y

    def canvas_to_gps(self, x: float, y: float) -> tuple[float, float]:
        """Трансформация Canvas координат (x/y в метрах) в GPS координаты (lat/lon в градусах)

        Args:
            x: Canvas координата X в метрах
            y: Canvas координата Y в метрах

        Returns:
            Tuple[float, float]: GPS координаты (lat, lon) в градусах
        """
        # Разница в метрах от опорной точки
        delta_x = x - self._origin_canvas_x
        delta_y = self._origin_canvas_y - y  # Инвертируем Y обратно

        # Конверсия в градусы
        delta_lon = delta_x / self.meters_per_degree_lon
        delta_lat = delta_y / METERS_PER_DEGREE_LAT

        # Добавление к GPS координатам опорной точки
        lat = self._origin_gps_lat + delta_lat
        lon = self._origin_gps_lon + delta_lon

        return lat, lon


# Глобальный singleton transformer
coordinate_transformer = CoordinateTransformer()


def transform_gps_to_canvas(lat: float, lon: float) -> tuple[float, float]:
    """Трансформация GPS координат в Canvas координаты (helper функция)

    Args:
        lat: GPS широта в градусах
        lon: GPS долгота в градусах

    Returns:
        Tuple[float, float]: Canvas координаты (x, y) в метрах
    """
    return coordinate_transformer.gps_to_canvas(lat, lon)


def transform_canvas_to_gps(x: float, y: float) -> tuple[float, float]:
    """Трансформация Canvas координат в GPS координаты (helper функция)

    Args:
        x: Canvas координата X в метрах
        y: Canvas координата Y в метрах

    Returns:
        Tuple[float, float]: GPS координаты (lat, lon) в градусах
    """
    return coordinate_transformer.canvas_to_gps(x, y)
