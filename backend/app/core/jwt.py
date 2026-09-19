from datetime import datetime, timedelta
from jose import jwt, JWTError
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY=os.getenv("JWT_SECRET_KEY")
ALGORITHM=os.getenv("JWT_ALGORITHM")
EXPIRE_MINUTES=int(os.getenv("JWT_EXPIRE_MINUTES",60))

def create_access_token(user_id: int)->str:
    expire_time=datetime.utcnow()+timedelta(minutes=EXPIRE_MINUTES)
    payload={
        "sub":str(user_id),
        "exp":expire_time
    }
    token=jwt.encode(payload,SECRET_KEY,algorithm=ALGORITHM)
    return token

def decode_access_token(token: str):
    try:
        payload=jwt.decode(token,SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str=payload.get("sub")
        return user_id
    except JWTError:
        return None
    