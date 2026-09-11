import paramiko
import time
import json

host = "10.99.209.171"
port = 22
user = "gridguardpi"
password = "gridguardpi2026"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port=port, username=user, password=password, timeout=5)

print("Calling POST /api/node/toggle for smart-plug-1...")
stdin, stdout, stderr = ssh.exec_command('curl -s -X POST http://localhost:5000/api/node/toggle -H "Content-Type: application/json" -d \'{"node_id": "smart-plug-1", "action": "TOGGLE"}\'')
print("Toggle response:", stdout.read().decode())

time.sleep(2)
stdin, stdout, stderr = ssh.exec_command("tail -n 15 /home/gridguardpi/gridguard/app.log")
print("=== app.log ===")
print(stdout.read().decode())

ssh.close()
