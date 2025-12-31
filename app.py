from flask import Flask, render_template
import serial
import threading
import time
from datetime import datetime
app = Flask(__name__)
# Connexion série
try:
    ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
    print("✅ Serial connected on /dev/ttyUSB0")
except Exception as e:
    print("❌ Serial connection failed:", e)
    ser = None
# Données partagées
latest_data = {
    "temperature": None,
    "humidity": None,
    "timestamp": None
}
@app.route("/")
def index():
    return render_template("index.html", **latest_data)
# Thread pour lecture toutes les  heures
def publish_every_12_hours():
    while True:
        try:
            if ser:
                line = ser.readline().decode('utf-8').strip()
                print(f"[{datetime.now()}] Serial raw: {line}")
                if line:
                    temp, hum = map(float, line.split(','))
                    latest_data["temperature"] = temp
                    latest_data["humidity"] = hum
                    latest_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    # Enregistrer dans un fichier
                    with open("dht_data_log.txt", "a") as f:
                        f.write(f"{latest_data['timestamp']}: Temp={temp}°C, Hum={hum}%\n")
        except Exception as e:
            print(f"⚠️ Error reading/publishing data: {e}")
        # Temporisation : 1/2 heures
        time.sleep(60 )
# Démarrer le thread de fond
threading.Thread(target=publish_every_12_hours, daemon=True).start()
# Lancer le serveur Flask
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
