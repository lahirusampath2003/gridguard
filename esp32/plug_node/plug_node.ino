// Co-Developed by Kavishka Shanilka (@kavishshanilka)
#include <WiFi.h>
#include <PubSubClient.h>

// Wi-Fi & MQTT Credentials
const char* ssid = "Samsung M14";
const char* password = "deminiuom124";
const char* mqtt_server = "10.99.209.171"; // Raspberry Pi Current IP

const char* topic_power = "gridguard/sensor/plug1_power";
const char* topic_status = "gridguard/nodes/smart-plug-1/status";
const char* topic_command = "gridguard/nodes/smart-plug-1/command";

// Hardware Pin Definitions
#define RELAY_PIN 4
#define BUTTON_PIN 18
#define RED_LED_PIN 27    // External Red Status LED (Swapped to GPIO 27)
#define GREEN_LED_PIN 26  // External Green Status LED (Swapped to GPIO 26)

// Relay Trigger Logic (HIGH = ON, LOW = OFF)
#define RELAY_ON_STATE HIGH
#define RELAY_OFF_STATE LOW

WiFiClient espClient;
PubSubClient client(espClient);

bool relayState = false;
bool isPeakDelay = false;
bool overrideMode = false;
bool lastButtonState = HIGH;
unsigned long lastMqttTime = 0;
unsigned long lastBlinkTime = 0;
bool blinkState = false;

void setRelay(bool state, bool peakDelay = false, const char* statusMsg = "OFF") {
  relayState = state;
  isPeakDelay = peakDelay;
  digitalWrite(RELAY_PIN, relayState ? RELAY_ON_STATE : RELAY_OFF_STATE);
  
  // RED LED indicates Load State:
  // - Solid RED: Load ON
  // - Fast Blinking RED: Load Intercepted / Peak Delay Mode
  // - OFF: Load OFF
  if (!isPeakDelay) {
    digitalWrite(RED_LED_PIN, relayState ? HIGH : LOW);
  }

  if (client.connected()) {
    String payload = isPeakDelay ? "{\"state\":\"DELAY\"}" : (relayState ? "{\"state\":\"ON\"}" : "{\"state\":\"OFF\"}");
    client.publish(topic_status, payload.c_str());
    client.publish("gridguard/nodes/plug-1/status", payload.c_str());
  }
}

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to Wi-Fi: ");
  Serial.println(ssid);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  // Blink GREEN LED (GPIO 26) while searching for Wi-Fi
  while (WiFi.status() != WL_CONNECTED) {
    digitalWrite(GREEN_LED_PIN, !digitalRead(GREEN_LED_PIN));
    digitalWrite(RED_LED_PIN, LOW);
    delay(250);
    Serial.print(".");
  }
  
  Serial.println("\nWiFi connected successfully!");
  Serial.print("ESP32 IP Address: ");
  Serial.println(WiFi.localIP());
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message;
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.print("Plug command received via Web: ");
  Serial.println(message);

  lastMqttTime = millis();

  if (message.indexOf("OFF") >= 0) {
    overrideMode = false;
    setRelay(false, false, "OFF");
  } else if (message.indexOf("ON") >= 0) {
    overrideMode = false;
    setRelay(true, false, "ON");
  } else if (message.indexOf("DELAY") >= 0) {
    overrideMode = false;
    setRelay(false, true, "DELAY");
  } else if (message.indexOf("OVERRIDE") >= 0) {
    overrideMode = true;
    setRelay(true, false, "OVERRIDE");
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection to Pi (");
    Serial.print(mqtt_server);
    Serial.print(")...");
    
    // Blink GREEN LED (GPIO 26) while connecting to MQTT
    digitalWrite(GREEN_LED_PIN, !digitalRead(GREEN_LED_PIN));
    
    if (client.connect("smart-plug-1")) {
      Serial.println("CONNECTED to GridGuard Brain!");
      digitalWrite(GREEN_LED_PIN, HIGH); // Solid GREEN when Wi-Fi + MQTT connected!
      
      client.subscribe(topic_command);
      client.subscribe("gridguard/nodes/plug-1/command");
      setRelay(relayState, isPeakDelay, isPeakDelay ? "DELAY" : (relayState ? "ON" : "OFF"));
    } else {
      Serial.print("Failed! rc=");
      Serial.print(client.state());
      Serial.println(" retrying in 3 seconds...");
      delay(3000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(RED_LED_PIN, OUTPUT);
  pinMode(GREEN_LED_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  
  // Initial State: Load OFF
  setRelay(false, false, "OFF");

  lastButtonState = digitalRead(BUTTON_PIN);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(mqttCallback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  } else {
    digitalWrite(GREEN_LED_PIN, HIGH); // Solid GREEN = 100% Connected
  }
  
  client.loop();

  // Peak Delay LED Warning Blinking (Fast Red Blink when heavy load is intercepted)
  if (isPeakDelay) {
    if (millis() - lastBlinkTime > 300) {
      lastBlinkTime = millis();
      blinkState = !blinkState;
      digitalWrite(RED_LED_PIN, blinkState ? HIGH : LOW);
    }
  }

  // Physical Push Button Toggle Logic
  if (millis() - lastMqttTime > 1500) {
    bool currentButtonState = digitalRead(BUTTON_PIN);
    if (currentButtonState == LOW && lastButtonState == HIGH) {
      delay(50); // debounce
      if (digitalRead(BUTTON_PIN) == LOW) {
        setRelay(!relayState, false, !relayState ? "ON" : "OFF");
        Serial.print("Physical button pressed! Relay state: ");
        Serial.println(relayState ? "ON" : "OFF");
        while (digitalRead(BUTTON_PIN) == LOW) {
          delay(10);
        }
      }
    }
    lastButtonState = currentButtonState;
  } else {
    lastButtonState = digitalRead(BUTTON_PIN);
  }
}
