import urllib.request, urllib.error
try:
    req = urllib.request.Request('http://localhost:8000/health', method='GET')
    print(urllib.request.urlopen(req).read().decode())
except urllib.error.HTTPError as e:
    print('STATUS:', e.code)
    print('BODY:', e.read().decode())
