import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.181.248.171', username='gridguardpi', password='gridguardpi2026')

def safe_print(title, text):
    print(f"\n--- {title} ---")
    clean_text = text.encode('ascii', 'ignore').decode('ascii')
    print(clean_text.strip())

_, o, _ = ssh.exec_command('sudo systemctl status mosquitto')
safe_print("1. Mosquitto Service Status", o.read().decode('utf-8', errors='ignore'))

_, o, _ = ssh.exec_command('cat /etc/mosquitto/conf.d/local.conf')
safe_print("2. Mosquitto Config File", o.read().decode('utf-8', errors='ignore'))

print("\n--- 3. Pinging ESP32 Nodes from Pi ---")
for ip in ["10.181.248.77", "10.181.248.216", "10.181.248.72"]:
    _, o, _ = ssh.exec_command(f'ping -c 2 -w 2 {ip}')
    res = o.read().decode('utf-8', errors='ignore')
    if "bytes from" in res:
        print(f"  [REACHABLE] ESP32 at {ip}")
    else:
        print(f"  [UNREACHABLE] ESP32 at {ip}")

_, o, _ = ssh.exec_command('sudo ss -tulpn | grep 1883')
safe_print("4. Active Mosquitto Listening Ports", o.read().decode('utf-8', errors='ignore'))

ssh.close()
