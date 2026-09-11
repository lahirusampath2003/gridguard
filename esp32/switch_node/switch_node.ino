#include <WiFi.h>
#include <PubSubClient.h>

// Wi-Fi & MQTT Credentials
const char* ssid = "Samsung M14";
const char* password = "deminiuom124";
const char* mqtt_server = "10.99.209.171"; // Raspberry Pi Current IP

const char* topic_status = "gridguard/nodes/smart-switch-1/status";
const char* topic_command = "gridguard/nodes/smart-switch-1/command";

// Hardware Pin Definitions
#define RELAY_PIN 4
#define SWITCH_PIN 18
#define RED_LED_PIN 27    // External Red Status LED (Swapped to GPIO 27)
#define GREEN_LED_PIN 26  // External Green Status LED (Swapped to GPIO 26)

// Relay Trigger Logic (HIGH = ON, LOW = OFF)
#define RELAY_ON_STATE HIGH
#define RELAY_OFF_STATE LOW

WiFiClient espClient;
PubSubClient client(espClient);

bool relayState = false;
bool isPeakDelay = false;
bool lastSwitchState = HIGH;
unsigned long lastMqttTime = 0;
unsigned long lastBlinkTime = 0;
bool blinkState = false;

void setRelay(bool state, bool peakDelay = false) {
  relayState = state;
  isPeakDelay = peakDelay;
  digitalWrite(RELAY_PIN, relayState ? RELAY_ON_STATE : RELAY_OFF_STATE);
  
  // RED LED indicates Load State:
  // - Solid RED: Load ON
  // - Fast Blinking RED: Load ON/Intercepted during Peak Time
  // - OFF: Load OFF
  if (!isPeakDelay) {
    digitalWrite(RED_LED_PIN, relayState ? HIGH : LOW);
  }

  if (client.connected()) {
    String payload = isPeakDelay ? "{\"state\":\"DELAY\"}" : (relayState ? "{\"state\":\"ON\"}" : "{\"state\":\"OFF\"}");
    client.publish(topic_status, payload.c_str());
    client.publish("gridguard/nodes/switch-1/status", payload.c_str());
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
  Serial.print("Web Command received: ");
  Serial.println(message);

  lastMqttTime = millis();

  if (message.indexOf("OFF") >= 0) {
    setRelay(false, false);
  } else if (message.indexOf("ON") >= 0 || message.indexOf("OVERRIDE") >= 0) {
    setRelay(true, false);
  } else if (message.indexOf("DELAY") >= 0) {
    setRelay(false, true);
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection to Pi (");
    Serial.print(mqtt_server);
    Serial.print(")...");
    
    // Blink GREEN LED (GPIO 26) while connecting to MQTT Broker
    digitalWrite(GREEN_LED_PIN, !digitalRead(GREEN_LED_PIN));
    
    if (client.connect("smart-switch-1")) {
      Serial.println("CONNECTED to GridGuard Brain!");
      digitalWrite(GREEN_LED_PIN, HIGH); // Solid GREEN when Wi-Fi + MQTT connected!
      
      client.subscribe(topic_command);
      client.subscribe("gridguard/nodes/switch-1/command");
      
      setRelay(relayState, isPeakDelay);
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
  pinMode(SWITCH_PIN, INPUT_PULLUP);
  
  // Initial State: Load OFF
  setRelay(false);

  lastSwitchState = digitalRead(SWITCH_PIN);
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

  // Peak Delay LED Warning Blinking (Fast Red Blink when load is intercepted)
  if (isPeakDelay) {
    if (millis() - lastBlinkTime > 300) {
      lastBlinkTime = millis();
      blinkState = !blinkState;
      digitalWrite(RED_LED_PIN, blinkState ? HIGH : LOW);
    }
  }

  // Physical Button & Wall Switch Toggle Logic
  if (millis() - lastMqttTime > 1500) {
    bool currentSwitchState = digitalRead(SWITCH_PIN);
    
    if (currentSwitchState == LOW && lastSwitchState == HIGH) {
      delay(50); // debounce
      if (digitalRead(SWITCH_PIN) == LOW) {
        setRelay(!relayState, false);
        Serial.print("Physical button pressed! Relay state: ");
        Serial.println(relayState ? "ON" : "OFF");
        while (digitalRead(SWITCH_PIN) == LOW) {
          delay(10);
        }
      }
    }
    lastSwitchState = currentSwitchState;
  } else {
    lastSwitchState = digitalRead(SWITCH_PIN);
  }
}
