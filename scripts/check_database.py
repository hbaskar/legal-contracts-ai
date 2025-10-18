
"""
Check SQLite database contents and structure
"""
import sqlite3
import os

def check_database():
    db_path = './data/metadata.db'
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print('Tables in database:', [table[0] for table in tables])
        
        # Check each table for data
        for table in tables:
            table_name = table[0]
            if table_name != 'sqlite_sequence':
                cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
                count = cursor.fetchone()[0]
                print(f'{table_name}: {count} records')
                
                if count > 0:
                    if table_name == 'file_metadata':
                        cursor.execute(f'SELECT id, filename, upload_timestamp FROM {table_name} LIMIT 3')
                        rows = cursor.fetchall()
                        for row in rows:
                            print(f'  File ID {row[0]}: {row[1]} uploaded at {row[2]}')
                    elif table_name == 'document_chunks':
                        cursor.execute(f'SELECT file_id, chunk_method, COUNT(*) FROM {table_name} GROUP BY file_id, chunk_method')
                        rows = cursor.fetchall()
                        for row in rows:
                            print(f'  File {row[0]} has {row[2]} chunks with method: {row[1]}')
        
        conn.close()
    else:
        print('Database file not found at:', db_path)

if __name__ == "__main__":
    check_database()