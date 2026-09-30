import os
import time
import requests
import smbus2

SLAVE_ADDR = 0x11
WRITE_KEY = os.getenv("THINGSPEAK_WRITE_KEY")


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
            requests.get(
                "https://api.thingspeak.com/update",
                params={"api_key": WRITE_KEY, "field1": co2},
                timeout=10,
            ).raise_for_status()
            print(f"ThingSpeak: {co2} ppm")
    except Exception as exc:
        print(f"ThingSpeak error: {exc}")

    time.sleep(15)
