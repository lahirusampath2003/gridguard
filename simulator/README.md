# ⚡ GridGuard Standalone Interactive Simulator

> 🎮 **Zero-Hardware Presentation Hub**: Run the complete GridGuard Smart Demand-Response experience directly in any web browser without needing the Raspberry Pi, ESP32 nodes, or PZEM power meter connected!

---

## 🚀 How to Run (1-Click)

No server or installation required! 

1. **Option A (Direct Double-Click):**
   - Double-click [`demo_simulator.html`](../demo_simulator.html) or [`simulator/index.html`](index.html).
   - It opens instantly in your default web browser (Chrome, Edge, Firefox, Safari).

2. **Option B (Local HTTP Server if desired):**
   ```bash
   cd "D:\University\extra\genesiz 26\gridguard\simulator"
   python -m http.server 8000
   ```
   Then open `http://localhost:8000` in your browser.

---

## 🌟 Interactive Demonstration Capabilities

The simulator runs an in-memory client-side physics and demand-response engine that faithfully reproduces the exact state machine from `gridguard_brain.py`:

| Feature | Behavior in Simulator |
| :--- | :--- |
| **🔌 Standby Background Load** | Reads strictly **0.0 W** and **0.00 A** when appliances are OFF, exactly matching the physical PZEM meter. |
| **💡 Light Bulb (Smart Switch 1)** | Rated at **25.0W**. When turned ON during Peak Hours, it is **never delayed** (essential load < 1000W). |
| **⚡ Electric Kettle (Smart Plug 1)** | Rated at **1,500.0W**. When turned ON during Peak Hours, the engine analyzes the 5-second ramp-up delta, intercepts the surge, clicks the virtual relay OFF, triggers the **⚠️ Intercepted** alert, and transforms the button to the **Yellow OVERRIDE** button! |
| **🔄 Seamless User Override** | Clicking the Yellow **⚡ OVERRIDE** button immediately re-engages power and turns the kettle back ON. |
| **⏱️ Live Countdown Timers** | Setting a 15m, 30m, 60m, or custom timer shows the animated **⏱️ Turn OFF in Xm Ys [✕]** pill with pulsing dot indicator and instant cancel. |
| **📅 Daily Schedules** | Configurable auto ON/OFF daily schedules. |
| **📊 Tariff & Bill Forecasting** | Displays realistic Sri Lankan household figures: **LKR 3,112.72 projected bill**, **113.19 kWh/month**, 7-day weekly trend bar chart with Y-axis guide lines. |
| **📜 Real-time System Event Log** | Terminal prints timestamped events for every toggle, delta-P measurement, intercept, and override. |
| **⚡ 1-Click Peak Intercept Demo** | Convenient button in the top banner that forces peak mode and fires the kettle to show evaluators the complete autonomous sequence in 5 seconds. |

---

## 🎬 Step-by-Step Demo Flow for Video or Presentations

1. **Show Normal Operation:**
   - Tap **Turn ON** on the **Light Bulb (Smart Switch 1)**.
   - Note the power dial updates from 0W to **25W** (+25W).
   - The bulb stays ON smoothly without any delay.

2. **Demonstrate Autonomous Peak Demand-Response:**
   - Click the top banner button: **"⚡ 1-Click Peak Intercept Demo"** (or select **"Force Peak"** and click **"Turn ON"** on the Kettle).
   - Watch the power dial jump to **1,500W** (kettle surge).
   - In 4 seconds, the autonomous engine triggers:
     - The kettle relay clicks OFF (state changes to `DELAY`).
     - Power returns to normal.
     - A notification toast pops up: `⚠️ Intercepted: Electric Kettle | Power: 1500 W | Peak ends in 180 mins`.
     - The button transforms into the **Yellow ⚡ OVERRIDE** button.
     - The Peak Savings Counter increments (+0.25 kWh / +LKR 7.25 saved).

3. **Demonstrate User-First Override:**
   - Click the **Yellow ⚡ OVERRIDE** button.
   - Kettle turns back ON, power returns to 1,500W, and button becomes `Turn OFF`.

4. **Showcase Tariff & Bill Prediction:**
   - Click the **Tariff** tab (or bottom bar on mobile).
   - Showcase the **LKR 3,112 Projected Bill**, the clean 7-day Weekly Trend chart with Y-axis levels, and the customizable Time-of-Use rates.
   - Click **🔄 Calibrate Demo** to reset baseline values anytime.

---

### 🛡️ Developed for Genesiz 2026
GridGuard — Autonomous Demand-Response & Smart Home Energy Engine.
