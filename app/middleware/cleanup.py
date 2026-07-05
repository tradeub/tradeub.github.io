import sqlite3
import datetime
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'tradehub_core.db')

def enforce_expiry():
    """
    Sweeps the TradeHub database and purges any listing older than 21 days.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Calculate the exact timestamp 21 days ago
        cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=21)).strftime("%Y-%m-%d %H:%M:%S")
        
        # Delete expired listings permanently to keep the grid fresh
        cursor.execute("DELETE FROM listings WHERE timestamp < ?", (cutoff_date,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        print(f"[SYSTEM] Expiry Sweep Complete: {deleted_count} dead listings purged from the grid.")
        
    except Exception as e:
        print(f"[ERROR] Sweep failed: {str(e)}")
    finally:
        conn.close()

if __name__ == '__main__':
    enforce_expiry()

