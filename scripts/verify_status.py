import paramiko
import json
import time

host = "10.99.209.171"
port = 22
user = "gridguardpi"
password = "gridguardpi2026"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port=port, username=user, password=password, timeout=5)

time.sleep(2)
stdin, stdout, stderr = ssh.exec_command("curl -s http://localhost:5000/api/status")
data = json.loads(stdout.read().decode())
print("Live Power on Web API:", data.get("total_power_w"))
print("Live Voltage on Web API:", data.get("total_voltage"))
print("Live Current on Web API:", data.get("total_current_a"))
print("System Link:", data.get("system_link"))
print("Nodes:", data.get("nodes"))

ssh.close()
