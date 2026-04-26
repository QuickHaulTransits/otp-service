from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
import random
import string
from datetime import timedelta
import httpx
import sys
from pathlib import Path

from shared.config import settings

NOTIFICATION_SERVICE_URL = settings.notification_service_url

app = FastAPI(title="OTP Service", version="2.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis connection for OTP storage
redis_client = redis.from_url(settings.redis_url, db=3, decode_responses=True)

# OTP TTL (10 minutes)
OTP_TTL = timedelta(minutes=10)

class OTPRequest(BaseModel):
    email: str

class OTPVerifyRequest(BaseModel):
    email: str
    otp: str

def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP"""
    return ''.join(random.choices(string.digits, k=length))

def format_phone_otp_message(phone: str, otp: str) -> str:
    """Format OTP message for SMS"""
    return f"Your QuickHaul OTP is: {otp}. Valid for 10 minutes. Do not share this OTP."

def format_email_otp_message(email: str, otp: str) -> str:
    """Format OTP message for email"""
    return f"""
    Your QuickHaul OTP is: {otp}
    
    This OTP is valid for 10 minutes.
    Please enter this code to complete your registration/login.
    
    If you didn't request this OTP, please ignore this email.
    
    Thank you,
    QuickHaul Team
    """

@app.post("/send")
async def send_otp(request: OTPRequest):
    """Send OTP to email via notification service"""
    email = request.email
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    # Generate OTP
    otp = generate_otp()
    
    # Store OTP in Redis
    redis_client.setex(f"otp:{email}", OTP_TTL, otp)
    
    # Try to send email via notification service
    email_sent = False
    notification_error = None
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{NOTIFICATION_SERVICE_URL}/send-otp",
                json={"email": email, "otp": otp},
                timeout=5.0
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    email_sent = True
                else:
                    notification_error = result.get("message", "Unknown error")
            else:
                notification_error = f"Notification service returned {response.status_code}"
    except Exception as e:
        notification_error = str(e)
    
    # Always log to console for visibility
    print(f"\n{'='*50}")
    print(f"🔔 OTP GENERATED FOR: {email}")
    print(f"🔢 OTP CODE: {otp}")
    print(f"📧 EMAIL SENT: {'Yes' if email_sent else 'No'}")
    if notification_error:
        print(f"⚠️  EMAIL ERROR: {notification_error}")
    print(f"⏰ VALID FOR: 10 minutes")
    print(f"{'='*50}\n")
    
    return {
        "success": True,
        "message": "OTP generated" + (" and email sent" if email_sent else f" (email failed: {notification_error})"),
        "otp": otp,  # Returned for UI display
        "email_sent": email_sent,
        "expires_in": 600  # 10 minutes in seconds
    }

@app.post("/verify")
async def verify_otp(request: OTPVerifyRequest):
    """Verify OTP"""
    email = request.email
    otp = request.otp
    
    if not email or not otp:
        raise HTTPException(status_code=400, detail="Email and OTP are required")
    
    # Get stored OTP
    stored_otp = redis_client.get(f"otp:{email}")
    
    if not stored_otp:
        raise HTTPException(status_code=400, detail="OTP not found or expired")
    
    if stored_otp != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    # OTP is valid, delete it
    redis_client.delete(f"otp:{email}")
    
    return {
        "success": True,
        "message": "OTP verified successfully"
    }

@app.post("/send-phone")
async def send_phone_otp(phone: str):
    """Send OTP to phone (development mode - prints to console)"""
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number is required")
    
    # Generate OTP
    otp = generate_otp()
    
    # Store OTP in Redis
    redis_client.setex(f"otp:phone:{phone}", OTP_TTL, otp)
    
    # In development mode, just log the OTP
    print(f"\n{'='*50}")
    print(f"📱 OTP SENT TO PHONE: {phone}")
    print(f"🔢 OTP CODE: {otp}")
    print(f"⏰ VALID FOR: 10 minutes")
    print(f"{'='*50}\n")
    
    return {
        "success": True,
        "message": "OTP sent to phone successfully",
        "otp": otp,  # Only in development mode
        "expires_in": 600
    }

@app.post("/verify-phone")
async def verify_phone_otp(phone: str, otp: str):
    """Verify phone OTP"""
    if not phone or not otp:
        raise HTTPException(status_code=400, detail="Phone number and OTP are required")
    
    # Get stored OTP
    stored_otp = redis_client.get(f"otp:phone:{phone}")
    
    if not stored_otp:
        raise HTTPException(status_code=400, detail="OTP not found or expired")
    
    if stored_otp != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    # OTP is valid, delete it
    redis_client.delete(f"otp:phone:{phone}")
    
    return {
        "success": True,
        "message": "Phone OTP verified successfully"
    }

@app.delete("/clear")
async def clear_otp(email: str = None, phone: str = None):
    """Clear OTP for testing purposes"""
    if email:
        redis_client.delete(f"otp:{email}")
        return {"message": f"OTP cleared for {email}"}
    elif phone:
        redis_client.delete(f"otp:phone:{phone}")
        return {"message": f"OTP cleared for {phone}"}
    else:
        raise HTTPException(status_code=400, detail="Email or phone is required")

@app.get("/status")
async def get_otp_status():
    """Get OTP service status and stored OTPs (development only)"""
    try:
        # Get all OTP keys
        email_keys = redis_client.keys("otp:*")
        phone_keys = redis_client.keys("otp:phone:*")
        
        return {
            "status": "active",
            "redis": "connected",
            "email_otps": len(email_keys),
            "phone_otps": len(phone_keys),
            "total_otps": len(email_keys) + len(phone_keys)
        }
    except Exception as e:
        return {
            "status": "error",
            "redis": "disconnected",
            "error": str(e)
        }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        redis_client.ping()
        return {"status": "healthy", "redis": "connected"}
    except:
        return {"status": "unhealthy", "redis": "disconnected"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
