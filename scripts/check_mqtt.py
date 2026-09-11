import paramiko

host = "10.99.209.171"
port = 22
user = "gridguardpi"
password = "gridguardpi2026"

print("Connecting to Pi to check Mosquitto broker and MQTT traffic...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port=port, username=user, password=password, timeout=10)

# Check Mosquitto status
stdin, stdout, stderr = ssh.exec_command("systemctl status mosquitto | head -n 10")
out = stdout.read().decode('utf-8', errors='ignore')
print("MOSQUITTO STATUS:\n", out.encode('ascii', errors='ignore').decode())

# Subscribe to main_power topic for 5 seconds using mosquitto_sub
stdin, stdout, stderr = ssh.exec_command("timeout 5 mosquitto_sub -t 'gridguard/sensor/main_power' || echo 'No MQTT messages received within 5 seconds'")
out2 = stdout.read().decode('utf-8', errors='ignore')
print("MQTT MESSAGES RECEIVED:\n", out2.encode('ascii', errors='ignore').decode())

ssh.close()
