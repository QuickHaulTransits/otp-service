import pytest
from unittest.mock import MagicMock, patch
import redis

@pytest.fixture(autouse=True)
def mock_redis():
    with patch('redis.from_url') as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client

@pytest.fixture(autouse=True)
def mock_settings():
    with patch('shared.config.settings') as mock:
        mock.redis_url = "redis://localhost:6379"
        mock.notification_service_url = "http://notification:8004"
        yield mock
