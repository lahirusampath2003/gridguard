# Co-Author: Kavishka Shanilka (@kavishshanilka)
# Co-Author: Lahiru Sampath (@lahirusampath2003)
import time
import json
import logging
import os
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt

# Configure Logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

class GridGuardBrain:
    def __init__(self, broker_host="localhost", broker_port=1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        
        # Grid Peak Hour Configuration (Default: 18:30 to 22:30)
        self.peak_start_time = "18:30"
        self.peak_end_time = "22:30"
        self.manual_peak_override = None  # None: Auto Time, True: Force Peak, False: Force Off-Peak
        
        # Heavy Load Protection Threshold (1000 Watts)
        self.heavy_load_threshold_w = 1000.0

        # Total Grid Power & Telemetry
        self.total_power_w = 0.0
        self.total_voltage = 230.0
        self.total_current_a = 0.0
        self.total_energy_kwh = 0.05  # Accumulated energy counter
        
        # Energy & Tariff Analytics
        self.billing_start_day = 1
        self.tariff_offpeak_rate = 25.0  # Cost per kWh in Off-Peak
        self.tariff_peak_rate = 54.0     # Cost per kWh in Peak Hours
        self.peak_prevented_kwh = 0.0    # Reset to 0.0 (Real accumulated shifted energy)
        self.load_tariff_config()
        
        # 7-Day Daily Consumption History Tracker
        self.daily_history = {}
        self.load_daily_history()

        # Node tracking dictionary
        self.nodes = {}
        
        # Notifications List
        self.notifications = []
        
        # Node Countdown Timers
        self.timers = {}
        
        # Node Schedules
        self.schedules = {}
        self.load_schedules_from_file()

        # Delta P Disaggregation state
        self.pending_node_action = None 
        self.prev_total_power = 0.0
        self.last_energy_calc_time = time.time()
        self.last_pzem_telemetry_time = time.time()  # Tracks when last live PZEM packet arrived

        # MQTT Client Initialization
        self.client = mqtt.Client(client_id=f"GridGuard_Pi_Brain_{os.getpid()}_{int(time.time())}")
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

    def add_notification(self, title, message, notif_type="warning", node_id=None, time_to_peak_end_min=None, peak_end_str=None, power_w=None):
        notif = {
            "id": f"notif_{int(time.time()*1000)}",
            "title": title,
            "message": message,
            "type": notif_type,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "read": False,
            "node_id": node_id,
            "time_to_peak_end_min": time_to_peak_end_min,
            "peak_end_str": peak_end_str,
            "power_w": power_w
        }
        self.notifications.insert(0, notif)
        if len(self.notifications) > 50:
            self.notifications = self.notifications[:50]
        logging.info(f"[NOTIF] {title}: {message}")

    def delete_notification_by_id(self, notif_id):
        self.notifications = [n for n in self.notifications if n.get("id") != notif_id]
        return {"status": "success", "message": f"Notification {notif_id} deleted"}

    def clear_all_notifications(self):
        self.notifications.clear()
        return {"status": "success", "message": "All notifications cleared"}

    def set_peak_config(self, start_str, end_str):
        try:
            datetime.strptime(start_str, "%H:%M")
            datetime.strptime(end_str, "%H:%M")
            self.peak_start_time = start_str
            self.peak_end_time = end_str
            self.add_notification(
                title="⚙️ Peak Hours Updated",
                message=f"Window: {start_str} - {end_str}",
                notif_type="info"
            )
            return {"status": "success", "peak_start": start_str, "peak_end": end_str}
        except Exception as e:
            return {"status": "error", "message": f"Invalid time format: {e}"}

    def is_peak_time(self):
        if self.manual_peak_override is not None:
            return self.manual_peak_override
        
        now = datetime.now()
        sh, sm = map(int, self.peak_start_time.split(":"))
        eh, em = map(int, self.peak_end_time.split(":"))
        
        peak_start = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
        peak_end = now.replace(hour=eh, minute=em, second=0, microsecond=0)
        
        if peak_end < peak_start:
            return now >= peak_start or now <= peak_end
        return peak_start <= now <= peak_end

    def get_time_until_peak_end(self):
        now = datetime.now()
        eh, em = map(int, self.peak_end_time.split(":"))
        peak_end = now.replace(hour=eh, minute=em, second=0, microsecond=0)
        
        if peak_end < now:
            peak_end += timedelta(days=1)
            
        diff_sec = (peak_end - now).total_seconds()
        diff_min = max(1, int(diff_sec // 60))
        return diff_min, self.peak_end_time

    def get_tariff_analytics(self):
        """Calculates live cost predictions, monthly projections, and peak savings."""
        now = datetime.now()
        days_in_month = 30
        
        # Calculate energy accumulated today
        today_str = now.strftime("%Y-%m-%d")
        today_kwh = self.daily_history.get(today_str, self.total_energy_kwh)
        
        curr_rate = self.tariff_peak_rate if self.is_peak_time() else self.tariff_offpeak_rate
        today_cost = today_kwh * curr_rate
        
        # Monthly Prediction using recorded daily history average
        valid_days = [v for k, v in self.daily_history.items() if v > 0]
        if valid_days:
            avg_daily_kwh = sum(valid_days) / len(valid_days)
        else:
            avg_daily_kwh = max(1.0, today_kwh)
            
        projected_monthly_kwh = round(avg_daily_kwh * days_in_month, 2)
        projected_monthly_cost = round(projected_monthly_kwh * ((self.tariff_offpeak_rate + self.tariff_peak_rate) / 2), 2)
        
        # Money saved by GridGuard demand response intercept
        savings_per_kwh = max(1.0, self.tariff_peak_rate - self.tariff_offpeak_rate)
        saved_money = round(self.peak_prevented_kwh * savings_per_kwh, 2)

        return {
            "current_kwh": round(today_kwh, 3),
            "today_cost": round(today_cost, 2),
            "billing_start_day": self.billing_start_day,
            "offpeak_rate": self.tariff_offpeak_rate,
            "peak_rate": self.tariff_peak_rate,
            "projected_monthly_kwh": projected_monthly_kwh,
            "projected_monthly_cost": projected_monthly_cost,
            "peak_prevented_kwh": round(self.peak_prevented_kwh, 3),
            "saved_money": saved_money,
            "daily_history": self.get_last_7_days_history()
        }

    def reset_demo_energy(self):
        """Calibrates 7-day history and today energy to realistic Sri Lankan home demonstration values."""
        today = datetime.now().date()
        demo_data = [
            (6, 3.82),
            (5, 4.15),
            (4, 3.90),
            (3, 4.45),
            (2, 3.65),
            (1, 4.10),
            (0, 2.34) # Today
        ]
        self.daily_history = {}
        for days_ago, val in demo_data:
            d_str = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            self.daily_history[d_str] = val
            
        self.total_energy_kwh = 2.34
        self.peak_prevented_kwh = 1.85
        self.save_daily_history()
        logging.info("[DEMO CALIBRATION] Reset daily history and energy to realistic demo values.")
        return {"status": "success", "message": "Demo data calibrated successfully"}

    def load_daily_history(self):
        filepath = "/home/gridguardpi/gridguard/daily_history.json"
        if not os.path.exists(filepath):
            filepath = "daily_history.json"
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    self.daily_history = json.load(f)
            except Exception as e:
                logging.warning(f"Could not load daily history: {e}")
                
        today_str = datetime.now().strftime("%Y-%m-%d")
        if today_str in self.daily_history:
            self.total_energy_kwh = round(self.daily_history[today_str], 3)

    def save_daily_history(self):
        filepath = "/home/gridguardpi/gridguard/daily_history.json"
        try:
            with open(filepath, "w") as f:
                json.dump(self.daily_history, f, indent=2)
        except Exception:
            try:
                with open("daily_history.json", "w") as f:
                    json.dump(self.daily_history, f, indent=2)
            except Exception:
                pass

    def load_tariff_config(self):
        filepath = "/home/gridguardpi/gridguard/tariff_config.json"
        if not os.path.exists(filepath):
            filepath = "tariff_config.json"
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                    self.billing_start_day = int(data.get("billing_start_day", 1))
                    self.tariff_offpeak_rate = float(data.get("offpeak_rate", 25.0))
                    self.tariff_peak_rate = float(data.get("peak_rate", 54.0))
            except Exception as e:
                logging.warning(f"Could not load tariff config: {e}")

    def save_tariff_config(self):
        filepath = "/home/gridguardpi/gridguard/tariff_config.json"
        data = {
            "billing_start_day": self.billing_start_day,
            "offpeak_rate": self.tariff_offpeak_rate,
            "peak_rate": self.tariff_peak_rate
        }
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            try:
                with open("tariff_config.json", "w") as f:
                    json.dump(data, f, indent=2)
            except Exception:
                pass

    def get_last_7_days_history(self):
        """Returns the last 7 calendar days of real consumption in kWh."""
        today = datetime.now().date()
        result = []
        for i in range(6, -1, -1):
            day_date = today - timedelta(days=i)
            day_str = day_date.strftime("%Y-%m-%d")
            day_label = day_date.strftime("%d")
            kwh = round(self.daily_history.get(day_str, 0.0), 3)
            result.append({
                "date": day_str,
                "label": day_label,
                "kwh": kwh,
                "is_today": (i == 0)
            })
        return result

    def load_schedules_from_file(self):
        filepath = "/home/gridguardpi/gridguard/schedules.json"
        if not os.path.exists(filepath):
            filepath = "schedules.json"
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    self.schedules = json.load(f)
            except Exception as e:
                logging.warning(f"Could not load schedules: {e}")

    def save_schedules_to_file(self):
        filepath = "/home/gridguardpi/gridguard/schedules.json"
        try:
            with open(filepath, "w") as f:
                json.dump(self.schedules, f, indent=2)
        except Exception as e:
            try:
                with open("schedules.json", "w") as f:
                    json.dump(self.schedules, f, indent=2)
            except Exception:
                pass

    def set_node_timer(self, node_id, action, minutes):
        if minutes <= 0:
            self.timers.pop(node_id, None)
            return {"status": "cancelled", "message": f"Timer cancelled for {node_id}"}
        
        expire = time.time() + (minutes * 60)
        self.timers[node_id] = {
            "action": action,
            "expire_time": expire,
            "duration_min": minutes
        }
        name = self.nodes.get(node_id, {}).get("name", node_id)
        self.add_notification("Timer Set ⏱️", f"{name}: Turn {action} in {minutes} min.", notif_type="info")
        return {"status": "success", "message": f"Timer set to turn {action} {node_id} in {minutes} mins"}

    def set_node_schedule(self, node_id, on_time, off_time, enabled=True):
        self.schedules[node_id] = {
            "on_time": on_time,
            "off_time": off_time,
            "enabled": enabled
        }
        self.save_schedules_to_file()
        name = self.nodes.get(node_id, {}).get("name", node_id)
        self.add_notification("Schedule Set 📅", f"{name}: ON at {on_time}, OFF at {off_time}.", notif_type="info")
        return {"status": "success", "message": "Schedule updated successfully"}

    def on_connect(self, client, userdata, flags, rc):
        logging.info(f"Connected to MQTT Broker with result code {rc}")
        self.client.subscribe("gridguard/sensor/main_power")
        self.client.subscribe("gridguard/nodes/+/telemetry")
        self.client.subscribe("gridguard/nodes/+/status")
        self.client.subscribe("gridguard/nodes/+/request")
        self.client.subscribe("gridguard/nodes/+/override")
        self.client.subscribe("gridguard/nodes/+/event")

    def on_disconnect(self, client, userdata, rc):
        logging.warning(f"[MQTT] Disconnected from MQTT Broker (rc={rc}). Auto-reconnect active.")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload_str = msg.payload.decode("utf-8")
            
            try:
                payload = json.loads(payload_str)
            except Exception:
                payload = {"raw": payload_str}

            if topic == "gridguard/sensor/main_power":
                self.handle_main_power(payload)
            elif "/telemetry" in topic or "/status" in topic:
                node_id = topic.split("/")[2]
                self.handle_node_status(node_id, payload)
            elif "/request" in topic or "/event" in topic:
                node_id = topic.split("/")[2]
                self.handle_node_request(node_id, payload)
            elif "/override" in topic:
                node_id = topic.split("/")[2]
                self.handle_node_override(node_id, payload)
        except Exception as e:
            logging.error(f"Unexpected error in on_message: {e}", exc_info=True)

    def handle_main_power(self, data):
        self.last_pzem_telemetry_time = time.time()
        new_power = data.get("power_w", 0.0)
        self.total_voltage = data.get("voltage", 230.0)
        self.total_current_a = data.get("current", 0.0)
        
        # Real-time energy integration
        now = time.time()
        dt_hr = (now - self.last_energy_calc_time) / 3600.0
        self.last_energy_calc_time = now
        
        # Safeguard: clamp dt_hr to max 3 seconds to prevent integration jumps during restarts or pauses
        if dt_hr > (3.0 / 3600.0):
            dt_hr = 1.0 / 3600.0
        
        if new_power > 0 and dt_hr > 0:
            added_kwh = (new_power / 1000.0) * dt_hr
            self.total_energy_kwh += added_kwh

            today_str = datetime.now().strftime("%Y-%m-%d")
            self.daily_history[today_str] = round(self.daily_history.get(today_str, 0.0) + added_kwh, 4)
            self.save_daily_history()

        self.total_power_w = new_power

        # True 5-Second Ramp-Up Delta-P Attribution Window
        if self.pending_node_action:
            elapsed = now - self.pending_node_action["start_time"]
            nid = self.pending_node_action["node_id"]
            baseline = self.pending_node_action["baseline_power"]
            
            current_delta = max(0.0, new_power - baseline)
            
            if current_delta > self.pending_node_action["peak_delta"]:
                self.pending_node_action["peak_delta"] = current_delta

            if nid in self.nodes:
                self.nodes[nid]["power_w"] = round(self.pending_node_action["peak_delta"], 1)

            # Close ramp-up window after 5 seconds & Evaluate Peak Hour Protection
            if elapsed >= 5.0:
                peak_w = self.nodes[nid]["power_w"]
                logging.info(f"[Delta-P Disaggregation] Measured {peak_w}W for Node '{nid}'")
                
                if self.is_peak_time() and peak_w > self.heavy_load_threshold_w and not self.nodes[nid].get("override", False):
                    name = self.nodes[nid].get("name", nid)
                    rem_min, end_str = self.get_time_until_peak_end()
                    
                    logging.info(f"[PEAK DEMAND RESPONSE] Heavy Load ({peak_w}W > 1000W) Intercepted for '{nid}'! Peak ends in {rem_min} mins.")
                    
                    # Accumulate peak prevented energy stats ONCE per intercept BEFORE send_command sets pending_node_action to None
                    if self.pending_node_action and not self.pending_node_action.get("intercept_counted", False):
                        self.pending_node_action["intercept_counted"] = True
                        # Benchmark standard deferred appliance operational cycle: 30 minutes (0.5 hours)
                        shifted_hours = min(rem_min, 30) / 60.0
                        self.peak_prevented_kwh += (peak_w / 1000.0) * shifted_hours
                    
                    self.send_command(nid, "DELAY", reason=f"Heavy Load ({peak_w}W > 1000W) Intercepted during Peak Hours")
                    
                    self.add_notification(
                        title=f"⚠️ Intercepted: {name}",
                        message=f"Power: {peak_w} W | Peak ends in {rem_min} mins (at {end_str})",
                        notif_type="warning",
                        node_id=nid,
                        time_to_peak_end_min=rem_min,
                        peak_end_str=end_str,
                        power_w=peak_w
                    )
                
                self.pending_node_action = None

        # Ensure OFF nodes are strictly 0W
        for nid, ndata in self.nodes.items():
            if ndata.get("state") == "OFF":
                ndata["power_w"] = 0.0

        self.prev_total_power = new_power

    def handle_node_status(self, node_id, data):
        node_type = "plug" if "plug" in node_id or (isinstance(data, dict) and data.get("type") in ["plug", "smart_plug"]) else "switch"
        
        # Robust status parsing supporting JSON dict and raw string payloads
        if isinstance(data, dict):
            raw_relay = data.get("state") or data.get("relay") or data.get("raw") or "OFF"
        else:
            raw_relay = str(data)

        raw_str = str(raw_relay).upper()
        if "DELAY" in raw_str:
            state = "DELAY"
        elif "OVERRIDE" in raw_str:
            state = "OVERRIDE"
        elif any(w in raw_str for w in ["CLOSED", "ON", "TRUE", "HIGH", "1"]):
            if self.nodes.get(node_id, {}).get("override", False):
                state = "OVERRIDE"
            else:
                state = "ON"
        else:
            # If the node is currently in DELAY mode (waiting for user override during peak hours),
            # do not overwrite DELAY with OFF when the physical relay switches OFF!
            current_local_state = self.nodes.get(node_id, {}).get("state", "OFF")
            if current_local_state == "DELAY":
                state = "DELAY"
            else:
                state = "OFF"
            
        name = "Heavy Appliance Plug" if node_type == "plug" else "Living Room Lighting Switch"
        
        if node_id not in self.nodes:
            self.nodes[node_id] = {
                "name": name,
                "type": node_type,
                "state": state,
                "power_w": 0.0,
                "last_seen": time.time(),
                "override": False
            }
        else:
            self.nodes[node_id]["last_seen"] = time.time()
            self.nodes[node_id]["state"] = state
            self.nodes[node_id]["name"] = name

    def handle_node_request(self, node_id, data):
        node_type = self.nodes.get(node_id, {}).get("type", "plug" if "plug" in node_id else "switch")
        current_state = self.nodes.get(node_id, {}).get("state", "OFF")

        if node_type == "switch" or "switch" in node_id:
            target = "ON" if current_state == "OFF" else "OFF"
            self.send_command(node_id, target, reason="Critical Load Immediate Execution")
            return

        if current_state in ["ON", "OVERRIDE"]:
            self.send_command(node_id, "OFF", reason="User Turn OFF")
        elif current_state == "DELAY":
            self.handle_node_override(node_id, data)
        else:
            self.send_command(node_id, "ON", reason="Initial Load Start & Power Check")

    def handle_node_override(self, node_id, data):
        logging.info(f"[OVERRIDE] Human-in-the-Loop Override triggered for Node '{node_id}'")
        targets = [node_id]
        if node_id == "plug-1": targets.append("smart-plug-1")
        elif node_id == "smart-plug-1": targets.append("plug-1")
        for tid in set(targets):
            if tid in self.nodes:
                self.nodes[tid]["override"] = True
                self.nodes[tid]["state"] = "OVERRIDE"
        self.send_command(node_id, "OVERRIDE", reason="Human Push-Button Override")
        name = self.nodes.get(node_id, {}).get("name", node_id)
        self.add_notification(
            title=f"⚡ Override: {name}",
            message="Appliance forced ON during peak hours.",
            notif_type="info"
        )

    def send_command(self, node_id, command, reason=""):
        if not self.client.is_connected():
            try:
                logging.warning("[MQTT] Client disconnected before command execution. Attempting reconnect...")
                self.client.reconnect()
            except Exception as e:
                logging.error(f"[MQTT] Reconnect failed during send_command: {e}")

        targets = [node_id]
        if node_id == "plug-1": targets.append("smart-plug-1")
        elif node_id == "smart-plug-1": targets.append("plug-1")
        elif node_id == "switch-1": targets.append("smart-switch-1")
        elif node_id == "smart-switch-1": targets.append("switch-1")

        for target_id in set(targets):
            topic_cmd = f"gridguard/nodes/{target_id}/command"
            topic_ctrl = f"gridguard/nodes/{target_id}/control"
            self.client.publish(topic_cmd, command)
            self.client.publish(topic_ctrl, command)
            if command == "DELAY":
                # Ensure firmware that only listens for OFF physically opens the relay
                self.client.publish(topic_ctrl, "OFF")

        primary_id = node_id
        if command in ["ON", "OVERRIDE"]:
            if command == "OVERRIDE":
                for tid in set(targets):
                    if tid in self.nodes:
                        self.nodes[tid]["override"] = True
            
            # Start 5-second Ramp-Up Window
            self.pending_node_action = {
                "node_id": primary_id,
                "baseline_power": self.total_power_w,
                "start_time": time.time(),
                "peak_delta": 0.0
            }
            for tid in set(targets):
                if tid in self.nodes:
                    self.nodes[tid]["state"] = "OVERRIDE" if command == "OVERRIDE" else "ON"
        elif command == "OFF":
            self.pending_node_action = None
            for tid in set(targets):
                if tid in self.nodes:
                    self.nodes[tid]["state"] = "OFF"
                    self.nodes[tid]["power_w"] = 0.0
                    self.nodes[tid]["override"] = False
        elif command == "DELAY":
            self.pending_node_action = None
            for tid in set(targets):
                if tid in self.nodes:
                    self.nodes[tid]["state"] = "DELAY"
                    self.nodes[tid]["power_w"] = 0.0

    def check_background_jobs(self):
        """Evaluates active node timers and daily ON/OFF schedules every second."""
        now_time = time.time()
        curr_hm = datetime.now().strftime("%H:%M")

        # 1. Evaluate Timers
        expired_timers = []
        for nid, timer_data in list(self.timers.items()):
            if now_time >= timer_data["expire_time"]:
                target_action = timer_data["action"]
                name = self.nodes.get(nid, {}).get("name", nid)
                node_type = self.nodes.get(nid, {}).get("type", "plug" if "plug" in nid else "switch")
                
                logging.info(f"[TIMER EXPIRED] Executing {target_action} for node {nid}")
                
                if target_action == "ON":
                    exec_cmd = "ON" if node_type == "switch" or "switch" in nid else "OVERRIDE"
                else:
                    exec_cmd = "OFF"
                    
                self.send_command(nid, exec_cmd, reason="User Countdown Timer Execution")
                
                self.add_notification(
                    title=f"⏱️ Timer Finished: {name}",
                    message=f"Turned {target_action} as scheduled.",
                    notif_type="success"
                )
                expired_timers.append(nid)

        for nid in expired_timers:
            self.timers.pop(nid, None)

        # 2. Evaluate Schedules
        for nid, sched in self.schedules.items():
            if not sched.get("enabled", True):
                continue
            
            on_t = sched.get("on_time")
            off_t = sched.get("off_time")
            node_type = self.nodes.get(nid, {}).get("type", "plug" if "plug" in nid else "switch")
            
            if on_t and curr_hm == on_t:
                last_exec = sched.get("last_on_exec")
                if last_exec != curr_hm:
                    sched["last_on_exec"] = curr_hm
                    name = self.nodes.get(nid, {}).get("name", nid)
                    logging.info(f"[SCHEDULE MATCH] Turning ON node {nid} at {on_t}")
                    
                    exec_cmd = "ON" if node_type == "switch" or "switch" in nid else "OVERRIDE"
                    self.send_command(nid, exec_cmd, reason=f"User Daily Schedule ({on_t})")
                    self.add_notification(
                        title=f"📅 Schedule Triggered: {name}",
                        message=f"Turned ON at {on_t}.",
                        notif_type="info"
                    )

            if off_t and curr_hm == off_t:
                last_exec = sched.get("last_off_exec")
                if last_exec != curr_hm:
                    sched["last_off_exec"] = curr_hm
                    name = self.nodes.get(nid, {}).get("name", nid)
                    logging.info(f"[SCHEDULE MATCH] Turning OFF node {nid} at {off_t}")
                    self.send_command(nid, "OFF", reason=f"User Daily Schedule ({off_t})")
                    self.add_notification(
                        title=f"📅 Schedule Triggered: {name}",
                        message=f"Turned OFF at {off_t}.",
                        notif_type="info"
                    )

        # 3. Evaluate Stale Telemetry Timeout (If PZEM stops publishing for > 6 seconds, reset live power to 0.0W)
        if self.last_pzem_telemetry_time > 0 and (now_time - self.last_pzem_telemetry_time > 6.0):
            self.total_power_w = 0.0
            self.total_current_a = 0.0

    def start(self):
        def _connect_loop():
            connected = False
            while not connected:
                try:
                    self.client.connect(self.broker_host, self.broker_port, 60)
                    connected = True
                except Exception as e:
                    logging.warning(f"Waiting for Mosquitto MQTT Broker ({e}). Retrying in 2 seconds...")
                    time.sleep(2)
            self.client.loop_start()
            logging.info("GridGuard Mastermind Engine started successfully.")

        import threading
        t = threading.Thread(target=_connect_loop, daemon=True)
        t.start()

if __name__ == "__main__":
    brain = GridGuardBrain()
    brain.start()
    try:
        while True:
            brain.check_background_jobs()
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping GridGuard Brain...")
