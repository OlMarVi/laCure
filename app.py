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
DATA_FILE = "docs/data.json"   # mesures du jour
STATS_FILE = "docs/stats.json" # tendances annuelles
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
    print(f"✅ Serial connecté sur {SERIAL_PORT}")
except Exception as e:
    print("❌ Connexion série échouée:", e)
    ser = None

# ==============================
# Dernière date pour vérifier minuit
# ==============================
last_date_checked = datetime.now().date()

# ==============================
# Fonctions JSON / stats
# ==============================
def calculate_daily_stats(data):
    if not data:
        return None
    temps = [d['temperature'] for d in data]
    hums = [d['humidity'] for d in data]
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "temp_min": round(min(temps), 2),
        "temp_max": round(max(temps), 2),
        "temp_avg": round(sum(temps)/len(temps), 2),
        "hum_min": round(min(hums), 2),
        "hum_max": round(max(hums), 2),
        "hum_avg": round(sum(hums)/len(hums), 2)
    }

def update_stats_file(daily_stats):
    os.makedirs("docs", exist_ok=True)
    try:
        with open(STATS_FILE, "r") as f:
            stats = json.load(f)
    except:
        stats = []

    stats.append(daily_stats)
    stats = stats[-365:]  # garder max 1 an
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)

    print("✅ stats.json mis à jour:", daily_stats)

def push_to_github():
    try:
        subprocess.run(["git", "add", "docs/data.json", "docs/stats.json"], cwd=REPO_DIR, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Update data & stats {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"],
            cwd=REPO_DIR,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        subprocess.run(["git", "push", "origin", "main"], cwd=REPO_DIR, check=True)
        print("🚀 Push vers GitHub réussi")
    except subprocess.CalledProcessError:
        pass  # aucun changement à pousser

# ==============================
# Thread de lecture série + stats
# ==============================
def read_serial_loop():
    global last_date_checked
    while True:
        try:
            if ser:
                line = ser.readline().decode("utf-8").strip()
                if line:
                    temp, hum = map(float, line.split(","))
                    now = datetime.now()

                    # Vérifier changement de jour
                    if now.date() != last_date_checked:
                        # Calcul stats journalières
                        try:
                            with open(DATA_FILE, "r") as f:
                                daily_data = json.load(f)
                        except:
                            daily_data = []

                        stats = calculate_daily_stats(daily_data)
                        if stats:
                            update_stats_file(stats)

                        # Vider le data.json pour le nouveau jour
                        with open(DATA_FILE, "w") as f:
                            json.dump([], f)
                        last_date_checked = now.date()
                        print(f"🕛 Nouveau jour : data.json vidé")

                    # Ajouter la nouvelle mesure au jour courant
                    latest_entry = {
                        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                        "temperature": round(temp,2),
                        "humidity": round(hum,2)
                    }

                    try:
                        with open(DATA_FILE, "r") as f:
                            data = json.load(f)
                    except:
                        data = []

                    data.append(latest_entry)
                    with open(DATA_FILE, "w") as f:
                        json.dump(data, f, indent=2)

                    print("📊 Mesure ajoutée :", latest_entry)

                    # Push GitHub
                    push_to_github()

        except Exception as e:
            print("⚠️ Erreur :", e)

        time.sleep(INTERVAL_SECONDS)

# ==============================
# Lancement
# ==============================
if __name__ == "__main__":
    print("🚀 Lancement du thread capteur + stats")
    threading.Thread(target=read_serial_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)
