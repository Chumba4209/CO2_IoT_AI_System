from collections import deque
from datetime import datetime
from pathlib import Path
import csv
import json
import time

import joblib
import pandas as pd
import smbus2

SLAVE_ADDR = 0x11
READ_COMMAND = 0x01
SAMPLE_SECONDS = 60
HISTORY_SIZE = 16

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BASE_DIR / "models" / "co2_random_forest.pkl"
LOG_PATH = BASE_DIR / "data" / "co2_predictions.csv"
LATEST_PATH = BASE_DIR / "data" / "latest_prediction.json"

FEATURES = [
    "co2_ppm",
    "co2_lag_5",
    "co2_lag_15",
    "co2_change_5",
    "co2_change_15",
    "hour",
    "minute",
    "day_of_week",
]

history = deque(maxlen=HISTORY_SIZE)


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found: {MODEL_PATH}\n"
            "Copy co2_random_forest.pkl into the models folder."
        )
    return joblib.load(MODEL_PATH)


def read_co2():
    try:
        with smbus2.SMBus(1) as bus:
            write = smbus2.i2c_msg.write(SLAVE_ADDR, [READ_COMMAND])
            read = smbus2.i2c_msg.read(SLAVE_ADDR, 2)
            bus.i2c_rdwr(write, read)
            data = list(read)

        return (data[0] << 8) | data[1]
    except Exception as exc:
        print(f"[I2C] {exc}")
        return None


def valid_reading(co2):
    return co2 is not None and co2 not in (0, 65535)


def build_features(timestamp):
    current = history[-1]
    lag_5 = history[-6]
    lag_15 = history[-16]

    values = {
        "co2_ppm": current,
        "co2_lag_5": lag_5,
        "co2_lag_15": lag_15,
        "co2_change_5": current - lag_5,
        "co2_change_15": current - lag_15,
        "hour": timestamp.hour,
        "minute": timestamp.minute,
        "day_of_week": timestamp.weekday(),
    }

    return pd.DataFrame([values], columns=FEATURES)


def get_status(ppm):
    if ppm < 800:
        return "Good"
    if ppm < 1000:
        return "Moderate"
    return "High"


def save_result(timestamp, current, predicted):
    result = {
        "timestamp": timestamp.isoformat(),
        "current_co2_ppm": int(current),
        "predicted_co2_ppm_15min": round(float(predicted), 2),
        "status": get_status(predicted),
    }

    LATEST_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")

    new_file = not LOG_PATH.exists()
    with LOG_PATH.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=result.keys())
        if new_file:
            writer.writeheader()
        writer.writerow(result)

    return result


def main():
    model = load_model()

    print("PAS CO2 AI predictor started")

    while True:
        start = time.monotonic()
        timestamp = datetime.now()
        co2 = read_co2()

        if valid_reading(co2):
            history.append(co2)
            print(
                f"[{timestamp:%H:%M:%S}] PAS CO2: {co2} ppm "
                f"| History: {len(history)}/{HISTORY_SIZE}"
            )

            if len(history) == HISTORY_SIZE:
                features = build_features(timestamp)
                predicted = model.predict(features)[0]
                result = save_result(timestamp, co2, predicted)

                print(
                    f"[AI] Current: {result['current_co2_ppm']} ppm "
                    f"| +15 min: {result['predicted_co2_ppm_15min']} ppm "
                    f"| Status: {result['status']}"
                )
            else:
                print("[AI] Collecting one-minute history")
        else:
            print(f"[{timestamp:%H:%M:%S}] Invalid PAS CO2 reading: {co2}")

        elapsed = time.monotonic() - start
        time.sleep(max(0, SAMPLE_SECONDS - elapsed))


if __name__ == "__main__":
    main()
