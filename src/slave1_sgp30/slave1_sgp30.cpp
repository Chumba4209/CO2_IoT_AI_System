#include <Arduino.h>
#include <driver/i2c.h>
#include <SoftWire.h>

#define SLAVE_ADDR 0x10
#define PI_SDA 6
#define PI_SCL 7
#define I2C_PORT I2C_NUM_0

#define SGP30_ADDR 0x58
#define SENSOR_SDA 8
#define SENSOR_SCL 10

SoftWire sensorWire(SENSOR_SDA, SENSOR_SCL);
uint16_t eco2_ppm = 400;

bool sgp30Command(uint16_t command, uint8_t *data = nullptr, size_t length = 0) {
    sensorWire.beginTransmission(SGP30_ADDR);
    sensorWire.write(command >> 8);
    sensorWire.write(command & 0xFF);

    if (sensorWire.endTransmission() != 0) {
        return false;
    }

    if (length == 0) {
        return true;
    }

    delay(12);
    sensorWire.requestFrom(SGP30_ADDR, (uint8_t)length);

    size_t i = 0;
    while (sensorWire.available() && i < length) {
        data[i++] = sensorWire.read();
    }

    return i == length;
}

void setupPiI2C() {
    i2c_config_t config = {};
    config.mode = I2C_MODE_SLAVE;
    config.sda_io_num = (gpio_num_t)PI_SDA;
    config.scl_io_num = (gpio_num_t)PI_SCL;
    config.sda_pullup_en = GPIO_PULLUP_ENABLE;
    config.scl_pullup_en = GPIO_PULLUP_ENABLE;
    config.slave.addr_10bit_en = 0;
    config.slave.slave_addr = SLAVE_ADDR;

    i2c_param_config(I2C_PORT, &config);
    i2c_driver_install(I2C_PORT, config.mode, 256, 256, 0);
}

void setup() {
    Serial.begin(115200);
    sensorWire.begin();
    setupPiI2C();

    // Initialize SGP30 and allow it to stabilize.
    sgp30Command(0x2003);
    delay(15000);
}

void loop() {
    static unsigned long lastMeasure = 0;

    if (millis() - lastMeasure >= 1000) {
        lastMeasure = millis();

        uint8_t data[6];
        if (sgp30Command(0x2008, data, sizeof(data))) {
            eco2_ppm = ((uint16_t)data[0] << 8) | data[1];
            Serial.printf("eCO2: %u ppm\n", eco2_ppm);
        }
    }

    uint8_t command;
    int received = i2c_slave_read_buffer(I2C_PORT, &command, 1, 10 / portTICK_PERIOD_MS);

    if (received == 1 && command == 0x01) {
        uint8_t response[2] = {
            (uint8_t)(eco2_ppm >> 8),
            (uint8_t)(eco2_ppm & 0xFF)
        };

        i2c_slave_write_buffer(I2C_PORT, response, 2, 100 / portTICK_PERIOD_MS);
    }
}
