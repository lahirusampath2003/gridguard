#include <WiFi.h>
#include <PubSubClient.h>
#include <PZEM004Tv30.h>

// Wi-Fi & MQTT Credentials
const char* ssid = "Samsung M14";
const char* password = "deminiuom124";
const char* mqtt_server = "10.99.209.171"; // Raspberry Pi 5 IP

const char* topic_power = "gridguard/sensor/main_power";

// Hardware Pin Definitions for D26 / D27 Wiring:
#define PZEM_RX_PIN 26 // Connected to PZEM TX
#define PZEM_TX_PIN 27 // Connected to PZEM RX
#define STATUS_LED_PIN 2 // Built-in Blue LED (GPIO 2)

PZEM004Tv30 pzem(Serial2, PZEM_RX_PIN, PZEM_TX_PIN);

WiFiClient espClient;
PubSubClient client(espClient);

unsigned long lastMsgTime = 0;

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to Wi-Fi: ");
  Serial.println(ssid);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN));
    delay(250);
    Serial.print(".");
  }
  
  Serial.println("\nWiFi connected successfully!");
  Serial.print("PZEM ESP32 IP Address: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection to Pi (");
    Serial.print(mqtt_server);
    Serial.print(")...");
    
    digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN));
    
    if (client.connect("pzem-main-meter")) {
      Serial.println("CONNECTED to GridGuard Brain!");
      digitalWrite(STATUS_LED_PIN, HIGH);
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" retrying in 3 seconds...");
      delay(3000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(STATUS_LED_PIN, OUTPUT);
  digitalWrite(STATUS_LED_PIN, LOW);

  Serial.println("\n==========================================");
  Serial.println("   GridGuard PZEM-004T Meter Node         ");
  Serial.println("==========================================");

  // Initialize HardwareSerial2 explicitly on Pins 26 (RX) & 27 (TX)
  Serial2.begin(9600, SERIAL_8N1, PZEM_RX_PIN, PZEM_TX_PIN);
  delay(1000);

  Serial.printf("PZEM Configured Pins: ESP RX=%d, ESP TX=%d\n", PZEM_RX_PIN, PZEM_TX_PIN);

  setup_wifi();
  client.setServer(mqtt_server, 1883);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  } else {
    digitalWrite(STATUS_LED_PIN, HIGH);
  }
  client.loop();

  unsigned long now = millis();
  if (now - lastMsgTime > 2000) {
    lastMsgTime = now;

    float voltage = pzem.voltage();
    float current = pzem.current();
    float power = pzem.power();

    if (isnan(voltage)) voltage = 0.0;
    if (isnan(current)) current = 0.0;
    if (isnan(power)) power = 0.0;

    String jsonPayload = "{\"power_w\":" + String(power, 1) + 
                         ",\"current\":" + String(current, 2) + 
                         ",\"voltage\":" + String(voltage, 1) + "}";

    Serial.print("Telemetry: ");
    Serial.println(jsonPayload);

    if (client.connected()) {
      client.publish(topic_power, jsonPayload.c_str());
    }
  }
}
