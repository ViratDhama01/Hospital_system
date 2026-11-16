from datetime import datetime, timedelta, timezone
from uuid import uuid4
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
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)
        except (TypeError, ValueError):
            return False

    def get_password_hash(self, password):
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def create_access_token(self, data: dict):
        session_id = uuid4().hex
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        db.execute("DELETE FROM auth_sessions WHERE expires_at <= CURRENT_TIMESTAMP")
        db.execute(
            "INSERT INTO auth_sessions (session_id, user_id, expires_at) VALUES (?, ?, ?)",
            (session_id, data["user_id"], expire.replace(tzinfo=None).isoformat()),
        )
        return jwt.encode({"jti": session_id, "exp": int(expire.timestamp())}, SECRET_KEY, algorithm=ALGORITHM)

    def decode_access_token(self, token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            session_id = payload.get("jti")
        except JWTError:
            return None
        if not session_id:
            return None
        user = db.query_one(
            "SELECT u.user_id, u.username, u.display_name, u.role, u.doctor_id, s.session_id "
            "FROM auth_sessions s JOIN users u ON u.user_id = s.user_id LEFT JOIN doctors d ON d.doctor_id = u.doctor_id "
            "WHERE s.session_id = ? AND (u.doctor_id IS NULL OR d.employment_status = 'active')",
            (session_id,),
        )
        return dict(user) if user else None

    def revoke_session(self, session_id):
        db.execute("DELETE FROM auth_sessions WHERE session_id = ?", (session_id,))

    def create_user(self, username, password, role="receptionist", display_name=None, doctor_id=None):
        hashed_pw = self.get_password_hash(password)
        query = "INSERT INTO users (username, hashed_password, role, display_name, doctor_id) VALUES (?, ?, ?, ?, ?)"
        cursor = db.execute(query, (username, hashed_pw, role, display_name or username, doctor_id))
        return cursor.lastrowid

    def authenticate_user(self, username, password):
        row = db.query_one(
            "SELECT u.* FROM users u LEFT JOIN doctors d ON d.doctor_id = u.doctor_id "
            "WHERE u.username = ? AND (u.doctor_id IS NULL OR d.employment_status = 'active')",
            (username.strip(),),
        )
        if not row:
            return None

        if self.verify_password(password, row['hashed_password']):
            return {
                "user_id": row['user_id'],
                "username": row['username'],
                "role": row['role'],
                "display_name": row['display_name'],
                "doctor_id": row['doctor_id'],
            }
        return None

auth_manager = AuthManager()
