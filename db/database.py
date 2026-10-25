"""Small database adapter supporting PostgreSQL and a local SQLite fallback."""

import os
import sqlite3
import time
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor


DB_PATH = os.environ.get(
    "HOSPITAL_DB_PATH",
    str(Path(__file__).resolve().parent.parent / "hospital_system.db"),
)


class ExecutionResult:
    """Expose the cursor fields used by the application across both drivers."""

    def __init__(self, lastrowid=None, rowcount=0):
        self.lastrowid = lastrowid
        self.rowcount = rowcount


class Database:
    # IDs returned by inserts in the core layer, keyed by the inserted table.
    _id_columns = {
        "patients": "patient_id",
        "doctors": "doctor_id",
        "appointments": "appointment_id",
        "walk_in_queue": "queue_id",
        "users": "user_id",
        "health_records": "record_id",
        "prescriptions": "prescription_id",
        "lab_results": "lab_id",
        "bills": "bill_id",
        "payments": "payment_id",
        "insurance_policies": "policy_id",
        "report_snapshots": "snapshot_id",
        "triage_logs": "triage_id",
        "appointment_schedule_history": "history_id",
    }

    def __init__(self, database_url=None, db_path=None, retries=10, retry_delay=2):
        self.database_url = database_url if database_url is not None else os.getenv("DATABASE_URL")
        self.db_path = db_path or DB_PATH
        if self.database_url:
            self.engine = "postgres"
            self.conn = self._connect_with_retry(self.database_url, retries, retry_delay)
        else:
            self.engine = "sqlite"
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON")

        self._init_db()

    @staticmethod
    def _connect_with_retry(url, retries, delay):
        """Wait for the database service to become ready during Compose startup."""
        for attempt in range(retries):
            try:
                connection = psycopg2.connect(url)
                connection.autocommit = True
                return connection
            except psycopg2.OperationalError:
                if attempt == retries - 1:
                    raise
                print(f"PostgreSQL is not ready; retrying in {delay}s ({attempt + 1}/{retries})")
                time.sleep(delay)

    def _init_db(self):
        schema_path = Path(__file__).with_name("schema.sql")
        schema = schema_path.read_text(encoding="utf-8")
        if self.engine == "sqlite":
            self.conn.executescript(schema)
            self.conn.commit()
            self._ensure_patient_cure_columns()
            self._ensure_doctor_status_columns()
            self._ensure_user_profile_columns()
            self._ensure_appointment_columns()
            self._ensure_payment_columns()
            return

        # Keep one canonical schema usable by both drivers.
        pg_schema = schema.replace(
            "INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY"
        )
        with self.conn.cursor() as cursor:
            cursor.execute(pg_schema)
        self._ensure_patient_cure_columns()
        self._ensure_doctor_status_columns()
        self._ensure_user_profile_columns()
        self._ensure_appointment_columns()
        self._ensure_payment_columns()

    def _ensure_appointment_columns(self):
        """Add emergency classification and completion metadata to existing appointments."""
        if self.engine == "sqlite":
            columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(appointments)")}
            if "category" not in columns:
                self.conn.execute("ALTER TABLE appointments ADD COLUMN category TEXT NOT NULL DEFAULT 'routine'")
            if "completed_at" not in columns:
                self.conn.execute("ALTER TABLE appointments ADD COLUMN completed_at TIMESTAMP")
            self.conn.commit()
            return

        with self.conn.cursor() as cursor:
            cursor.execute("ALTER TABLE appointments ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'routine'")
            cursor.execute("ALTER TABLE appointments ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP")

    def _ensure_payment_columns(self):
        """Add gateway reference and status to older payment tables without losing transactions."""
        if self.engine == "sqlite":
            columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(payments)")}
            if "transaction_id" not in columns:
                self.conn.execute("ALTER TABLE payments ADD COLUMN transaction_id TEXT")
            if "status" not in columns:
                self.conn.execute("ALTER TABLE payments ADD COLUMN status TEXT NOT NULL DEFAULT 'completed'")
            self.conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_transaction_id "
                "ON payments(transaction_id) WHERE transaction_id IS NOT NULL"
            )
            self.conn.commit()
            return

        with self.conn.cursor() as cursor:
            cursor.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS transaction_id TEXT")
            cursor.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'completed'")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_transaction_id ON payments(transaction_id)")

    def _ensure_patient_cure_columns(self):
        """Apply the small additive migration to databases created before cure tracking."""
        if self.engine == "sqlite":
            columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(patients)")}
            if "is_cured" not in columns:
                self.conn.execute("ALTER TABLE patients ADD COLUMN is_cured INTEGER NOT NULL DEFAULT 0")
            if "cured_at" not in columns:
                self.conn.execute("ALTER TABLE patients ADD COLUMN cured_at TIMESTAMP")
            self.conn.commit()
            return

        with self.conn.cursor() as cursor:
            cursor.execute("ALTER TABLE patients ADD COLUMN IF NOT EXISTS is_cured INTEGER NOT NULL DEFAULT 0")
            cursor.execute("ALTER TABLE patients ADD COLUMN IF NOT EXISTS cured_at TIMESTAMP")

    def _ensure_doctor_status_columns(self):
        """Add employment status to existing doctor directories without losing history."""
        if self.engine == "sqlite":
            columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(doctors)")}
            if "employment_status" not in columns:
                self.conn.execute("ALTER TABLE doctors ADD COLUMN employment_status TEXT NOT NULL DEFAULT 'active'")
            if "status_reason" not in columns:
                self.conn.execute("ALTER TABLE doctors ADD COLUMN status_reason TEXT")
            if "status_updated_at" not in columns:
                self.conn.execute("ALTER TABLE doctors ADD COLUMN status_updated_at TIMESTAMP")
            self.conn.execute("UPDATE doctors SET status_updated_at = CURRENT_TIMESTAMP WHERE status_updated_at IS NULL")
            self.conn.commit()
            return

        with self.conn.cursor() as cursor:
            cursor.execute("ALTER TABLE doctors ADD COLUMN IF NOT EXISTS employment_status TEXT NOT NULL DEFAULT 'active'")
            cursor.execute("ALTER TABLE doctors ADD COLUMN IF NOT EXISTS status_reason TEXT")
            cursor.execute("ALTER TABLE doctors ADD COLUMN IF NOT EXISTS status_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

    def _ensure_user_profile_columns(self):
        """Add editable display names for existing login accounts."""
        if self.engine == "sqlite":
            columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(users)")}
            if "display_name" not in columns:
                self.conn.execute("ALTER TABLE users ADD COLUMN display_name TEXT NOT NULL DEFAULT ''")
            self.conn.execute(
                "UPDATE users SET display_name = CASE WHEN username = 'admin' THEN 'Dr. Sharma' ELSE username END "
                "WHERE display_name IS NULL OR display_name = ''"
            )
            self.conn.commit()
            return

        with self.conn.cursor() as cursor:
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name TEXT NOT NULL DEFAULT ''")
            cursor.execute(
                "UPDATE users SET display_name = CASE WHEN username = 'admin' THEN 'Dr. Sharma' ELSE username END "
                "WHERE display_name IS NULL OR display_name = ''"
            )

    @staticmethod
    def _postgres_query(query):
        return query.replace("?", "%s")

    def execute(self, query, params=()):
        """Execute a write and return a driver-independent result."""
        if self.engine == "sqlite":
            cursor = self.conn.execute(query, params)
            self.conn.commit()
            return cursor

        sql = self._postgres_query(query)
        insert_table = None
        if sql.lstrip().upper().startswith("INSERT INTO ") and " RETURNING " not in sql.upper():
            insert_table = sql.lstrip().split()[2].strip('"').lower()
            id_column = self._id_columns.get(insert_table)
            if id_column:
                sql = f"{sql.rstrip().rstrip(';')} RETURNING {id_column}"

        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
            lastrowid = cursor.fetchone()[0] if insert_table and cursor.description else None
            return ExecutionResult(lastrowid=lastrowid, rowcount=cursor.rowcount)

    def query(self, query, params=()):
        sql = self._postgres_query(query) if self.engine == "postgres" else query
        if self.engine == "sqlite":
            return self.conn.execute(sql, params).fetchall()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def query_one(self, query, params=()):
        results = self.query(query, params)
        return results[0] if results else None

    def close(self):
        self.conn.close()


db = Database()
