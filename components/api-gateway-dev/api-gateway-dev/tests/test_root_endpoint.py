import unittest

from aiohttp.test_utils import TestClient, TestServer

from src.app import create_app
from src.config import Settings


class RootEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        settings = Settings(
            services={
                "versioned-service": {
                    "url": "http://versioned-service:3001",
                    "path_pattern": "/api/{version}/{path}",
                },
                "unversioned-service": {
                    "url": "http://legacy-service:3002",
                    "path_pattern": "/api/{path}",
                },
            },
            auth={
                "url": "http://auth-service:3000",
                "verify_endpoint": "/api/v1/verify",
            },
            service_name="api-gateway-test",
            log_level="INFO",
        )
        app = create_app(settings)
        self.server = TestServer(app)
        await self.server.start_server()
        self.client = TestClient(self.server)
        await self.client.start_server()

    async def asyncTearDown(self) -> None:
        await self.client.close()
        await self.server.close()

    async def test_get_root_returns_200_and_json_content_type(self) -> None:
        response = await self.client.get("/")

        self.assertEqual(response.status, 200)
        self.assertEqual(response.content_type, "application/json")

    async def test_get_root_response_contains_expected_contract(self) -> None:
        response = await self.client.get("/")
        self.assertEqual(response.status, 200)

        payload = await response.json()

        self.assertIn("version", payload)
        self.assertIn("services", payload)
        self.assertIn("supported_versions", payload)
        self.assertIn("auth", payload)

        self.assertIsInstance(payload["version"], str)
        self.assertTrue(payload["version"].strip())

        services = payload["services"]
        self.assertTrue(services["versioned-service"]["versioned"])
        self.assertFalse(services["unversioned-service"]["versioned"])

        supported_versions = payload["supported_versions"]
        self.assertIn("v1", supported_versions)
        self.assertIn("v2", supported_versions)

        auth = payload["auth"]
        self.assertIn("url", auth)
        self.assertIn("verify_endpoint", auth)
        self.assertIsInstance(auth["url"], str)
        self.assertIsInstance(auth["verify_endpoint"], str)

    async def test_get_root_without_authorization_header_returns_200(self) -> None:
        response = await self.client.get("/")

        self.assertEqual(response.status, 200)


class RootEndpointEmptyServicesTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        settings = Settings(
            services={
                "placeholder": {
                    "url": "http://placeholder-service:3001",
                    "path_pattern": "/api/{version}/{path}",
                },
            },
            auth={
                "url": "http://auth-service:3000",
                "verify_endpoint": "/api/v1/verify",
            },
            service_name="api-gateway-test",
            log_level="INFO",
        )
        settings.services = {}
        app = create_app(settings)
        self.server = TestServer(app)
        await self.server.start_server()
        self.client = TestClient(self.server)
        await self.client.start_server()

    async def asyncTearDown(self) -> None:
        await self.client.close()
        await self.server.close()

    async def test_get_root_returns_empty_services_dict(self) -> None:
        response = await self.client.get("/")

        self.assertEqual(response.status, 200)
        payload = await response.json()
        self.assertEqual(payload["services"], {})
