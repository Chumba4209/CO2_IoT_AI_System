# CO2 IoT AI Predictive Monitoring System

An end-to-end IoT and machine learning project for indoor CO2 monitoring and short-term predictive analysis.

The system combines two ESP32-C3 sensor nodes, a Raspberry Pi I2C master, cloud data services, and a Random Forest model that forecasts PAS CO2 levels 15 minutes ahead. A web dashboard presents live sensor measurements and the AI forecast.

## System Overview

The project uses a distributed I2C architecture:

```text
SGP30 eCO2                         XENSIV PAS CO2
    |                                   |
ESP32-C3 Slave 1                  ESP32-C3 Slave 2
I2C address 0x10                  I2C address 0x11
    \                                   /
     \                                 /
              Raspberry Pi
                   |
        +----------+----------+
        |                     |
   Cloud logging          AI prediction
                              |
                     15-minute forecast
                              |
                         Dashboard
```

The SGP30 node provides eCO2 measurements, while the XENSIV PAS CO2 node provides true CO2 measurements. The PAS CO2 measurements are used for the machine learning integration.

## Key Features

- Distributed ESP32-C3 I2C sensor architecture
- Raspberry Pi as the I2C master and AI inference host
- SGP30 eCO2 monitoring
- XENSIV PAS CO2 true CO2 monitoring
- Random Forest CO2 forecasting
- 15-minute prediction horizon
- Rolling one-minute measurement history
- Automatic prediction logging
- Live JSON output for dashboard integration
- ThingSpeak, Adafruit IO, and MongoDB integration scripts
- Responsive web dashboard with live sensor monitoring
- AI forecast display with predicted CO2, expected change, trend, and predicted status
- Dark and light dashboard themes

## Hardware

### Raspberry Pi

The Raspberry Pi acts as the main I2C controller and inference host.

It:

- communicates with both ESP32-C3 slaves
- reads PAS CO2 measurements
- maintains the rolling history required by the AI model
- loads the trained Random Forest model
- performs 15-minute CO2 forecasting
- logs predictions
- provides prediction data for the dashboard
- can forward sensor readings to cloud platforms

### Slave 1: SGP30

- Microcontroller: Lolin ESP32-C3 Mini
- Raspberry Pi I2C address: `0x10`
- Pi-facing SDA: GPIO6
- Pi-facing SCL: GPIO7
- Sensor: SGP30
- Sensor I2C address: `0x58`
- Sensor SDA: GPIO8
- Sensor SCL: GPIO10
- Measurement: eCO2

### Slave 2: XENSIV PAS CO2

- Microcontroller: Lolin ESP32-C3 Mini
- Raspberry Pi I2C address: `0x11`
- Pi-facing SDA: GPIO6
- Pi-facing SCL: GPIO7
- Sensor: Infineon XENSIV PAS CO2
- Sensor I2C address: `0x28`
- Sensor SDA: GPIO8
- Sensor SCL: GPIO10
- Measurement: true CO2

The PAS CO2 sensor is the source used by the AI prediction pipeline.

## I2C Communication

Both ESP32-C3 boards operate as Raspberry Pi-facing I2C slaves.

The Raspberry Pi sends command:

```text
0x01
```

The selected slave responds with two bytes containing the CO2 value as a big-endian unsigned 16-bit integer.

For Slave 2:

```text
Raspberry Pi
    |
    | command 0x01
    v
ESP32-C3 Slave 2 (0x11)
    |
    | two-byte CO2 response
    v
Raspberry Pi
```

## Machine Learning

The project uses a `RandomForestRegressor` to predict the PAS CO2 level 15 minutes into the future.

The model was developed using one week of one-minute time-series CO2 readings.

### Features

The model uses eight input features:

```text
co2_ppm
co2_lag_5
co2_lag_15
co2_change_5
co2_change_15
hour
minute
day_of_week
```

The target is:

```text
co2_future
```

where `co2_future` represents CO2 15 minutes ahead.

### Model Configuration

```text
Algorithm: Random Forest Regressor
Number of trees: 100
Random state: 42
Training/test split: chronological 80/20
Prediction horizon: 15 minutes
```

The chronological split preserves the time ordering of the measurements.

### Prototype Evaluation

The held-out prototype evaluation produced approximately:

```text
R2 Score: 0.990
Mean Absolute Error: 13.31 ppm
Root Mean Squared Error: 18.34 ppm
Persistence Baseline MAE: 13.58 ppm
```

These metrics describe evaluation on the development dataset. They should not be interpreted as validation on real PAS CO2 sensor measurements.

The model file is stored at:

```text
models/co2_random_forest.pkl
```

## Real-Time AI Pipeline

The model was developed using one-minute intervals. The Raspberry Pi therefore maintains one AI sample per minute even though sensor/cloud processes may operate at different intervals.

A rolling history of 16 measurements provides:

```text
Current reading
5-minute lag
15-minute lag
5-minute change
15-minute change
```

Once 16 valid one-minute measurements are available, the Raspberry Pi can generate a new 15-minute forecast every minute.

```text
PAS CO2
   |
ESP32-C3 Slave 2
   |
Raspberry Pi
   |
1-minute sampling
   |
16-reading rolling buffer
   |
Feature engineering
   |
Random Forest
   |
15-minute CO2 forecast
```

## Prediction Status

The AI output uses the following configurable project categories:

```text
Predicted CO2 < 800 ppm       Good
Predicted CO2 < 1000 ppm      Moderate
Predicted CO2 >= 1000 ppm     High
```

These labels are application-level categories used by this project.

## Project Structure

```text
CO2_IoT_AI_System/
|
├── esp32/
│   ├── slave1_sgp30/
│   │   └── slave1_sgp30.cpp
│   └── slave2_pasco2/
│       └── slave2_pasco2.cpp
|
├── raspberry_pi/
│   ├── pasco2_ai_predict.py
│   ├── pasco2_adafruit.py
│   ├── pasco2_mongodb.py
│   └── pasco2_thingspeak.py
|
├── models/
│   └── co2_random_forest.pkl
|
├── dashboard/
│   └── dashboard.html
|
├── data/
│   ├── .gitkeep
│   ├── co2_predictions.csv
│   └── latest_prediction.json
|
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

`co2_predictions.csv` and `latest_prediction.json` are generated automatically while the AI prediction script is running.

## Raspberry Pi Setup

### 1. Enable I2C

Ensure I2C is enabled on the Raspberry Pi.

Confirm that the ESP32-C3 slaves are visible:

```bash
i2cdetect -y 1
```

With both sensor nodes connected, the expected slave addresses are:

```text
0x10
0x11
```

### 2. Create a Python Virtual Environment

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Running the AI Predictor

From the project root:

```bash
python3 raspberry_pi/pasco2_ai_predict.py
```

The program reads the PAS CO2 value from Slave 2 once per minute.

During startup, the rolling history fills:

```text
[AI] History: 1/16 readings
[AI] History: 2/16 readings
...
[AI] History: 16/16 readings
```

After sufficient history is available, the model generates a 15-minute forecast.

The predictor automatically updates:

```text
data/co2_predictions.csv
data/latest_prediction.json
```

## Prediction Data

### co2_predictions.csv

This file stores the prediction history.

Example:

```csv
timestamp,current_co2_ppm,predicted_co2_ppm_15min,status
2026-09-14T10:30:00,624,671.40,Good
2026-09-14T10:31:00,628,676.25,Good
```

### latest_prediction.json

This file contains the latest forecast for the dashboard.

Example:

```json
{
  "timestamp": "2026-09-14T10:31:00",
  "current_co2_ppm": 628,
  "predicted_co2_ppm_15min": 676.25,
  "status": "Good"
}
```

The file is overwritten whenever a new prediction is generated so the dashboard can always access the most recent result.

## Dashboard

The web dashboard provides separate views for the two sensor nodes.

### Slave 1

The SGP30 view displays:

- current eCO2
- sensor status
- gauge
- session minimum and maximum
- historical trend

### Slave 2 and AI

The PAS CO2 view displays:

- current true CO2
- sensor status
- gauge
- session minimum and maximum
- historical CO2 trend
- predicted CO2 15 minutes ahead
- expected change in ppm
- rising, falling, or stable prediction trend
- predicted status
- AI prediction timestamp

The existing live sensor history is obtained through the project's ThingSpeak integration. The AI section reads:

```text
data/latest_prediction.json
```

## Serving the Dashboard

The dashboard should be served through HTTP so that the browser can retrieve the prediction JSON file.

From the project root:

```bash
python3 -m http.server 8000
```

Then open:

```text
http://<raspberry-pi-ip>:8000/dashboard/dashboard.html
```

When opened on the Raspberry Pi itself, it can also be accessed using:

```text
http://localhost:8000/dashboard/dashboard.html
```

## Cloud Integration

Separate Raspberry Pi scripts are included for:

### ThingSpeak

```text
raspberry_pi/pasco2_thingspeak.py
```

Uploads PAS CO2 measurements to ThingSpeak.

### Adafruit IO

```text
raspberry_pi/pasco2_adafruit.py
```

Uploads PAS CO2 measurements to an Adafruit IO feed.

### MongoDB

```text
raspberry_pi/pasco2_mongodb.py
```

Stores timestamped PAS CO2 measurements in MongoDB.

Credentials and API keys should not be committed to the repository.

Use environment variables or another appropriate secret-management method for:

```text
AIO_USERNAME
AIO_KEY
AIO_FEED
THINGSPEAK_WRITE_KEY
MONGO_URI
```

The `.env.example` file documents the expected variable names without containing real credentials.

## Data Folder

The `data` directory is reserved for runtime AI output.

Before the first run it may contain only:

```text
.gitkeep
```

`.gitkeep` is an empty placeholder that allows Git to retain the otherwise empty directory.

During operation, the AI predictor creates:

```text
co2_predictions.csv
latest_prediction.json
```

The development/training CSV files do not need to be copied into this deployment directory.

## Security

Do not commit:

- MongoDB connection credentials
- ThingSpeak write keys
- Adafruit IO keys
- other private API credentials

The repository `.gitignore` excludes `.env` and generated runtime prediction files.

If a credential is accidentally exposed publicly or committed to version control, it should be revoked or rotated.

## Current Validation Scope

The hardware integration uses real measurements from the XENSIV PAS CO2 sensor.

## Project Objective

The project demonstrates how embedded sensing, IoT communication, time-series feature engineering, machine learning, cloud connectivity, and web visualization can be combined into a single predictive monitoring system.

Rather than only reporting the current indoor CO2 level, the system extends conventional monitoring by estimating what the CO2 level may be 15 minutes into the future.
