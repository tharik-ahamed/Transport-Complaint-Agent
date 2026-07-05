import urllib.request
import urllib.error
import json
import re
import time

BASE = 'http://127.0.0.1:8000'
results = []

def chk(name, passed, detail='', warn=False):
    st = 'WARN' if warn else ('PASS' if passed else 'FAIL')
    results.append((st, name, detail))
    print('[' + st + '] ' + name + (' | ' + str(detail) if detail else ''))

def get(path):
    try:
        req = urllib.request.Request(BASE + path)
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except:
            return e.code, {}
    except Exception as e:
        return None, str(e)

def post_json(path, payload):
    body = json.dumps(payload).encode()
    headers = {'Content-Type': 'application/json', 'Content-Length': str(len(body))}
    try:
        req = urllib.request.Request(BASE + path, data=body, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except:
            return e.code, {}
    except Exception as e:
        return None, str(e)

def post_form(path, fields):
    boundary = 'AuditBoundary123'
    body = b''
    for k, v in fields.items():
        body += ('--' + boundary + '\r\nContent-Disposition: form-data; name="' + k + '"\r\n\r\n' + str(v) + '\r\n').encode()
    body += ('--' + boundary + '--\r\n').encode()
    headers = {
        'Content-Type': 'multipart/form-data; boundary=' + boundary,
        'Content-Length': str(len(body))
    }
    try:
        req = urllib.request.Request(BASE + path, data=body, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except:
            return e.code, {}
    except Exception as e:
        return None, str(e)

print('=== LIVE API TESTS ===')

# Root endpoint
code, data = get('/')
chk('GET / returns 200', code == 200, 'code=' + str(code))
chk('Root has version field', 'version' in data, str(data.get('version')))
chk('Root has ai_enabled field', 'ai_enabled' in data, 'ai_enabled=' + str(data.get('ai_enabled')))

# Health check
code, data = get('/health')
chk('GET /health returns 200', code == 200)
chk('Health status is healthy', data.get('status') == 'healthy', str(data))

# Swagger docs
code, data = get('/docs')
chk('GET /docs returns 200 (Swagger UI)', code == 200, 'code=' + str(code))

# GET all complaints (empty or populated)
code, data = get('/api/v1/complaints')
chk('GET /api/v1/complaints returns 200', code == 200, 'code=' + str(code))
chk('Response has total field', 'total' in data, str(data.get('total')))
chk('Response has complaints list', 'complaints' in data, str(type(data.get('complaints'))))
initial_count = data.get('total', 0)

# Valid complaint submission
valid_fields = {
    'passenger_name': 'Audit TestUser',
    'mobile_number': '+94771234567',
    'email': 'audit@test.com',
    'bus_number': 'NB-AUDIT-01',
    'route_number': 'Route-AUDIT',
    'category': 'Bus Delay',
    'complaint_description': 'This is an audit test complaint. Bus was 45 minutes late at Karur Bus Stand.',
    'incident_location': 'Karur Bus Stand',
    'incident_datetime': '2026-07-04T08:00:00',
}
t0 = time.time()
code, data = post_form('/api/v1/complaints/create', valid_fields)
elapsed = time.time() - t0
chk('POST create valid complaint returns 201', code == 201, 'code=' + str(code))
chk('Response has complaint_id', 'complaint_id' in data, str(data))
chk('Response has success message', data.get('message') == 'Your complaint has been registered successfully.', data.get('message'))
chk('Response has ai_analysis field (Phase 2)', 'ai_analysis' in data, str(data.get('ai_analysis')))
chk('Submission response time < 10s', elapsed < 10, str(round(elapsed, 2)) + 's')
submitted_id = data.get('complaint_id', '')

# Complaint ID format
if submitted_id:
    chk('Complaint ID format CMP-YYYY-NNNN', bool(re.match(r'^CMP-\d{4}-\d{4}$', submitted_id)), 'got: ' + submitted_id)
    chk('Complaint ID year is 2026', '2026' in submitted_id, submitted_id)

# GET complaints now has 1+ records
code, data2 = get('/api/v1/complaints')
new_count = data2.get('total', 0)
chk('Complaint count increased after insert', new_count > initial_count, str(initial_count) + '->' + str(new_count))

# Verify Phase 2 AI fields populated on returned complaint
if data2.get('complaints'):
    first = data2['complaints'][0]
    chk('ai_summary in complaint response', 'ai_summary' in first, str(first.get('ai_summary', 'None')))
    chk('detected_language in response', 'detected_language' in first, str(first.get('detected_language')))
    chk('extracted_keywords in response', 'extracted_keywords' in first)

# GET single complaint
if submitted_id:
    code, data3 = get('/api/v1/complaints/' + submitted_id)
    chk('GET single complaint returns 200', code == 200, 'code=' + str(code))
    chk('Single complaint has all P1 fields', all(k in data3 for k in ['passenger_name','email','bus_number','category','status']), str(list(data3.keys())[:8]))
    chk('Single complaint has AI fields', all(k in data3 for k in ['detected_language','ai_summary','extracted_keywords']), str(data3.get('detected_language')))

# GET non-existent complaint
code, _ = get('/api/v1/complaints/CMP-9999-9999')
chk('GET non-existent complaint returns 404', code == 404, 'code=' + str(code))

# Validation tests
print()
print('--- Validation Tests ---')
bad_name = dict(valid_fields, passenger_name='A')
code, d = post_form('/api/v1/complaints/create', bad_name)
chk('Short name (1 char) rejected 422', code == 422, 'code=' + str(code))

bad_email = dict(valid_fields, email='notanemail')
code, d = post_form('/api/v1/complaints/create', bad_email)
chk('Invalid email rejected 422', code == 422, 'code=' + str(code))

bad_mobile = dict(valid_fields, mobile_number='abc')
code, d = post_form('/api/v1/complaints/create', bad_mobile)
chk('Invalid mobile rejected 422', code == 422, 'code=' + str(code))

bad_cat = dict(valid_fields, category='FakeCategory')
code, d = post_form('/api/v1/complaints/create', bad_cat)
chk('Invalid category rejected 422', code == 422, 'code=' + str(code))

short_desc = dict(valid_fields, complaint_description='short')
code, d = post_form('/api/v1/complaints/create', short_desc)
chk('Short description (<10 chars) rejected 422', code == 422, 'code=' + str(code))

empty_req = {}
code, d = post_form('/api/v1/complaints/create', empty_req)
chk('Empty request rejected 422', code == 422, 'code=' + str(code))

bad_date = dict(valid_fields, incident_datetime='not-a-date')
code, d = post_form('/api/v1/complaints/create', bad_date)
chk('Invalid datetime rejected 422', code == 422, 'code=' + str(code))

# Phase 2 AI endpoints
print()
print('--- Phase 2 AI Endpoint Tests ---')
if submitted_id:
    # POST analyze-complaint
    t0 = time.time()
    code, data4 = post_json('/api/v1/ai/analyze-complaint', {'complaint_id': submitted_id})
    elapsed2 = time.time() - t0
    chk('POST /api/v1/ai/analyze-complaint returns 200', code == 200, 'code=' + str(code))
    chk('Analysis has detected_language', 'detected_language' in data4, str(data4.get('detected_language')))
    chk('Analysis has extracted_entities', 'extracted_entities' in data4)
    chk('Analysis has extracted_keywords', 'extracted_keywords' in data4)
    chk('Analysis has ai_summary', 'ai_summary' in data4, str(data4.get('ai_summary')))
    chk('Analysis has ai_mode field', 'ai_mode' in data4, data4.get('ai_mode'))
    chk('AI analysis response time < 15s', elapsed2 < 15, str(round(elapsed2, 2)) + 's')

    # GET analysis endpoint
    code, data5 = get('/api/v1/complaints/' + submitted_id + '/analysis')
    chk('GET /complaints/{id}/analysis returns 200', code == 200, 'code=' + str(code))
    chk('Analysis retrieval has complaint_id', data5.get('complaint_id') == submitted_id)

# POST analyze-complaint with invalid ID
code, d = post_json('/api/v1/ai/analyze-complaint', {'complaint_id': 'CMP-FAKE-0000'})
chk('POST analyze with invalid ID returns 404', code == 404, 'code=' + str(code))

# GET analysis with invalid ID
code, d = get('/api/v1/complaints/CMP-FAKE-0000/analysis')
chk('GET analysis invalid ID returns 404', code == 404, 'code=' + str(code))

# ID uniqueness
print()
print('--- Uniqueness Test ---')
code, data6 = post_form('/api/v1/complaints/create', dict(valid_fields, passenger_name='Second Audit User', email='audit2@test.com'))
second_id = data6.get('complaint_id', '')
chk('Second complaint gets different ID', second_id != submitted_id and bool(second_id), submitted_id + ' vs ' + second_id)
if submitted_id and second_id:
    n1 = int(submitted_id.split('-')[2])
    n2 = int(second_id.split('-')[2])
    chk('ID sequence increments', n2 == n1 + 1, str(n1) + '->' + str(n2))

print()
print('=== API SUMMARY ===')
passed = sum(1 for r in results if r[0] == 'PASS')
failed = sum(1 for r in results if r[0] == 'FAIL')
warned = sum(1 for r in results if r[0] == 'WARN')
print('Total: ' + str(len(results)) + ' | PASS: ' + str(passed) + ' | FAIL: ' + str(failed) + ' | WARN: ' + str(warned))
if failed:
    print()
    print('FAILURES:')
    for st, name, detail in results:
        if st == 'FAIL':
            print('  FAIL: ' + name + ' - ' + str(detail))
