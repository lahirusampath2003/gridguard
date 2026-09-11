import time
import json
import logging
import threading
from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
from gridguard_brain import GridGuardBrain

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
logging.basicConfig(level=logging.INFO)

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# Initialize Brain
brain = GridGuardBrain()
brain.start()

# Background Loop for Timers & Schedules
def background_scheduler_loop():
    while True:
        try:
            brain.check_background_jobs()
        except Exception as e:
            logging.warning(f"Error in background scheduler: {e}")
        time.sleep(1)

scheduler_thread = threading.Thread(target=background_scheduler_loop, daemon=True)
scheduler_thread.start()

# Event Logs List for Web Display
system_logs = []

def add_log(msg):
    timestamp = time.strftime("%H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    system_logs.append(entry)
    if len(system_logs) > 50:
        system_logs.pop(0)

add_log("GridGuard Raspberry Pi Central Hub Initialized.")

# Pre-populate initial demonstration nodes
brain.nodes["smart-plug-1"] = {
    "name": "Heavy Appliance Plug",
    "type": "plug",
    "state": "OFF",
    "power_w": 0.0,
    "last_seen": time.time(),
    "override": False
}

brain.nodes["smart-switch-1"] = {
    "name": "Living Room Lighting Switch",
    "type": "switch",
    "state": "OFF",
    "power_w": 0.0,
    "last_seen": time.time(),
    "override": False
}

brain.nodes["plug-1"] = brain.nodes["smart-plug-1"]
brain.nodes["switch-1"] = brain.nodes["smart-switch-1"]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def get_status():
    # Stale PZEM telemetry fallback (if PZEM stops publishing for > 6 seconds)
    if brain.last_pzem_telemetry_time > 0 and (time.time() - brain.last_pzem_telemetry_time > 6.0):
        brain.total_power_w = 0.0
        brain.total_current_a = 0.0

    is_peak = brain.is_peak_time()
    rem_min, end_str = brain.get_time_until_peak_end()
    tariff_data = brain.get_tariff_analytics()
    
    # Filter nodes for clean display (deduplicate smart-plug-1 / plug-1)
    display_nodes = {}
    for nid, data in brain.nodes.items():
        if nid in ["smart-plug-1", "smart-switch-1"]:
            display_nodes[nid] = data.copy()
            if nid in brain.timers:
                t_data = brain.timers[nid]
                remaining_sec = max(0, int(t_data["expire_time"] - time.time()))
                display_nodes[nid]["timer"] = {
                    "action": t_data["action"],
                    "remaining_sec": remaining_sec,
                    "remaining_str": f"{remaining_sec // 60}m {remaining_sec % 60}s"
                }
            if nid in brain.schedules:
                display_nodes[nid]["schedule"] = brain.schedules[nid]
        elif nid not in ["plug-1", "switch-1"]:
            display_nodes[nid] = data.copy()

    unread_count = sum(1 for n in brain.notifications if not n.get("read", False))

    return jsonify({
        "total_power_w": brain.total_power_w,
        "total_voltage": brain.total_voltage,
        "total_current_a": brain.total_current_a,
        "total_energy_kwh": round(brain.total_energy_kwh, 3),
        "is_peak": is_peak,
        "peak_start_time": brain.peak_start_time,
        "peak_end_time": brain.peak_end_time,
        "time_until_peak_end_min": rem_min,
        "peak_mode": f"PEAK TIME ({brain.peak_start_time} - {brain.peak_end_time})" if is_peak else "OFF-PEAK (NORMAL)",
        "manual_peak_override": brain.manual_peak_override,
        "system_link": "ONLINE" if brain.client.is_connected() else "OFFLINE",
        "nodes": display_nodes,
        "tariff": tariff_data,
        "notifications": brain.notifications,
        "unread_notifications": unread_count,
        "logs": list(reversed(system_logs))
    })

@app.route("/api/tariff_config", methods=["POST"])
def set_tariff_config():
    data = request.json
    start_day = int(data.get("billing_start_day", 1))
    offpeak_rate = float(data.get("offpeak_rate", 25.0))
    peak_rate = float(data.get("peak_rate", 54.0))
    
    brain.billing_start_day = start_day
    brain.tariff_offpeak_rate = offpeak_rate
    brain.tariff_peak_rate = peak_rate
    brain.save_tariff_config()
    
    add_log(f"Updated Tariff Rates: Off-Peak={offpeak_rate}, Peak={peak_rate}, Start Day={start_day}")
    return jsonify({"status": "success", "message": "Tariff settings updated"})

@app.route("/api/node/toggle", methods=["POST"])
def toggle_node():
    data = request.json
    node_id = data.get("node_id")
    action = data.get("action", "TOGGLE")
    
    if node_id in brain.nodes or node_id in ["smart-plug-1", "smart-switch-1", "plug-1", "switch-1"]:
        brain.handle_node_request(node_id, {"action": action})
        add_log(f"Web Dashboard triggered action '{action}' for Node '{node_id}'")
        return jsonify({"status": "success", "message": f"Command sent to {node_id}"})
    return jsonify({"status": "error", "message": "Node not found"}), 404

@app.route("/api/node/override", methods=["POST"])
def override_node():
    data = request.json
    node_id = data.get("node_id")
    
    if node_id in brain.nodes or node_id in ["smart-plug-1", "smart-switch-1", "plug-1", "switch-1"]:
        brain.handle_node_override(node_id, {})
        add_log(f"Web Dashboard activated OVERRIDE for Node '{node_id}'")
        return jsonify({"status": "success", "message": f"Override activated for {node_id}"})
    return jsonify({"status": "error", "message": "Node not found"}), 404

@app.route("/api/node/timer", methods=["POST"])
def set_timer():
    data = request.json
    node_id = data.get("node_id")
    action = data.get("action", "OFF")
    minutes = int(data.get("minutes", 0))
    
    if not node_id:
        return jsonify({"status": "error", "message": "Missing node_id"}), 400
        
    res = brain.set_node_timer(node_id, action, minutes)
    add_log(f"Set {minutes}-min {action} timer for '{node_id}'")
    return jsonify(res)

@app.route("/api/node/schedule", methods=["POST"])
def set_schedule():
    data = request.json
    node_id = data.get("node_id")
    on_time = data.get("on_time")
    off_time = data.get("off_time")
    enabled = data.get("enabled", True)
    
    if not node_id:
        return jsonify({"status": "error", "message": "Missing node_id"}), 400
        
    res = brain.set_node_schedule(node_id, on_time, off_time, enabled)
    add_log(f"Configured daily schedule for '{node_id}': ON={on_time}, OFF={off_time}")
    return jsonify(res)

@app.route("/api/peak_config", methods=["POST"])
def set_peak_config():
    data = request.json
    start_str = data.get("peak_start")
    end_str = data.get("peak_end")
    
    res = brain.set_peak_config(start_str, end_str)
    add_log(f"Updated Peak Time Window: {start_str} to {end_str}")
    return jsonify(res)

@app.route("/api/notifications/delete_one", methods=["POST"])
def delete_one_notification():
    data = request.json
    notif_id = data.get("id")
    res = brain.delete_notification_by_id(notif_id)
    return jsonify(res)

@app.route("/api/notifications/clear", methods=["POST"])
def clear_notifications():
    res = brain.clear_all_notifications()
    return jsonify(res)

@app.route("/api/peak_mode", methods=["POST"])
def set_peak_mode():
    data = request.json
    mode = data.get("mode")
    
    if mode == "FORCE_PEAK":
        brain.manual_peak_override = True
        add_log("Manual Override: Forced PEAK TIME mode ON")
    elif mode == "FORCE_OFFPEAK":
        brain.manual_peak_override = False
        add_log("Manual Override: Forced OFF-PEAK mode ON")
    else:
        brain.manual_peak_override = None
        add_log("System set to AUTO Peak Time mode")
        
    return jsonify({
        "status": "success", 
        "is_peak": brain.is_peak_time(),
        "manual_peak_override": brain.manual_peak_override
    })

@app.route("/api/savings/reset", methods=["POST"])
def reset_savings():
    brain.peak_prevented_kwh = 0.0
    add_log("User reset Peak Savings Counter to LKR 0.00")
    return jsonify({"status": "success", "message": "Savings counter reset successfully"})

@app.route("/api/tariff/demo_reset", methods=["POST"])
def reset_demo_tariff():
    res = brain.reset_demo_energy()
    add_log("Demonstration baseline calibrated (Projected Bill: ~LKR 3,110 / 113 kWh)")
    return jsonify(res)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
