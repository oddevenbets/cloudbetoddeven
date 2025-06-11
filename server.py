import logging
import threading
from flask import Flask
from oddeven import main

# Optional: log to console on Render
logging.basicConfig(level=logging.INFO, format="%(message)s")

app = Flask(__name__)

@app.route("/")
def index():
    return "✅ CSGO Betting Bot is online."

@app.route("/run-bot")
def run_bot():
    logging.info("🔔 Bot triggered by web hit")
    threading.Thread(target=main).start()  # Runs in background to avoid blocking
    return "🎯 Bot started — check logs on Render"

# Required to run on Render or locally
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
