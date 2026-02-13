"""
Database connection management for Reminder System
"""
import os
import sqlite3
import threading
from contextlib import contextmanager
from typing import Optional

# Database path
DATABASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(DATABASE_DIR, 'face_analysis.db')


class DatabaseConnection:
    """Thread-safe database connection manager using connection pooling"""

    _instance = None
    _lock = threading.Lock()
    _local = threading.local()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize database directory"""
        os.makedirs(DATABASE_DIR, exist_ok=True)

    @contextmanager
    def get_connection(self):
        """
        Get a thread-local database connection

        Usage:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM devices")
        """
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                DATABASE_PATH,
                check_same_thread=False,
                timeout=30.0
            )
            # Enable foreign keys
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            # Use WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode = WAL")

        conn = self._local.connection
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            # Don't close connection, keep it in thread-local storage
            pass

    def close(self):
        """Close the thread-local connection"""
        if hasattr(self._local, 'connection') and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None

    def execute(self, query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False):
        """
        Execute a query and return results

        Args:
            query: SQL query string
            params: Query parameters tuple
            fetch_one: Return single row
            fetch_all: Return all rows

        Returns:
            Query result (single row, list of rows, or rowcount for INSERT/UPDATE/DELETE)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                conn.commit()
                return cursor.rowcount

    def execute_script(self, script: str):
        """
        Execute a multi-line SQL script

        Args:
            script: SQL script string
        """
        with self.get_connection() as conn:
            conn.executescript(script)
            conn.commit()

    def init_database(self):
        """Initialize database with schema"""
        schema_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'schema.sql'
        )

        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            self.execute_script(schema_sql)
            print(f"✅ Database initialized: {DATABASE_PATH}")
        else:
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

    def is_initialized(self) -> bool:
        """Check if database is already initialized"""
        if not os.path.exists(DATABASE_PATH):
            return False

        try:
            result = self.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='devices'",
                fetch_one=True
            )
            return result is not None
        except Exception:
            return False


# Global database instance
db = DatabaseConnection()


def get_db() -> DatabaseConnection:
    """Get the global database instance"""
    return db


def init_database():
    """Initialize the database"""
    if not db.is_initialized():
        db.init_database()
    else:
        print(f"✅ Database already initialized: {DATABASE_PATH}")


if __name__ == "__main__":
    # Test database connection
    print(f"Database path: {DATABASE_PATH}")
    print(f"Database exists: {os.path.exists(DATABASE_PATH)}")
    print(f"Database initialized: {db.is_initialized()}")

    # Initialize if not already done
    init_database()

    # Test query
    result = db.execute("SELECT COUNT(*) FROM devices", fetch_one=True)
    print(f"Devices count: {result[0] if result else 0}")
