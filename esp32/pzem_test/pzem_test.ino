/*
 * GridGuard ESP32 + PZEM-004T (V3.0) Standalone Hardware Test Sketch
 * 
 * Pin Assignments:
 *  - PZEM VCC  : ESP32 5V (or VIN)
 *  - PZEM GND  : ESP32 GND
 *  - PZEM TX   : ESP32 GPIO 27 (Configured as ESP RX)
 *  - PZEM RX   : ESP32 GPIO 26 (Configured as ESP TX)
 * 
 * Instructions:
 *  1. Open Arduino IDE, select ESP32 Dev Module.
 *  2. Upload this standalone test sketch to ESP32.
 *  3. Open Serial Monitor at 115200 baud.
 */

#include <PZEM004Tv30.h>

#define PZEM_RX_PIN 27 // Connected to PZEM TX
#define PZEM_TX_PIN 26 // Connected to PZEM RX

PZEM004Tv30 pzem(Serial2, PZEM_RX_PIN, PZEM_TX_PIN);

void setup() {
  Serial.begin(115200);
  delay(1000);

  // Initialize HardwareSerial2 explicitly on Pins 27 (RX) and 26 (TX)
  Serial2.begin(9600, SERIAL_8N1, PZEM_RX_PIN, PZEM_TX_PIN);
  delay(500);

  Serial.println("\n==================================================");
  Serial.println("  GridGuard ESP32 + PZEM-004T Standalone Test     ");
  Serial.println("==================================================");
  Serial.printf("Configured Pins: RX=%d (ESP RX -> PZEM TX), TX=%d (ESP TX -> PZEM RX)\n\n", PZEM_RX_PIN, PZEM_TX_PIN);
}

void loop() {
  float voltage   = pzem.voltage();
  float current   = pzem.current();
  float power     = pzem.power();
  float energy    = pzem.energy();
  float frequency = pzem.frequency();
  float pf        = pzem.pf();

  Serial.println("──────────────────────────────────────────────────");
  if (isnan(voltage)) {
    Serial.println("❌ ERROR: No UART response from PZEM-004T!");
    Serial.println("   Check DC Wiring:");
    Serial.println("   1. Is PZEM VCC connected to ESP32 5V / VIN pin? (3.3V is insufficient)");
    Serial.println("   2. Is PZEM GND connected to ESP32 GND?");
    Serial.println("   3. Is PZEM TX connected to ESP32 GPIO 27?");
    Serial.println("   4. Is PZEM RX connected to ESP32 GPIO 26?\n");
  } else {
    Serial.printf(" ⚡ Voltage:      %.1f V %s\n", voltage, (voltage < 50.0) ? "⚠️ (0.0V -> Connect 230V AC Live & Neutral to L/N screws!)" : "✅ (AC Powered)");
    Serial.printf(" 🔌 Current:      %.2f A %s\n", isnan(current) ? 0.0 : current, (current == 0.0) ? "(Check if kettle/load is ON and Live wire passes through CT coil)" : "✅");
    Serial.printf(" 💡 Active Power: %.1f W\n", isnan(power) ? 0.0 : power);
    Serial.printf(" 📊 Energy:       %.4f kWh\n", isnan(energy) ? 0.0 : energy);
    Serial.printf(" 🌐 Frequency:    %.1f Hz\n", isnan(frequency) ? 0.0 : frequency);
    Serial.printf(" 📈 Power Factor: %.2f\n", isnan(pf) ? 0.0 : pf);
  }
  Serial.println("──────────────────────────────────────────────────\n");

  delay(2000);
}
