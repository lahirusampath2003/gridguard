import paramiko

host = "10.99.209.171"
port = 22
user = "gridguardpi"
password = "gridguardpi2026"

local_app = r"D:\University\extra\genesiz 26\gridguard\pi\app.py"
remote_app = "/home/gridguardpi/gridguard/app.py"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port=port, username=user, password=password, timeout=10)

sftp = ssh.open_sftp()
sftp.put(local_app, remote_app)
sftp.close()

# Restart python app
stdin, stdout, stderr = ssh.exec_command("pkill -f python3; cd /home/gridguardpi/gridguard && nohup python3 app.py > app.log 2>&1 &")
print("app.py deployed and restarted successfully.")

ssh.close()
