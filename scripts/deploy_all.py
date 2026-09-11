import paramiko

host = "10.99.209.171"
port = 22
user = "gridguardpi"
password = "gridguardpi2026"

local_html = r"D:\University\extra\genesiz 26\gridguard\pi\templates\index.html"
local_brain = r"D:\University\extra\genesiz 26\gridguard\pi\gridguard_brain.py"

print(f"Connecting to {host} to deploy GridGuard brain and templates...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port=port, username=user, password=password, timeout=10)

sftp = ssh.open_sftp()

# Deploy index.html
stdin, stdout, stderr = ssh.exec_command("find /home/gridguardpi/ -name index.html")
html_paths = [p for p in stdout.read().decode().strip().split('\n') if p]
for hp in html_paths:
    print(f"Deploying index.html to {hp}...")
    sftp.put(local_html, hp)

# Deploy gridguard_brain.py
stdin, stdout, stderr = ssh.exec_command("find /home/gridguardpi/ -name gridguard_brain.py")
brain_paths = [p for p in stdout.read().decode().strip().split('\n') if p]
for bp in brain_paths:
    print(f"Deploying gridguard_brain.py to {bp}...")
    sftp.put(local_brain, bp)

sftp.close()

# Restart gridguard service / app
print("Restarting gridguard_brain service...")
stdin, stdout, stderr = ssh.exec_command("echo gridguardpi2026 | sudo -S systemctl restart gridguard_brain.service || echo gridguardpi2026 | sudo -S pkill -f gridguard_brain.py || true")
print("STDOUT:", stdout.read().decode())
print("STDERR:", stderr.read().decode())

ssh.close()
print("All fixes deployed successfully!")
