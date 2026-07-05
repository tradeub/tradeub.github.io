import sqlite3
import datetime
import os
import re

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'tradehub_core.db')

class VelocityFirewall:
    def __init__(self):
        # The unyielding 24-hour baseline rate limit for free accounts
        self.rate_limit_hours = 24

    def sanitize_input(self, text_input):
        """
        Defensive Input Sanitization Layer
        Strips dangerous control tokens and HTML elements to neutralize script execution attempts.
        """
        if not text_input:
            return ""
        # Strip out direct inline script blocks comprehensively
        clean = re.sub(r'<script.*?>.*?</script>', '', text_input, flags=re.IGNORECASE)
        # Remove markdown/HTML bracket anchors to normalize fields to pure text strings
        clean = re.sub(r'<[^>]*>', '', clean)
        return clean.strip()

    def check_rate_limit(self, user_id):
        """
        Calculates user velocity metrics using strict server-side datetime evaluation.
        Uses exclusively parameterized variables to completely drop the risk of SQL injection.
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # Check profile data for existing premium or whitelist flags
            cursor.execute("SELECT is_premium, badge_tier FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                # If a new user encounters the firewall, automatically provision a baseline White account
                cursor.execute("INSERT INTO users (user_id, badge_tier, is_premium) VALUES (?, 'WHITE', 0)", (user_id,))
                conn.commit()
                is_premium = 0
            else:
                is_premium = user[0]
            
            # Premium/Whitelisted accounts immediately clear the firewall gate
            if is_premium == 1:
                return {"allowed": True, "remaining_seconds": 0}
            
            # Query log for the user's most recent entry timestamp
            cursor.execute(
                "SELECT timestamp FROM listing_velocity_log WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1",
                (user_id,)
            )
            last_post = cursor.fetchone()
            
            if not last_post:
                return {"allowed": True, "remaining_seconds": 0}
            
            # Parse the timestamp string cleanly to calculate elapsed time delta
            last_post_time = datetime.datetime.strptime(last_post[0], "%Y-%m-%d %H:%M:%S")
            time_elapsed = datetime.datetime.utcnow() - last_post_time
            limit_duration = datetime.timedelta(hours=self.rate_limit_hours)
            
            if time_elapsed < limit_duration:
                remaining_delta = limit_duration - time_elapsed
                return {
                    "allowed": False, 
                    "remaining_seconds": int(remaining_delta.total_seconds())
                }
            
            return {"allowed": True, "remaining_seconds": 0}
            
        finally:
            conn.close()

    def log_submission(self, user_id):
        """
        Commits an active tracking timestamp entry. Enforces standard system utilization tracking metrics.
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            current_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO listing_velocity_log (user_id, timestamp) VALUES (?, ?)",
                (user_id, current_utc)
            )
            conn.commit()
        finally:
            conn.close()

