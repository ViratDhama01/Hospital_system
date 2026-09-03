import sqlite3
import os

DB_PATH = os.environ.get("HOSPITAL_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "hospital_system.db"))

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row # Return results as dictionary-like objects
        self._init_db()

    def _init_db(self):
        """Initialize the database with the schema."""
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        with open(schema_path, 'r') as f:
            schema = f.read()
            self.conn.executescript(schema)
            self.conn.commit()

    def execute(self, query, params=()):
        """Execute a query that doesn't return results (INSERT, UPDATE, DELETE)."""
        cursor = self.conn.execute(query, params)
        self.conn.commit()
        return cursor

    def query(self, query, params=()):
        """Execute a query that returns results (SELECT)."""
        cursor = self.conn.execute(query, params)
        return cursor.fetchall()

    def query_one(self, query, params=()):
        """Execute a query that returns a single result."""
        cursor = self.conn.execute(query, params)
        return cursor.fetchone()

    def close(self):
        self.conn.close()

# Singleton instance for the app
db = Database()
