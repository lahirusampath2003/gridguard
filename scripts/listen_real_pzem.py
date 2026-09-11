import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect('10.181.248.171', username='gridguardpi', password='gridguardpi2026', timeout=5)
    print("Connected to Pi. Stopping PZEM background simulator...")
    ssh.exec_command('pkill -f pzem_reader.py')
    
    print("Listening to LIVE hardware MQTT readings on 'gridguard/sensor/main_power'...")
    _, o, _ = ssh.exec_command('mosquitto_sub -t gridguard/sensor/main_power -v -W 15')
    print("LIVE MQTT OUTPUT:\n", o.read().decode('utf-8', errors='ignore'))
    ssh.close()
except Exception as e:
    print("Pi Connection Notice:", e)
