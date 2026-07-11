import urllib.request, urllib.error
try:
    req = urllib.request.Request('http://localhost:8000/api/v1/auth/login', data=b'{\"email\":\"user@example.com\",\"password\":\"Admin@123\"}', headers={'Content-Type':'application/json'}, method='POST')
    print(urllib.request.urlopen(req).read().decode())
except urllib.error.HTTPError as e:
    print('STATUS:', e.code)
    print('BODY:', e.read().decode())
