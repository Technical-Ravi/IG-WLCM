import os
import time
import threading
from flask import Flask, request, jsonify, render_template
from instagrapi import Client

# Flask app setup (HTML file must be in the 'templates' folder)
app = Flask(__name__, template_folder='templates')

# Global bot state
bot_state = {
    "bot_running": False,
    "token_ready": False,
    "start_time": 0,
    "logs": ["Bot is ready! Set token to start monitoring..."],
    "welcomes": 0,
    "session_token": None,
    "cl": None
}

# Function to update logs safely
def log_msg(msg):
    timestamp = time.strftime("%H:%M:%S")
    bot_state["logs"].append(f"[{timestamp}] {msg}")
    # Keep only the latest 50 logs to save memory
    if len(bot_state["logs"]) > 50:
        bot_state["logs"].pop(0)

@app.route('/')
def index():
    # Renders your index.html page
    return render_template('index.html')

@app.route('/set_token', methods=['POST'])
def set_token():
    token = request.form.get('token')
    if not token:
        return jsonify({"error": "Token missing"}), 400
    
    bot_state["session_token"] = token
    bot_state["token_ready"] = True
    log_msg("✅ Session Token saved successfully.")
    return jsonify({"message": "Token set"})

@app.route('/start', methods=['POST'])
def start_bot():
    if not bot_state["token_ready"]:
        return jsonify({"error": "Please set the token first!"}), 400
    if bot_state["bot_running"]:
        return jsonify({"error": "Bot is already running!"}), 400

    # Fetch configuration from the HTML form
    config = {
        "welcome_msg": request.form.get('welcome', 'Welcome @username!'),
        "group_ids": request.form.get('group_ids', ''),
        "delay": int(request.form.get('delay', 2)),  # 2 seconds delay
        "use_custom_name": request.form.get('use_custom_name', 'yes')
    }

    bot_state["bot_running"] = True
    bot_state["start_time"] = time.time()
    
    # Start bot in a background thread so it doesn't freeze the web server
    threading.Thread(target=run_bot_loop, args=(config,), daemon=True).start()
    
    return jsonify({"message": "✅ Bot started successfully!"})

@app.route('/stop', methods=['POST'])
def stop_bot():
    bot_state["bot_running"] = False
    log_msg("🔴 Bot stopped.")
    return jsonify({"message": "Bot stopped!"})

@app.route('/logs', methods=['GET'])
def get_logs():
    return jsonify({
        "logs": bot_state["logs"],
        "welcomes": bot_state["welcomes"]
    })

@app.route('/status', methods=['GET'])
def get_status():
    uptime = time.time() - bot_state["start_time"] if bot_state["bot_running"] else 0
    return jsonify({
        "token_ready": bot_state["token_ready"],
        "bot_running": bot_state["bot_running"],
        "uptime": uptime
    })

# Core bot logic (Connecting to Instagram)
def run_bot_loop(config):
    cl = Client()
    try:
        log_msg("🔄 Connecting to Instagram servers...")
        # Login via Session ID (Token)
        cl.login_by_sessionid(bot_state["session_token"])
        log_msg("✅ Instagram login successful!")
    except Exception as e:
        log_msg(f"❌ Login Error: {str(e)}")
        bot_state["bot_running"] = False
        return

    group_ids = [g.strip() for g in config["group_ids"].split(',') if g.strip()]
    if not group_ids:
        log_msg("⚠️ No Group IDs provided. Please enter Group IDs.")

    log_msg(f"🚀 Monitoring started. Checking every {config['delay']} seconds...")
    
    # Main bot loop
    while bot_state["bot_running"]:
        try:
            # Logic to check for new members goes here
            # Apply delay to avoid getting blocked by Instagram
            time.sleep(config["delay"])
            
            # Example: cl.direct_send() would be used here to send the actual message
            # log_msg("Checked - No new members found")

        except Exception as e:
            log_msg(f"⚠️ Network Error: {str(e)}")
            time.sleep(5)  # Wait 5 seconds on error

if __name__ == '__main__':
    # Port 5000 is typically used on Render
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
