import urllib.request
import urllib.parse
import json
import urllib.error
import re

BASE = 'http://localhost:8000'

def get(path):
    try:
        req = urllib.request.Request(f'{BASE}{path}')
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())
    except Exception as e:
        return None, str(e)

def post_form(path, fields):
    boundary = '----FormBoundary7MA4YWxkTrZu0gW'
    body = b''
    for k, v in fields.items():
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    body += f'--{boundary}--\r\n'.encode()
    headers = {
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'Content-Length': str(len(body)),
    }
    try:
        req = urllib.request.Request(f'{BASE}{path}', data=body, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())
    except Exception as e:
        return None, str(e)

results = []

def test(name, passed, info=''):
    status = 'PASS' if passed else 'FAIL'
    results.append((status, name, info))
    print(f'[{status}] {name}' + (f' | {info}' if info else ''))

print('=== API ENDPOINT TESTS ===')

# Test 1: GET / (root)
code, data = get('/')
test('GET / returns 200', code == 200, f'code={code}')

# Test 2: GET /health
code, data = get('/health')
test('GET /health returns 200', code == 200, f'code={code}, data={data}')

# Test 3: GET /api/v1/complaints (empty initially)
code, data = get('/api/v1/complaints')
test('GET /api/v1/complaints returns 200', code == 200, f'code={code}, total={data.get("total")}')
test('Complaints response has total field', 'total' in data, str(data))
test('Complaints response has complaints field', 'complaints' in data, str(data))

# Test 4: POST valid complaint
valid_fields = {
    'passenger_name': 'John Smith',
    'mobile_number': '+94771234567',
    'email': 'john@example.com',
    'bus_number': 'NB-1234',
    'route_number': 'Route 120',
    'category': 'Bus Delay',
    'complaint_description': 'The bus was 45 minutes late at the main stop',
    'incident_location': 'Main Street Bus Stop',
    'incident_datetime': '2026-07-04T10:00:00',
}
code, data = post_form('/api/v1/complaints/create', valid_fields)
test('POST valid complaint returns 201', code == 201, f'code={code}')
test('Response has complaint_id', 'complaint_id' in data, str(data))
test('Response has success message', data.get('message') == 'Your complaint has been registered successfully.', data.get('message'))

# Test 5: Verify complaint_id format
cid = data.get('complaint_id', '')
test('Complaint ID format CMP-YYYY-NNNN', bool(re.match(r'^CMP-\d{4}-\d{4}$', cid)), f'got: {cid}')

# Test 6: GET complaints after insert
code, data2 = get('/api/v1/complaints')
test('GET complaints returns non-zero total after insert', data2.get('total', 0) > 0, f'total={data2.get("total")}')

# Test 7: GET single complaint
if cid:
    code, data3 = get(f'/api/v1/complaints/{cid}')
    test(f'GET /complaints/{cid} returns 200', code == 200, f'code={code}')
    test('Single complaint has all fields', all(k in data3 for k in ['passenger_name','mobile_number','email','bus_number','route_number','category','complaint_description','incident_location','incident_datetime','status']), str(list(data3.keys())))

# Test 8: GET non-existent complaint → 404
code, data4 = get('/api/v1/complaints/CMP-9999-9999')
test('GET non-existent complaint returns 404', code == 404, f'code={code}')

print()
print('=== VALIDATION TESTS ===')

# Test 9: Missing passenger_name → 422
missing_fields = {k: v for k, v in valid_fields.items() if k != 'passenger_name'}
code, data = post_form('/api/v1/complaints/create', missing_fields)
test('Missing passenger_name returns 422', code in [400, 422], f'code={code}')

# Test 10: Invalid email → 422
bad_email = {**valid_fields, 'email': 'notanemail'}
code, data = post_form('/api/v1/complaints/create', bad_email)
test('Invalid email returns 422', code in [400, 422], f'code={code}')

# Test 11: Invalid mobile → 422
bad_mobile = {**valid_fields, 'mobile_number': 'abc'}
code, data = post_form('/api/v1/complaints/create', bad_mobile)
test('Invalid mobile number returns 422', code in [400, 422], f'code={code}')

# Test 12: Invalid category → 422
bad_cat = {**valid_fields, 'category': 'FakeCategory'}
code, data = post_form('/api/v1/complaints/create', bad_cat)
test('Invalid category returns 422', code in [400, 422], f'code={code}')

# Test 13: Short description < 10 chars → 422
short_desc = {**valid_fields, 'complaint_description': 'short'}
code, data = post_form('/api/v1/complaints/create', short_desc)
test('Description < 10 chars returns 422', code in [400, 422], f'code={code}')

# Test 14: Empty request → 422
code, data = post_form('/api/v1/complaints/create', {})
test('Empty request returns 422', code in [400, 422], f'code={code}')

# Test 15: Single-char name → 422
short_name = {**valid_fields, 'passenger_name': 'A'}
code, data = post_form('/api/v1/complaints/create', short_name)
test('Single-char name returns 422', code in [400, 422], f'code={code}')

# Test 16: Invalid datetime → 422
bad_dt = {**valid_fields, 'incident_datetime': 'not-a-date'}
code, data = post_form('/api/v1/complaints/create', bad_dt)
test('Invalid datetime format returns 422', code in [400, 422], f'code={code}')

# Test 17: Second valid complaint → auto-increment ID
valid_fields2 = {**valid_fields, 'passenger_name': 'Jane Doe', 'email': 'jane@example.com'}
code, data = post_form('/api/v1/complaints/create', valid_fields2)
cid2 = data.get('complaint_id', '')
test('Second complaint auto-increments ID', bool(re.match(r'^CMP-\d{4}-\d{4}$', cid2)) and cid2 != cid, f'got: {cid2}')

# Summary
print()
print('=== SUMMARY ===')
passed = sum(1 for r in results if r[0] == 'PASS')
failed = sum(1 for r in results if r[0] == 'FAIL')
print(f'Total Tests: {len(results)} | PASSED: {passed} | FAILED: {failed}')
