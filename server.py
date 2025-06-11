import logging
import threading
from flask import Flask
from oddeven import main

app = Flask(__name__)

@app.route("/")
def index():
    return "✅ CSGO Betting Bot is online."

@app.route("/run-bot")
def run_bot():
    logging.info("🔔 Bot triggered by web hit")
    threading.Thread(target=main).start()  # Runs in background to avoid timeout
    return "🎯 Bot started — check logs on Render"
