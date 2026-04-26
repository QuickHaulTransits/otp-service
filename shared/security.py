import bcrypt
import hashlib
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from shared.config import settings

ALGORITHM = "HS256"
security_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')[:72]
    pwd_hash = hashlib.sha256(password_bytes).digest()
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_hash, salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode('utf-8')[:72]
    pwd_hash = hashlib.sha256(password_bytes).digest()
    return bcrypt.checkpw(pwd_hash, hashed_password.encode('utf-8'))


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    try:
        # Debug logging
        with open("security_debug.log", "a") as f:
            f.write(f"{datetime.now()}: Decoding token with key starting {settings.secret_key[:4]}...\n")
        
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload.get("sub")
    except Exception as e:
        with open("security_debug.log", "a") as f:
            f.write(f"{datetime.now()}: Decode failed: {str(e)}\n")
        return None


async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)) -> str:
    token = credentials.credentials
    user_id = decode_access_token(token)
    if not user_id:
        with open("security_debug.log", "a") as f:
            f.write(f"{datetime.now()}: Returning 401 for token: {token[:10]}...\n")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user_id
