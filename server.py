from flask import Flask
import logging
import threading
from oddeven import main  # This imports and reuses your existing code

app = Flask(__name__)

@app.route("/")
def index():
    return "✅ CSGO Betting Bot is online."

@app.route("/run-bot")
def run_bot():
    logging.info("🎯 Bot triggered from web!")
    threading.Thread(target=main).start()  # Runs in background to avoid timeout
    return "Bot started! ✅"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)  # Required for Render
