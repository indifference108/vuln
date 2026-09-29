#!/usr/bin/env bash
set -u
export PATH="$HOME/node22/bin:$HOME/npm-global/bin:$PATH"
python3 -c 'import requests' 2>/dev/null || pip3 install --quiet --user requests
cp /mnt/c/Users/SYQ/Documents/Kimi/Workspaces/Vuln/scira-ssrf/zaidmukaddam_Scira_SSRF/poc/poc.py ~/scira-test/
cd ~/scira-test/scira
docker start scira-pg scira-redis >/dev/null 2>&1
nohup pnpm dev -p 3000 > /tmp/scira-dev.log 2>&1 &
for i in $(seq 1 40); do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://localhost:3000/ 2>/dev/null)
  [ "$code" != "000" ] && break
  sleep 3
done
curl -s -o /dev/null -w 'warmup:%{http_code}\n' --max-time 120 \
  'http://localhost:3000/api/proxy-image?url=https%3A%2F%2Fhttpbin.org%2Fimage%2Fpng'
TARGET=http://localhost:3000 USE_BURP=0 python3 ~/scira-test/poc.py
RC=$?
pkill -f 'next dev' 2>/dev/null
echo "POC_EXIT=$RC"
