from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os

# Import the defensive middleware we just built
from middleware.firewall import VelocityFirewall

app = Flask(__name__)
# Enable CORS to allow your GitHub Pages frontend to talk to this local Termux server
CORS(app)

# Initialize the Firewall instance
gatekeeper = VelocityFirewall()
DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'tradehub_core.db')

@app.route('/api/health', methods=['GET'])
def system_health():
    """
    A simple diagnostic endpoint. 
    The frontend will ping this to ensure the Termux engine is online and the tunnel is active.
    """
    return jsonify({"status": "online", "message": "TradeHub Engine is active."}), 200

@app.route('/api/submit_listing', methods=['POST'])
def submit_listing():
    """
    The main ingestion route for new classifieds or freelance gigs.
    """
    try:
        # Extract the JSON payload from the incoming web request
        data = request.get_json()
        
        # 1. Identity Extraction
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({"error": "Unauthorized", "message": "User ID missing."}), 401

        # 2. Firewall Interception
        # The script halts here and checks the user's velocity against the 24-hour limit
        clearance = gatekeeper.check_rate_limit(user_id)
        
        if not clearance['allowed']:
            return jsonify({
                "error": "Rate Limit Exceeded",
                "message": f"Velocity Firewall block. Please wait {clearance['remaining_seconds']} seconds.",
                "remaining_seconds": clearance['remaining_seconds']
            }), 429

        # 3. Defensive Sanitization
        # Strip malicious scripts or broken HTML from the user inputs
        clean_title = gatekeeper.sanitize_input(data.get('title', ''))
        clean_desc = gatekeeper.sanitize_input(data.get('description', ''))
        clean_category = gatekeeper.sanitize_input(data.get('category', 'General'))
        clean_image_url = gatekeeper.sanitize_input(data.get('image_url', ''))
        
        # Ensure price is a valid number
        try:
            price = float(data.get('price', 0.0))
        except ValueError:
            price = 0.0

        # 4. Database Commitment
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO listings (user_id, title, description, price, category, image_url)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, clean_title, clean_desc, price, clean_category, clean_image_url))
        
        conn.commit()
        conn.close()

        # 5. Log the Action
        # Record this timestamp so the firewall knows to block the user for the next 24 hours
        gatekeeper.log_submission(user_id)

        return jsonify({
            "status": "success", 
            "message": "Listing approved and published to the TradeHub grid."
        }), 201

    except Exception as e:
        return jsonify({"error": "Server Error", "message": str(e)}), 500
@app.route('/api/user_status', methods=['POST'])
def user_status():
    """
    Checks if a user has an active listing and triggers the daily engagement prompt.
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if the user currently has any active items on the market
        cursor.execute("SELECT title FROM listings WHERE user_id = ?", (user_id,))
        active_listing = cursor.fetchone()
        conn.close()
        
        # If they have an active listing, send the prompt to the frontend UI
        if active_listing:
            return jsonify({
                "prompt_active": True,
                "message": f"Did you sell '{active_listing[0]}' yet? Remove this ad to reset your daily limit and post a new ad!"
            }), 200
            
        return jsonify({"prompt_active": False}), 200

    except Exception as e:
        return jsonify({"error": "Server Error", "message": str(e)}), 500

if __name__ == '__main__':
    # Binds the server to all network interfaces on port 5000
    print("[SYSTEM] Booting TradeHub API Gateway...")
    print("[SYSTEM] Velocity Firewall Active. Waiting for web traffic...")
    app.run(host='0.0.0.0', port=5000, debug=False)

