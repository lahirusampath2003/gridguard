/*
 * GridGuard ESP32 PZEM-004T Automatic Pin Pair Scanner
 * 
 * Upload this sketch to your ESP32. It will automatically test every common
 * GPIO pin combination to find which physical pins your PZEM module is wired to!
 */

#include <PZEM004Tv30.h>

struct PinPair {
  uint8_t rx;
  uint8_t tx;
  const char* name;
};

// List of candidate RX / TX pin pairs to scan
PinPair candidatePairs[] = {
  {16, 17, "ESP RX=16, ESP TX=17"},
  {17, 16, "ESP RX=17, ESP TX=16"},
  {27, 26, "ESP RX=27, ESP TX=26"},
  {26, 27, "ESP RX=26, ESP TX=27"},
  {32, 33, "ESP RX=32, ESP TX=33"},
  {33, 32, "ESP RX=33, ESP TX=32"},
  {18, 19, "ESP RX=18, ESP TX=19"},
  {4, 5,   "ESP RX=4,  ESP TX=5"}
};

const int totalPairs = sizeof(candidatePairs) / sizeof(candidatePairs[0]);

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println("\n==================================================");
  Serial.println("   GridGuard PZEM-004T Automatic Pin Scanner     ");
  Serial.println("==================================================");
  Serial.println("Scanning candidate GPIO pairs to detect PZEM-004T...\n");
}

void loop() {
  bool foundPzem = false;

  for (int i = 0; i < totalPairs; i++) {
    uint8_t rxPin = candidatePairs[i].rx;
    uint8_t txPin = candidatePairs[i].tx;

    Serial.printf("[%d/%d] Testing Pair: %s ... ", i + 1, totalPairs, candidatePairs[i].name);

    // End previous serial session and re-init HardwareSerial2 on test pins
    Serial2.end();
    delay(50);
    Serial2.begin(9600, SERIAL_8N1, rxPin, txPin);
    delay(200);

    PZEM004Tv30 pzemTest(Serial2, rxPin, txPin);
    float voltage = pzemTest.voltage();

    if (!isnan(voltage)) {
      Serial.println(" SUCCESS! 🎉");
      Serial.println("==================================================");
      Serial.printf(" ✅ PZEM DETECTED ON: RX = %d (to PZEM TX) | TX = %d (to PZEM RX)\n", rxPin, txPin);
      Serial.printf(" ⚡ Measured Voltage: %.1f V\n", voltage);
      Serial.println("==================================================\n");
      foundPzem = true;
      
      // Stay on this working pair and keep reading metrics!
      while (true) {
        float v = pzemTest.voltage();
        float c = pzemTest.current();
        float p = pzemTest.power();

        Serial.printf("⚡ Voltage: %.1f V | 🔌 Current: %.2f A | 💡 Power: %.1f W\n", 
                      isnan(v) ? 0.0 : v, 
                      isnan(c) ? 0.0 : c, 
                      isnan(p) ? 0.0 : p);
        delay(1500);
      }
    } else {
      Serial.println("❌ (No Response)");
    }
    delay(300);
  }

  if (!foundPzem) {
    Serial.println("\n⚠️ Scan finished. No PZEM detected on any tested pin pairs.");
    Serial.println("Please check:");
    Serial.println(" 1. Is PZEM VCC connected to ESP32 5V / VIN?");
    Serial.println(" 2. Is PZEM GND connected to ESP32 GND?");
    Serial.println(" 3. Are the jumper wires firmly plugged into the pins?\n");
    Serial.println("Retrying scan in 5 seconds...\n");
    delay(5000);
  }
}
