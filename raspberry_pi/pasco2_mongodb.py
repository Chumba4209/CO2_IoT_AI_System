import os
import time
from datetime import datetime, timezone

import smbus2
from pymongo import MongoClient

SLAVE_ADDR = 0x11
MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise RuntimeError("Set MONGO_URI before running this script.")

client = MongoClient(MONGO_URI)
collection = client["CO2_Meter"]["pasco2"]


def read_co2():
    with smbus2.SMBus(1) as bus:
        write = smbus2.i2c_msg.write(SLAVE_ADDR, [0x01])
        read = smbus2.i2c_msg.read(SLAVE_ADDR, 2)
        bus.i2c_rdwr(write, read)
        data = list(read)
    return (data[0] << 8) | data[1]


while True:
    try:
        co2 = read_co2()
        if co2 not in (0, 65535):
            collection.insert_one({
                "timestamp": datetime.now(timezone.utc),
                "sensor": "XENSIV_PAS_CO2",
                "node": "slave_0x11",
                "co2_ppm": co2,
            })
            print(f"MongoDB: {co2} ppm")
    except Exception as exc:
        print(f"MongoDB error: {exc}")

    time.sleep(15)
