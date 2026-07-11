import urllib.request, urllib.error
try:
    req = urllib.request.Request('http://localhost:8000/docs', method='GET')
    response = urllib.request.urlopen(req)
    print('DOCS STATUS:', response.status)
except urllib.error.HTTPError as e:
    print('STATUS:', e.code)
    print('BODY:', e.read().decode())
