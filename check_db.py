#!/usr/bin/env python3
import sqlite3
import os

db_path = './data/metadata.db'

if os.path.exists(db_path):
    print(f"Database exists at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Tables: {tables}")
    
    # Check each table for records
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count} records")
        
        # Show first few records if any exist
        if count > 0:
            cursor.execute(f"SELECT * FROM {table} LIMIT 3")
            rows = cursor.fetchall()
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            print(f"    Columns: {columns}")
            for i, row in enumerate(rows):
                print(f"    Record {i+1}: {dict(zip(columns, row))}")
    
    conn.close()
else:
    print(f"Database does not exist at: {db_path}")