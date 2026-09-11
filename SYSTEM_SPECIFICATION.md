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
* **Status**: **100% OPERATIONAL & VERIFIED LIVE**
* **Microcontroller**: ESP32 + PZEM-004T v3.0 AC Power Sensor
* **PZEM RX Pin**: **GPIO 26** (ESP32 RX2, connected to PZEM TX pin)
* **PZEM TX Pin**: **GPIO 27** (ESP32 TX2, connected to PZEM RX pin)
* **🟢 Built-in Status LED (GPIO 2)**: **Network & MQTT Connection Status Indicator** (Solid BLUE = Connected to Pi)
* **High-Voltage AC Screw Terminals (L & N)**: Connected to 230V AC Mains (Live reading: ~226.5V - 236.5V AC).
* **Current Transformer (CT) Pass-Through**: 1 single AC Live wire feeding loads. (Live reading: 6.47A / 1464.7W kettle load).
* **MQTT Topic**: `gridguard/sensor/main_power` (Publishes JSON telemetry every 2 seconds)
* **Verified Live Payload**:
  ```json
  {
    "power_w": 1464.7,
    "current": 6.47,
    "voltage": 226.5
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

4. **Human-in-the-Loop Demand-Response Override Lifecycle**:
   - **Load Intercept**: When a heavy load (>1000W) is detected during peak hours, GridGuard opens the physical relay, sets state to `DELAY`, and turns the dashboard button into a yellow `⚡ OVERRIDE` button.
   - **Override Trigger**: The user can click `⚡ OVERRIDE` on the web dashboard or press the physical device button.
   - **State Protection**: When triggered, GridGuard sends `"OVERRIDE"` to the hardware, closes the relay, marks `override = True`, and updates the UI button to purple `⏻ TURN OFF`. Incoming physical telemetry reports (`{"state": "ON"}`) are shielded so they never overwrite or cancel the `OVERRIDE` state.
   - **Clean Load Termination**: When the user clicks `⏻ TURN OFF` (or when the appliance finishes), the system sends `"OFF"`, opens the relay, and automatically resets `override = False` and state to `OFF`. The system is immediately re-armed for future peak hour load shedding.
   - **Cache Invalidation**: Server-side HTTP headers (`no-cache, no-store, must-revalidate`) and HTML head meta tags ensure browsers always execute the latest control logic without stale script retention.

5. **Electricity Tariff, Bill Prediction & 7-Day History Engine**:
   - Calculates live daily energy usage (kWh), today's cost (LKR), and projects 30-day monthly electricity bill.
   - **Real 7-Day Energy History**: Persists daily energy totals into `daily_history.json` and renders real date labels (`04`, `05`, `06`, ...) on the dashboard bar chart.
   - **Realistic Peak Savings Benchmark**: Intercepted heavy loads calculate energy savings using a standard 30-minute deferred operational cycle benchmark (`min(rem_min, 30) / 60.0`). For a ~1450W kettle, this accurately saves ~0.725 kWh (~21.00 LKR) per intercept rather than assuming 8 straight hours of continuous heating.
   - **Savings Counter Reset**: Includes a one-click reset button (`/api/savings/reset`) to zero out accumulated test savings for live demos.
   - **Tariff Configuration Persistence**: Billing start day and peak/off-peak rates are permanently saved to `tariff_config.json` and automatically populate the settings form on every page load.
   - **Dynamic Gauge Arc**: Radial power dial arc moves dynamically from 0W (empty) up to 3000W (full arc).

---

## 🎨 3. Dashboard UI Architecture (`templates/index.html`)

* **Theme**: Neumorphic Minimalist Light Vibe with Electric Purple (`#7c3aed`) & Amber Accents.
* **Weekly Consumption Trend Y-Axis**: Features a clean, uncluttered Y-axis on the left showing Max, Mid, and 0 `kWh` levels with subtle dashed guide lines across the 7-day bar chart.
* **Device Control Buttons**: Large, high-visibility action pill buttons (`⏻ TURN ON` / `⏻ TURN OFF` / `⚡ OVERRIDE`) with glowing active indicators.
* **Live Timer Countdown Banners**: Whenever a user sets a countdown timer on any device, the device card displays an animated pulsing countdown pill (`⏱️ Turn OFF in 2m 45s`) with a one-click `✕` cancel button, and dynamically updates the `⏱️ Timer` button with the remaining time.
* **High-Contrast Peak Window Bar**: Large, crystal-clear white capsule header featuring deep navy, high-visibility time inputs (`#1e1b4b`, 15px bold font) with soft purple borders, making peak utility window configuration effortlessly legible on all screens.
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

---

## 🎮 5. Standalone Interactive Simulator Architecture (`simulator/`)

* **Primary Launch Point**: [`demo_simulator.html`](demo_simulator.html) or [`simulator/index.html`](simulator/index.html)
* **Execution Environment**: 100% Client-Side In-Memory JavaScript State Machine (No Node.js, Python, or network server required).
* **Virtual Physics & Telemetry**:
  - Standby AC Power: `0.0 W` | `0.00 A` | `230.0 V` (Exact zero-load baseline matching physical PZEM meter).
  - Living Room Lamp (`smart-switch-1`): `25.0 W` | `0.11 A`.
  - Electric Kettle (`smart-plug-1`): `1,500.0 W` | `6.52 A`.
* **Demand-Response Simulation Lifecycle**:
  - Turning on the 1,500W Kettle in Peak Mode triggers a 4-second observation window.
  - Automatically trips the virtual relay to `DELAY`, drops power back to `0.0W`, triggers swipeable alert toast, shifts button to **Yellow `⚡ OVERRIDE`**, and increments the peak money saved counter (+0.25 kWh / +LKR 7.25).
  - Essential 25W lamp is recognized as non-deferrable and is never delayed during peak hours.
* **1-Click Quick Demo Button**:
  - Includes top banner with `⚡ 1-Click Peak Intercept Demo` and `🔄 Reset Demo` for streamlined video recording.

---

## 🛡️ 6. Numerical Safeguards & Calibration Engine

1. **Delta-Time ($\Delta t$) Bounded Integration Safeguard**:
   - In `gridguard_brain.py` (`handle_main_power`), $\Delta t$ between incoming packets is strictly clamped to $\le 3\text{ seconds}$ (`dt_hr = min(dt_hr, 3.0 / 3600.0)`).
   - If the server restarts or network connection pauses while loads are drawing power, the system will never integrate dead time into kilowatt-hours, preventing artificial mathematical spikes.

2. **Demonstration Baseline Calibration API (`/api/tariff/demo_reset`)**:
   - Restores 7-day historical consumption to realistic Sri Lankan home numbers (Day 4: 3.82, Day 5: 4.15, Day 6: 3.90, Day 7: 4.45, Day 8: 3.65, Day 9: 4.10, Today: 2.34 kWh).
   - Projects realistic monthly bill of **LKR 3,112.72** for **113.19 kWh/month** at standard CEB rates.
   - Accessible via the **`🔄 Calibrate Demo`** button on the Tariff Card.

