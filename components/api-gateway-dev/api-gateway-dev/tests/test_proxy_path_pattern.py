import pytest

from src.proxy import _build_upstream_url


@pytest.mark.parametrize(
    ("pattern", "version", "path", "expected_path"),
    [
        ("/api/{version}/{path}", "v1", "orders", "/api/v1/orders"),
        ("/api/{path}", "v1", "orders", "/api/orders"),
        ("/{path}", "v1", "orders", "/orders"),
        ("/api/{version}/{path}", "v1", "", "/api/v1"),
        ("/api/{path}", "v1", "", "/api"),
        ("/{path}", "v1", "", "/"),
        ("/api/{version}", "v1", "orders", "/api/v1/orders"),
    ],
)
def test_build_upstream_url_uses_path_pattern(
    pattern: str,
    version: str,
    path: str,
    expected_path: str,
) -> None:
    upstream_url = _build_upstream_url(
        service_url="http://trip-service:3001",
        api_version=version,
        path_pattern=pattern,
        path=path,
        query_string="",
    )

    assert upstream_url.path == expected_path


def test_build_upstream_url_appends_query_string() -> None:
    upstream_url = _build_upstream_url(
        service_url="http://trip-service:3001",
        api_version="v1",
        path_pattern="/api/{version}/{path}",
        path="orders",
        query_string="limit=10&offset=20",
    )

    assert upstream_url.path == "/api/v1/orders"
    assert upstream_url.query_string == "limit=10&offset=20"
