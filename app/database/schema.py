import sqlite3
import os

# Establishes a permanent, secure relative path for the database file
DB_PATH = os.path.join(os.path.dirname(__file__), 'tradehub_core.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. CORE USER TABLE: Tracks registration and security clearance tiers
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            phone_number TEXT UNIQUE,
            badge_tier TEXT DEFAULT 'WHITE',
            is_premium INTEGER DEFAULT 0
        )
    ''')
    
    # 2. VELOCITY LOG: Immutable log tracking submission timestamps down to the second
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listing_velocity_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    # 3. LEAN LISTING TABLE: Strictly maps lightweight text strings (No binary image bloat)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            title TEXT,
            description TEXT,
            price REAL,
            category TEXT,
            image_url TEXT,   -- Holds the lightweight external CDN URL string
            catalog_url TEXT, -- Pointer for freelance PDF/image portfolios
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("[SUCCESS] TradeHub Immutable Database Shell Initialized Natively.")

