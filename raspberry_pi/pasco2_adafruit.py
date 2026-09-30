import os
import time
import requests
import smbus2

SLAVE_ADDR = 0x11
AIO_USERNAME = os.getenv("AIO_USERNAME")
AIO_KEY = os.getenv("AIO_KEY")
AIO_FEED = os.getenv("AIO_FEED", "pasco2-level")


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
            url = f"https://io.adafruit.com/api/v2/{AIO_USERNAME}/feeds/{AIO_FEED}/data"
            requests.post(
                url,
                headers={"X-AIO-Key": AIO_KEY},
                json={"value": co2},
                timeout=10,
            ).raise_for_status()
            print(f"Adafruit IO: {co2} ppm")
    except Exception as exc:
        print(f"Adafruit IO error: {exc}")

    time.sleep(15)
