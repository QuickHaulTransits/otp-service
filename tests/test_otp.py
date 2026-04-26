import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from app import app, redis_client

@pytest.mark.asyncio
async def test_health_check_healthy():
    with patch.object(redis_client, 'ping', return_value=True):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "redis": "connected"}

@pytest.mark.asyncio
async def test_health_check_unhealthy():
    with patch.object(redis_client, 'ping', side_effect=Exception("Connection error")):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "unhealthy", "redis": "disconnected"}

@pytest.mark.asyncio
async def test_send_otp_success():
    email = "test@example.com"
    with patch.object(redis_client, 'setex', return_value=True), \
         patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"success": True}
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/send", json={"email": email})
            
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "otp" in response.json()
    assert response.json()["email_sent"] is True

@pytest.mark.asyncio
async def test_send_otp_email_failure():
    email = "test@example.com"
    with patch.object(redis_client, 'setex', return_value=True), \
         patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        
        mock_post.return_value.status_code = 500
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/send", json={"email": email})
            
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["email_sent"] is False
    assert "email failed" in response.json()["message"]

@pytest.mark.asyncio
async def test_verify_otp_success():
    email = "test@example.com"
    otp = "123456"
    with patch.object(redis_client, 'get', return_value=otp), \
         patch.object(redis_client, 'delete', return_value=1):
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/verify", json={"email": email, "otp": otp})
            
    assert response.status_code == 200
    assert response.json()["success"] is True

@pytest.mark.asyncio
async def test_verify_otp_invalid():
    email = "test@example.com"
    otp = "123456"
    with patch.object(redis_client, 'get', return_value="654321"):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/verify", json={"email": email, "otp": otp})
            
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid OTP"

@pytest.mark.asyncio
async def test_verify_otp_expired():
    email = "test@example.com"
    otp = "123456"
    with patch.object(redis_client, 'get', return_value=None):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/verify", json={"email": email, "otp": otp})
            
    assert response.status_code == 400
    assert response.json()["detail"] == "OTP not found or expired"

@pytest.mark.asyncio
async def test_send_phone_otp():
    phone = "1234567890"
    with patch.object(redis_client, 'setex', return_value=True):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(f"/send-phone?phone={phone}")
            
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "otp" in response.json()

@pytest.mark.asyncio
async def test_verify_phone_otp_success():
    phone = "1234567890"
    otp = "123456"
    with patch.object(redis_client, 'get', return_value=otp), \
         patch.object(redis_client, 'delete', return_value=1):
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(f"/verify-phone?phone={phone}&otp={otp}")
            
    assert response.status_code == 200
    assert response.json()["success"] is True

@pytest.mark.asyncio
async def test_get_status():
    with patch.object(redis_client, 'keys', side_effect=[["key1"], ["key2"]]):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/status")
            
    assert response.status_code == 200
    assert response.json()["email_otps"] == 1
    assert response.json()["phone_otps"] == 1

@pytest.mark.asyncio
async def test_clear_otp_email():
    email = "test@example.com"
    with patch.object(redis_client, 'delete', return_value=1):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.delete(f"/clear?email={email}")
            
    assert response.status_code == 200
    assert f"OTP cleared for {email}" in response.json()["message"]
