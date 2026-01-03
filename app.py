from flask import Flask
import serial
import threading
import time
from datetime import datetime
import json
import os
import subprocess

# ==============================
# Configuration
# ==============================
SERIAL_PORT = "/dev/ttyUSB0"
BAUDRATE = 9600
INTERVAL_SECONDS = 60 * 30   # toutes les 30 minutes
DATA_FILE = "docs/data.json"
REPO_DIR = "/home/pi/web-server"   # change selon ton chemin

# ==============================
# Flask (optionnel – local)
# ==============================
app = Flask(__name__, static_folder="docs", static_url_path="")

@app.route("/")
def index():
    return app.send_static_file("index.html")


# ==============================
# Connexion série
# ==============================
try:
    ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=2)
    print(f"✅ Serial connected on {SERIAL_PORT}")
except Exception as e:
    print("❌ Serial connection failed:", e)
    ser = None

# ==============================
# Données en mémoire
# ==============================
latest_data = {
    "temperature": None,
    "humidity": None,
    "timestamp": None
}

# ==============================
# Fonction écriture JSON
# ==============================
def update_json(temp, hum):
    os.makedirs("docs", exist_ok=True)

    # Lire les données existantes
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
    except:
        data = []

    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "temperature": round(temp,2),
        "humidity": round(hum,2)
    }

    data.append(entry)
    data = data[-1000:]  # garder les 1000 dernières mesures

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print("✅ data.json mis à jour:", entry)
    return True

# ==============================
# Fonction push Git automatique
# ==============================
def push_to_github():
    try:
        subprocess.run(["git", "add", "docs/data.json"], cwd=REPO_DIR, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Update data.json {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"],
            cwd=REPO_DIR,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        subprocess.run(["git", "push", "origin", "main"], cwd=REPO_DIR, check=True)
        print("🚀 Push vers GitHub réussi")
    except subprocess.CalledProcessError as e:
        # Pas d'erreur si aucun changement
        pass

# ==============================
# Thread de lecture série + push
# ==============================
def read_serial_loop():
    while True:
        try:
            if ser:
                line = ser.readline().decode("utf-8").strip()
                print(f"[{datetime.now()}] Serial raw:", line)

                if line:
                    temp, hum = map(float, line.split(","))
                    latest_data["temperature"] = temp
                    latest_data["humidity"] = hum
                    latest_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    update_json(temp, hum)
                    push_to_github()

        except Exception as e:
            print("⚠️ Error:", e)

        time.sleep(INTERVAL_SECONDS)

# ==============================
# Lancement
# ==============================
if __name__ == "__main__":
    print("🚀 Lancement du thread capteur + push")
    threading.Thread(target=read_serial_loop, daemon=True).start()

    # Flask uniquement pour debug local
    app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)


