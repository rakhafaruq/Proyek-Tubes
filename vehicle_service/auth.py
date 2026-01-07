import os
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
import bcrypt

# Konfigurasi Keamanan
SECRET_KEY = os.getenv("SECRET_KEY", "rahasia_dapur_kelompok_a_super_secure")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def verify_password(plain_password, hashed_password):
    """Cek apakah password inputan user cocok dengan hash di DB"""
    # bcrypt membutuhkan input berupa BYTES, bukan String.
    # Jadi kita perlu melakukan .encode('utf-8')
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False

def get_password_hash(password):
    """Ubah password teks biasa jadi hash acak"""
    # 1. Ubah password ke bytes
    pwd_bytes = password.encode('utf-8')
    # 2. Generate salt
    salt = bcrypt.gensalt()
    # 3. Hash passwordnya
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    # 4. Kembalikan sebagai STRING agar bisa disimpan di Database
    return hashed.decode('utf-8')

def create_access_token(data: dict):
    to_encode = data.copy()
    # Menggunakan timezone.utc agar kompatibel dengan Python modern
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None