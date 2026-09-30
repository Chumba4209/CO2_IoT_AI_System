#include <Arduino.h>
#include <driver/i2c.h>
#include <SoftWire.h>

#define SLAVE_ADDR 0x11
#define PI_SDA 6
#define PI_SCL 7
#define I2C_PORT I2C_NUM_0

#define PAS_ADDR 0x28
#define SENSOR_SDA 8
#define SENSOR_SCL 10

#define REG_PROD_ID 0x00
#define REG_SENS_STS 0x01
#define REG_MEAS_CFG 0x04
#define REG_CO2PPM_H 0x05
#define REG_MEAS_STS 0x07

SoftWire sensorWire(SENSOR_SDA, SENSOR_SCL);
uint16_t co2_ppm = 0;

bool writeRegister(uint8_t reg, uint8_t value) {
    sensorWire.beginTransmission(PAS_ADDR);
    sensorWire.write(reg);
    sensorWire.write(value);
    return sensorWire.endTransmission() == 0;
}

bool readRegisters(uint8_t reg, uint8_t *data, size_t length) {
    sensorWire.beginTransmission(PAS_ADDR);
    sensorWire.write(reg);

    if (sensorWire.endTransmission(false) != 0) {
        return false;
    }

    sensorWire.requestFrom(PAS_ADDR, (uint8_t)length);

    size_t i = 0;
    while (sensorWire.available() && i < length) {
        data[i++] = sensorWire.read();
    }

    return i == length;
}

bool readRegister(uint8_t reg, uint8_t &value) {
    return readRegisters(reg, &value, 1);
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

bool initializePasCo2() {
    uint8_t productId = 0;
    uint8_t sensorStatus = 0;

    if (!readRegister(REG_PROD_ID, productId) || productId != 0x02) {
        Serial.printf("Unexpected PAS CO2 product ID: 0x%02X\n", productId);
        return false;
    }

    if (!readRegister(REG_SENS_STS, sensorStatus) || !(sensorStatus & 0x10)) {
        Serial.println("PAS CO2 sensor not ready");
        return false;
    }

    // Continuous measurement mode.
    return writeRegister(REG_MEAS_CFG, 0x04);
}

bool readPasCo2(uint16_t &ppm) {
    uint8_t measurementStatus = 0;

    if (!readRegister(REG_MEAS_STS, measurementStatus) || !(measurementStatus & 0x02)) {
        return false;
    }

    uint8_t data[2];
    if (!readRegisters(REG_CO2PPM_H, data, sizeof(data))) {
        return false;
    }

    ppm = ((uint16_t)data[0] << 8) | data[1];
    return true;
}

void setup() {
    Serial.begin(115200);
    sensorWire.begin();
    setupPiI2C();

    if (!initializePasCo2()) {
        Serial.println("PAS CO2 initialization failed");
    }
}

void loop() {
    static unsigned long lastMeasure = 0;

    if (millis() - lastMeasure >= 1000) {
        lastMeasure = millis();

        uint16_t reading;
        if (readPasCo2(reading)) {
            co2_ppm = reading;
            Serial.printf("CO2: %u ppm\n", co2_ppm);
        }
    }

    uint8_t command;
    int received = i2c_slave_read_buffer(I2C_PORT, &command, 1, 10 / portTICK_PERIOD_MS);

    if (received == 1 && command == 0x01) {
        uint8_t response[2] = {
            (uint8_t)(co2_ppm >> 8),
            (uint8_t)(co2_ppm & 0xFF)
        };

        i2c_slave_write_buffer(I2C_PORT, response, 2, 100 / portTICK_PERIOD_MS);
    }
}
