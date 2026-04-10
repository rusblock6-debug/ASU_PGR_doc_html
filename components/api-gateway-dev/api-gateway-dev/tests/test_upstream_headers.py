from unittest.mock import MagicMock

from multidict import CIMultiDict
from yarl import URL

from src.proxy import _build_upstream_headers


def _make_request(headers: dict[str, str], request_id: str | None = None) -> MagicMock:
    """Create a minimal mock of aiohttp.web.Request for _build_upstream_headers."""
    request = MagicMock()
    request.headers = CIMultiDict(headers)
    request.get = lambda key, default=None: (  # noqa: ARG005
        request_id if key == "request_id" else default
    )
    return request


def test_build_upstream_headers_sets_x_source() -> None:
    request = _make_request({"Host": "original-host", "Accept": "application/json"})
    upstream_url = URL("http://backend:3000/api/v1/data")

    headers = _build_upstream_headers(request, upstream_url)

    assert headers["X-Source"] == "api-gateway"


def test_build_upstream_headers_overwrites_existing_x_source() -> None:
    request = _make_request({
        "Host": "original-host",
        "X-Source": "malicious-client",
    })
    upstream_url = URL("http://backend:3000/api/v1/data")

    headers = _build_upstream_headers(request, upstream_url)

    assert headers["X-Source"] == "api-gateway"
