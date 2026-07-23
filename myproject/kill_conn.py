import os
import psycopg2
from dotenv import load_dotenv

def kill_connections():
    load_dotenv()
    db_url = os.environ.get('DATABASE_URL')
    print(f"Connecting to {db_url}")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()
    
    cur.execute("""
        SELECT pg_terminate_backend(pid) 
        FROM pg_stat_activity 
        WHERE datname = 'neondb' 
          AND pid <> pg_backend_pid();
    """)
    print("Killed connections!")
    cur.close()
    conn.close()

if __name__ == '__main__':
    kill_connections()
