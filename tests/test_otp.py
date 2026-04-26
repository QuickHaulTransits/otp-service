import pytest
import httpx
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock
from app import app, redis_client, generate_otp, format_phone_otp_message, format_email_otp_message

@pytest.mark.asyncio
async def test_generate_otp():
    otp = generate_otp()
    assert len(otp) == 6
    assert otp.isdigit()

def test_format_messages():
    phone_msg = format_phone_otp_message("1234567890", "123456")
    assert "123456" in phone_msg
    email_msg = format_email_otp_message("test@example.com", "123456")
    assert "123456" in email_msg

@pytest.mark.asyncio
async def test_health_check_healthy():
    with patch.object(redis_client, 'ping', return_value=True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "redis": "connected"}

@pytest.mark.asyncio
async def test_health_check_unhealthy():
    with patch.object(redis_client, 'ping', side_effect=Exception("Connection error")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "unhealthy", "redis": "disconnected"}

@pytest.mark.asyncio
async def test_send_otp_success():
    email = "test@example.com"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True}
    
    # Mock the entire AsyncClient to handle 'async with'
    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post = AsyncMock(return_value=mock_response)
    
    with patch.object(redis_client, 'setex', return_value=True), \
         patch('httpx.AsyncClient', return_value=mock_client):
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/send", json={"email": email})
            
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["email_sent"] is True
    assert "otp" in data

@pytest.mark.asyncio
async def test_send_otp_no_email():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/send", json={"email": ""})
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_send_otp_email_failure():
    email = "test@example.com"
    mock_response = MagicMock()
    mock_response.status_code = 500
    
    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post = AsyncMock(return_value=mock_response)
    
    with patch.object(redis_client, 'setex', return_value=True), \
         patch('httpx.AsyncClient', return_value=mock_client):
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/send", json={"email": email})
            
    assert response.status_code == 200
    assert response.json()["email_sent"] is False

@pytest.mark.asyncio
async def test_verify_otp_success():
    email = "test@example.com"
    otp = "123456"
    with patch.object(redis_client, 'get', return_value=otp), \
         patch.object(redis_client, 'delete', return_value=1):
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/verify", json={"email": email, "otp": otp})
            
    assert response.status_code == 200
    assert response.json()["success"] is True

@pytest.mark.asyncio
async def test_verify_otp_missing_fields():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/verify", json={"email": "", "otp": ""})
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_verify_otp_invalid():
    email = "test@example.com"
    otp = "123456"
    with patch.object(redis_client, 'get', return_value="654321"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/verify", json={"email": email, "otp": otp})
            
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid OTP"

@pytest.mark.asyncio
async def test_send_phone_otp_success():
    phone = "1234567890"
    with patch.object(redis_client, 'setex', return_value=True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(f"/send-phone?phone={phone}")
    assert response.status_code == 200
    assert response.json()["success"] is True

@pytest.mark.asyncio
async def test_send_phone_otp_no_phone():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/send-phone?phone=")
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_verify_phone_otp_success():
    phone = "1234567890"
    otp = "123456"
    with patch.object(redis_client, 'get', return_value=otp), \
         patch.object(redis_client, 'delete', return_value=1):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(f"/verify-phone?phone={phone}&otp={otp}")
    assert response.status_code == 200
    assert response.json()["success"] is True

@pytest.mark.asyncio
async def test_verify_phone_otp_fail():
    phone = "1234567890"
    otp = "123456"
    # Case: OTP not found
    with patch.object(redis_client, 'get', return_value=None):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(f"/verify-phone?phone={phone}&otp={otp}")
    assert response.status_code == 400
    
    # Case: Invalid OTP
    with patch.object(redis_client, 'get', return_value="wrong"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(f"/verify-phone?phone={phone}&otp={otp}")
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_clear_otp():
    with patch.object(redis_client, 'delete', return_value=1):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Email branch
            resp1 = await ac.delete("/clear?email=test@test.com")
            assert resp1.status_code == 200
            # Phone branch
            resp2 = await ac.delete("/clear?phone=12345")
            assert resp2.status_code == 200
            # Error branch
            resp3 = await ac.delete("/clear")
            assert resp3.status_code == 400

@pytest.mark.asyncio
async def test_get_status_error():
    with patch.object(redis_client, 'keys', side_effect=Exception("Redis error")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/status")
    assert response.status_code == 200
    assert response.json()["status"] == "error"
