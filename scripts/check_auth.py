import http.client
import http.cookies
import json

conn = http.client.HTTPConnection('localhost', 8000)
conn.request('GET', '/api/health')
res = conn.getresponse()
print('HEALTH', res.status, res.reason)
print(res.read().decode())

conn = http.client.HTTPConnection('localhost', 8000)
headers = {'Content-Type': 'application/json'}
body = json.dumps({'username': 'user', 'password': 'password'})
conn.request('POST', '/api/login', body, headers)
res = conn.getresponse()
print('LOGIN', res.status, res.reason)
cookies = res.getheader('Set-Cookie')
print('SET-COOKIE', cookies)
print(res.read().decode())

cookie_header = ''
if cookies:
    c = http.cookies.SimpleCookie()
    c.load(cookies)
    cookie_header = '; '.join(f'{m.key}={m.value}' for m in c.values())

conn = http.client.HTTPConnection('localhost', 8000)
conn.request('GET', '/api/session', headers={'Cookie': cookie_header})
res = conn.getresponse()
print('SESSION', res.status, res.reason)
print(res.read().decode())
