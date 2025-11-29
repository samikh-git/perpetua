import sqlite3
from pathlib import Path

# Get the directory where this script is located
script_dir = Path(__file__).parent
# Connect to database.db in the same directory as this script
URI = script_dir / 'database.db'

class DBManager:
    def __init__(self, URI): 
        self.conn = sqlite3.connect(URI)
        self.cur = self.conn.cursor()

    def create_doc_table(self):
        self.cur.execute(""" 
            CREATE TABLE docs(
            id TEXT PRIMARY KEY,
            filepath TEXT,
            file_hash TEXT, 
            chunk_count INT,
            last_indexed TEXT
            ) 
        """)
        self.cur.execute("CREATE INDEX IF NOT EXISTS idx_filepath ON docs(filepath)")
        self.cur.execute("CREATE INDEX IF NOT EXISTS idx_file_hash ON docs(file_hash)")
        self.conn.commit()

    def drop_doc_table(self):
        """Drop the docs table if it exists."""
        self.cur.execute("DROP TABLE IF EXISTS docs")
        self.conn.commit()
        print("Table 'docs' dropped successfully")
    
    def reset(self):
        self.cur.execute("DELETE FROM docs")
        self.conn.commit()
        print(f"Deleted {self.cur.rowcount} rows")
