from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from db.database import db

import os

# Configuration
SECRET_KEY = os.environ.get("HOSPITAL_SECRET_KEY", "dev-secret-key-do-not-use-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

class AuthManager:
    def verify_password(self, plain_password, hashed_password):
        # hashed_password from DB is bytes or string
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode('utf-8')
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)

    def get_password_hash(self, password):
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def create_access_token(self, data: dict):
        to_encode = data.copy()
        # Use timezone-aware UTC so .timestamp() gives the correct Unix epoch
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": int(expire.timestamp())})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    def decode_access_token(self, token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            # Payload contains 'username', not 'sub'
            return payload if payload.get("username") else None
        except JWTError:
            return None

    def create_user(self, username, password, role="receptionist", display_name=None):
        hashed_pw = self.get_password_hash(password)
        query = "INSERT INTO users (username, hashed_password, role, display_name) VALUES (?, ?, ?, ?)"
        cursor = db.execute(query, (username, hashed_pw, role, display_name or username))
        return cursor.lastrowid

    def authenticate_user(self, username, password):
        row = db.query_one("SELECT * FROM users WHERE username = ?", (username,))
        if not row:
            return None

        if self.verify_password(password, row['hashed_password']):
            return {
                "user_id": row['user_id'],
                "username": row['username'],
                "role": row['role'],
                "display_name": row['display_name']
            }
        return None

auth_manager = AuthManager()
