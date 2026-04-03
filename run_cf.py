import subprocess
import re

p = subprocess.Popen(['.\\cloudflared.exe', 'tunnel', '--url', 'http://127.0.0.1:8000'], stderr=subprocess.PIPE, text=True)

for line in iter(p.stderr.readline, ''):
    match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
    if match:
        with open('cf_url.txt', 'w') as f:
            f.write(match.group(0))
        break
