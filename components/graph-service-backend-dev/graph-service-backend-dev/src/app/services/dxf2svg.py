"""Конвертация DXF-файла в изображение: векторный SVG

- SVG: ezdxf SVGBackend, без системных шрифтов, подходит для превью в браузере.
"""

import logging
from io import BytesIO

from ezdxf import recover
from ezdxf.addons.drawing import Frontend, RenderContext, layout, svg
from ezdxf.fonts.font_manager import FontNotFoundError

logger = logging.getLogger(__name__)


def dxf_bytes_to_svg_bytes(
    dxf_bytes: bytes,
    margin_mm: float = 10.0,
) -> bytes | None:
    """Конвертирует DXF из байтов в SVG байты полностью в памяти без использования временных файлов.

    Args:
        dxf_bytes: Байты DXF файла.
        margin_mm: Отступ от краёв страницы (мм). Размер страницы подстраивается под содержимое.

    Returns:
        Байты SVG файла или None при ошибке.
    """
    try:
        # Читаем DXF из байтов используя BytesIO
        dxf_stream = BytesIO(dxf_bytes)
        doc, auditor = recover.read(dxf_stream)

        logger.debug("Accessing modelspace")
        msp = doc.modelspace()

        logger.debug("Creating render context and backend")
        ctx = RenderContext(doc)
        backend = svg.SVGBackend()
        frontend = Frontend(ctx, backend)
        logger.debug("Drawing layout")
        frontend.draw_layout(msp)
        logger.debug("Layout drawn successfully")

        # Авто-размер страницы по содержимому, отступ в мм
        logger.debug("Creating page layout")
        page = layout.Page(0, 0, layout.Units.mm, margins=layout.Margins.all(margin_mm))
        logger.debug("Getting SVG string from backend")
        svg_string = backend.get_string(page)
        logger.debug(
            "SVG string generated length=%s is_none=%s",
            len(svg_string) if svg_string else 0,
            svg_string is None,
        )

        if not svg_string or len(svg_string.strip()) == 0:
            logger.error(
                "SVG string is empty after conversion svg_string_is_none=%s svg_string_length=%s",
                svg_string is None,
                len(svg_string) if svg_string else 0,
            )
            return None

        logger.info("DXF converted to SVG successfully in memory size=%s", len(svg_string))
        return svg_string.encode("utf-8")

    except FontNotFoundError as e:
        raise RuntimeError(
            "Не удалось конвертировать DXF в SVG: в системе отсутствуют шрифты. "
            "Установите пакеты fonts-dejavu и fonts-liberation в Docker-образ.",
        ) from e
    except Exception as e:
        logger.error("Failed to convert DXF to SVG error=%s", str(e), exc_info=True)
        raise
