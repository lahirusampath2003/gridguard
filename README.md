# ⚡ GridGuard: Smart Demand-Response Home Energy Engine

> 📖 **Master System Specification**: For complete pinouts, MQTT topics, control rules, and UI features, see [`SYSTEM_SPECIFICATION.md`](SYSTEM_SPECIFICATION.md).

**GridGuard** is an intelligent, autonomous IoT Home Demand-Response & Energy Cost Optimization Engine built for peak grid stabilization, load shedding, and real-time electricity tariff forecasting.

---

## 🌟 Key Features

- **⚡ Autonomous Peak Load Shedding**: Automatically delays non-critical heavy appliances (>1000W) during Peak Utility Hours (e.g. 18:30 – 22:30).
- **⏱️ Timers & Daily Schedules Override**: User-configured timers and daily schedules execute seamlessly with peak protection overrides.
- **📊 Electricity Tariff & Monthly Bill Projection**: Real-time projected electricity bill (LKR) and daily cost analytics based on customizable billing cycle start days and off-peak/peak tariff rates.
- **🌱 Cost & Carbon Savings Tracker**: Calculates exact money (LKR) and energy (kWh) saved by shifting heavy loads away from expensive peak windows.
- **🎨 Neumorphic Minimalist UI**: Dual responsive web application featuring a fixed icon sidebar for desktop/laptops and a native floating bottom navigation bar for mobile smartphones.
- **📜 Real-Time System Terminal Log**: Full console event logging for all MQTT commands, node state changes, and demand-response interventions.

---

## 🏗️ Hardware Architecture & Pinout Summary

### 1. Central Hub (Mastermind)
- **Raspberry Pi 5** running Raspberry Pi OS (Bookworm 64-bit).
- Hosts **Mosquitto MQTT Broker** (`0.0.0.0:1883`) and **Flask Web App** (`port 5000`).

### 2. IoT Nodes (ESP32 Microcontrollers)

| Node ID | Type | Hardware Pins | External Status LEDs | MQTT Command / Status Topics |
| :--- | :--- | :--- | :--- | :--- |
| `smart-plug-1` | **Plug** | Relay: **GPIO 4**<br>Button: **GPIO 18** | Red: **GPIO 26**<br>Green: **GPIO 27** | Command: `gridguard/nodes/smart-plug-1/command`<br>Status: `gridguard/nodes/smart-plug-1/status` |
| `smart-switch-1` | **Switch** | Relay: **GPIO 4**<br>Switch: **GPIO 18** | Red: **GPIO 26**<br>Green: **GPIO 27** | Command: `gridguard/nodes/smart-switch-1/command`<br>Status: `gridguard/nodes/smart-switch-1/status` |
| `pzem-main-meter` | **Sensor** | PZEM TX: **GPIO 26**<br>PZEM RX: **GPIO 27** | N/A | Telemetry: `gridguard/sensor/main_power` |

---

## 📁 Repository Directory Structure

```text
gridguard/
├── SYSTEM_SPECIFICATION.md        # Master System Architecture & Feature Reference
├── README.md                      # Quickstart Project Guide
├── pi/                            # Raspberry Pi Central Engine & Web Dashboard
│   ├── gridguard_brain.py         # Mastermind Engine (MQTT logic, tariff rules, timers)
│   ├── app.py                     # Flask Web REST API & background threads
│   └── templates/
│       └── index.html             # Neumorphic Light Vibe Web Dashboard
└── esp32/                         # ESP32 Microcontroller Firmware Sketches
    ├── plug_node/
    │   └── plug_node.ino          # Smart Heavy Appliance Plug sketch
    ├── switch_node/
    │   └── switch_node.ino        # Smart Lighting Switch sketch
    └── pzem_node/
        └── pzem_node.ino          # PZEM-004T Main Metering Telemetry sketch
```

---

## 🌐 Web Dashboard Access

Open any web browser on your phone, tablet, or laptop:
- **`http://gridguardpi.local:5000`**
- **`http://10.229.10.171:5000`**

---

### 🛡️ License & Credits
Built for **Genesiz 2026** Project Exhibition. Designed & Developed by GridGuard Engineering Team.
