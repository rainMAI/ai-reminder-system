#!/usr/bin/env python3
"""
Initialize Reminder System Database
Usage: python database/init_db.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import init_database, db


def main():
    """Initialize database"""
    print("=" * 60)
    print("Reminder Management System - Database Initialization")
    print("=" * 60)

    # Check if already initialized
    if db.is_initialized():
        print("\n⚠️  Database already exists.")
        response = input("Do you want to re-initialize? This will DELETE all existing data! (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Initialization cancelled.")
            return

        # Backup existing database
        import shutil
        from datetime import datetime
        backup_path = f"{db.DATABASE_PATH}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            shutil.copy2(db.DATABASE_PATH, backup_path)
            print(f"✅ Backup created: {backup_path}")
        except Exception as e:
            print(f"❌ Failed to create backup: {e}")
            return

        # Delete existing database
        try:
            os.remove(db.DATABASE_PATH)
            print(f"✅ Old database removed")
        except Exception as e:
            print(f"❌ Failed to remove database: {e}")
            return

    # Initialize database
    try:
        init_database()
        print("\n✅ Database initialized successfully!")
        print(f"📍 Location: {db.DATABASE_PATH}")
        print("\nNext steps:")
        print("  1. Start the web server: python web_server.py")
        print("  2. Access the web interface: http://192.140.190.183:8081/web-reminder/")
    except Exception as e:
        print(f"\n❌ Failed to initialize database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
