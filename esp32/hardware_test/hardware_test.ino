/*
 * GridGuard ESP32 Standalone Hardware Diagnostic Test Sketch
 * Pin Assignments:
 *  - RELAY_PIN       : Pin 18 (Relay Control)
 *  - BUTTON_PIN      : Pin 4  (Physical Push Button to GND)
 *  - LED_GREEN_PIN   : Pin 26 (Connection Green LED)
 *  - LED_RED_PIN     : Pin 25 (Load State Red LED)
 *
 * Instructions:
 * 1. Upload this sketch to your ESP32.
 * 2. Open Serial Monitor at 115200 baud.
 * 3. Press the push button: Relay should click ON/OFF, and Red LED should turn ON/OFF.
 * 4. Green LED will blink automatically every 1 second to confirm pin control.
 */

#define RELAY_PIN 4
#define BUTTON_PIN 18
#define LED_GREEN_PIN 26
#define LED_RED_PIN 27

bool relayState = false;
unsigned long lastButtonPress = 0;
unsigned long lastBlink = 0;
bool greenState = false;

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n==========================================");
  Serial.println("  GridGuard ESP32 Hardware Test Started");
  Serial.println("==========================================");

  pinMode(RELAY_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(LED_GREEN_PIN, OUTPUT);
  pinMode(LED_RED_PIN, OUTPUT);

  // Initial State: OFF
  digitalWrite(RELAY_PIN, LOW);
  digitalWrite(LED_RED_PIN, LOW);
  digitalWrite(LED_GREEN_PIN, LOW);
  
  Serial.println("System Ready. Press the Push Button to toggle Relay & Red LED!");
}

void loop() {
  // 1. Push Button & Relay Test (Debounced)
  if (digitalRead(BUTTON_PIN) == LOW) {
    if (millis() - lastButtonPress > 300) { // 300ms Debounce
      lastButtonPress = millis();
      relayState = !relayState;
      
      digitalWrite(RELAY_PIN, relayState ? HIGH : LOW);
      digitalWrite(LED_RED_PIN, relayState ? HIGH : LOW);
      
      Serial.printf("[BUTTON PRESS] Relay: %s | Red LED: %s\n", 
                    relayState ? "ON (HIGH)" : "OFF (LOW)", 
                    relayState ? "ON (HIGH)" : "OFF (LOW)");
    }
  }

  // 2. Green LED Blink Test (Every 1 second)
  if (millis() - lastBlink > 1000) {
    lastBlink = millis();
    greenState = !greenState;
    digitalWrite(LED_GREEN_PIN, greenState ? HIGH : LOW);
    Serial.printf("[HEARTBEAT] Green LED: %s\n", greenState ? "HIGH" : "LOW");
  }
}
