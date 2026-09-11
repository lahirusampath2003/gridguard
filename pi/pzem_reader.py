import time
import json
import random
import logging
import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] PZEM-Simulator: %(message)s')

class PZEMSimulator:
    """
    Simulates PZEM-004T AC Power Meter telemetry or reads real serial data if available.
    Streams live Voltage, Current, Active Power W, and Energy kWh to MQTT.
    """
    def __init__(self, broker_host="localhost", broker_port=1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client = mqtt.Client(client_id="GridGuard_PZEM_Producer")
        
        self.base_voltage = 230.0
        self.background_power_w = 45.0  # Standby loads (fridge idle, router, LED standby)
        self.active_appliances = {}  # { node_id: power_w }
        self.cumulative_energy_kwh = 1.25

    def set_appliance_power(self, node_id, power_w):
        if power_w > 0:
            self.active_appliances[node_id] = power_w
        else:
            self.active_appliances.pop(node_id, None)

    def publish_reading(self):
        # Calculate total load = background + active node loads + slight noise
        total_active_w = self.background_power_w + sum(self.active_appliances.values())
        voltage = self.base_voltage + random.uniform(-1.5, 1.5)
        current = total_active_w / voltage if voltage > 0 else 0.0
        
        # Accumulate kWh
        self.cumulative_energy_kwh += (total_active_w / 1000.0) * (1.0 / 3600.0)
        
        payload = {
            "voltage": round(voltage, 1),
            "current": round(current, 2),
            "power_w": round(total_active_w, 1),
            "energy_kwh": round(self.cumulative_energy_kwh, 4),
            "frequency_hz": 50.0,
            "power_factor": 0.95,
            "timestamp": time.time()
        }
        
        try:
            self.client.publish("gridguard/sensor/main_power", json.dumps(payload))
            logging.info(f"Published Power Meter: {payload['power_w']} W | {payload['current']} A | {payload['voltage']} V")
        except Exception as e:
            logging.warning(f"PZEM Publish error: {e}")

    def run(self):
        connected = False
        while not connected:
            try:
                self.client.connect(self.broker_host, self.broker_port, 60)
                connected = True
            except Exception as e:
                logging.warning(f"Waiting for MQTT Broker startup ({e}). Retrying in 2 seconds...")
                time.sleep(2)
                
        self.client.loop_start()
        logging.info("PZEM Power Meter Producer started.")
        
        try:
            while True:
                self.publish_reading()
                time.sleep(1.0)
        except KeyboardInterrupt:
            logging.info("Stopping PZEM Producer...")

if __name__ == "__main__":
    pzem = PZEMSimulator()
    pzem.run()
