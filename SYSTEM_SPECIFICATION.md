# 🗂️ GridGuard System Specification & Feature Reference

> **Master Reference File**: This document records the complete hardware pinouts, LED indicators, software functions, MQTT topics, control rules, and UI structure of the **GridGuard Smart Home Energy System**. Whenever new features or hardware modifications are added, this file MUST be updated.

---

## 🛠️ 1. Hardware Pinout & Node Specifications

### 💡 Smart Switch Node (`smart-switch-1` / `switch-1`)
* **Microcontroller**: ESP32
* **Relay Output**: **GPIO 4** (`RELAY_ON_STATE HIGH`, `RELAY_OFF_STATE LOW`)
* **Physical Wall Switch / Button**: **GPIO 18** (`INPUT_PULLUP`, Active-LOW debounce)
* **🟢 External Green LED (GPIO 26)**: **Network & MQTT Connection Status Indicator**
  - *Blinking*: Searching/Connecting to Wi-Fi (`Samsung M14`) or MQTT Broker.
  - *Solid GREEN*: 100% Active & Connected to Raspberry Pi.
* **🔴 External Red LED (GPIO 27)**: **Load & Peak State Indicator**
  - *OFF*: Relay / Load is OFF (Normal OFF).
  - *Solid RED*: Relay / Load is ON (Normal ON).
  - *Fast Blinking RED*: Load is in Peak Delay / Intercept Mode (Demand Response active).
* **MQTT Topics**:
  - Command: `gridguard/nodes/smart-switch-1/command` & `gridguard/nodes/switch-1/command`
  - Status: `gridguard/nodes/smart-switch-1/status` & `gridguard/nodes/switch-1/status`
* **Supported Commands**: `"ON"`, `"OFF"`, `"DELAY"`, `"OVERRIDE"`

---

### 🔌 Smart Plug Node (`smart-plug-1` / `plug-1`)
* **Microcontroller**: ESP32
* **Relay Output**: **GPIO 4** (`RELAY_ON_STATE HIGH`, `RELAY_OFF_STATE LOW`)
* **Physical Push Button**: **GPIO 18** (`INPUT_PULLUP`, Active-LOW)
* **🟢 External Green LED (GPIO 26)**: **Network & MQTT Connection Status Indicator**
* **🔴 External Red LED (GPIO 27)**: **Load & Peak State Indicator**
* **MQTT Topics**:
  - Command: `gridguard/nodes/smart-plug-1/command` & `gridguard/nodes/plug-1/command`
  - Status: `gridguard/nodes/smart-plug-1/status` & `gridguard/nodes/plug-1/status`
* **Supported Commands**: `"ON"`, `"OFF"`, `"DELAY"`, `"OVERRIDE"`

---

### ⚡ Main Metering Node (`pzem-main-meter`)
* **Microcontroller**: ESP32 + PZEM-004T v3.0 AC Power Sensor
* **PZEM RX Pin**: **GPIO 16** (ESP32 RX2, connected to PZEM TX pin)
* **PZEM TX Pin**: **GPIO 17** (ESP32 TX2, connected to PZEM RX pin)
* **🟢 External Green LED (GPIO 26)**: **Network & MQTT Connection Status Indicator** (Solid GREEN = Connected to Pi)
* **High-Voltage AC Screw Terminals (L & N)**: **MUST be connected to 230V AC Mains**. If L/N are disconnected or off, PZEM reports `voltage: 0.0`.
* **Current Transformer (CT) Pass-Through**: **ONLY 1 single AC conductor (Live wire)** feeding the loads must pass through the CT ring. Passing both L and N together cancels out magnetic flux and reads `0.00A`.
* **MQTT Topic**: `gridguard/sensor/main_power` (Publishes JSON telemetry every 2 seconds)
* **Payload Structure**:
  ```json
  {
    "power_w": 1250.5,
    "current": 5.43,
    "voltage": 230.0
  }
  ```

---

## 🧠 2. Central Engine Control Rules & Intelligence (`gridguard_brain.py`)

1. **Autonomous Peak Load Shedding**:
   - Compares current time against Peak Hour window (default: **18:30 to 22:30**).
   - If a heavy appliance (>1000W) turns ON during Peak Hours, GridGuard intercepts it, issues a `"DELAY"` command, and schedules its auto-start for right after peak hours.
   - Critical lighting switches (`smart-switch-1`) are categorized as non-deferrable and are allowed to stay ON.

2. **5-Second Delta-P Disaggregation**:
   - When a node is turned ON, GridGuard records total power baseline before activation.
   - Opens a 5-second ramp-up window, tracks peak delta power, and attributes exact disaggregated wattage (`power_w`) to that specific node.

3. **Web Command Cooldown Lock (Anti-Collision)**:
   - ESP32 nodes enforce a 1.5-second MQTT command lock (`lastMqttTime`) whenever a command is received from the Web Dashboard.
   - Prevents physical button state reads from triggering false toggles right after a web action.

4. **Human-in-the-Loop Override**:
   - Physical button presses, user countdown timers, or explicit web "Override" actions send `"OVERRIDE"` / `"ON"`, bypassing peak blocks.

5. **Electricity Tariff & Bill Prediction Engine**:
   - Calculates live daily energy usage (kWh), today's estimated cost (LKR), and projects 30-day monthly electricity bill.
   - Tracks **GridGuard Savings**: Accumulates money (LKR) and shifted energy (kWh) prevented from peak hour billing.

---

## 🎨 3. Dashboard UI Architecture (`templates/index.html`)

* **Theme**: Neumorphic Minimalist Light Vibe with Electric Purple (`#7c3aed`) & Amber Accents.
* **Device Control Buttons**: Large, high-visibility action pill buttons (`⏻ TURN ON` / `⏻ TURN OFF` / `⚡ OVERRIDE`) with glowing active indicators.
* **Dual Responsive Layout**:
  - **Desktop / Laptop (`>768px`)**: Left Icon Sidebar + Center Radial Hero Power Dial & Daily Bar Chart + Right Presets Panel.
  - **Mobile Smartphone (`<=768px`)**: Native Floating Bottom Navigation Bar (`🏠 Home`, `📊 Tariff`, `📜 Logs`, `🔔 Alerts`).

---

## 📋 4. Default System Credentials & Paths

* **Raspberry Pi Hostname**: `gridguardpi.local`
* **Raspberry Pi Current IP**: `10.99.209.171`
* **Wi-Fi SSID**: `Samsung M14` | **Password**: `deminiuom124`
* **Raspberry Pi SSH Login**: Username `gridguardpi` | Password `gridguardpi2026`
* **Web Dashboard URL**: `http://10.99.209.171:5000` or `http://gridguardpi.local:5000`
* **Local Workspace**: `D:\University\extra\genesiz 26\gridguard\`
* **Pi Deployment Path**: `/home/gridguardpi/gridguard/`
