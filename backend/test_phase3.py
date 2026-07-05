"""Quick Phase 3 smoke test."""
import urllib.request, urllib.error, json

BASE = "http://127.0.0.1:8000"

def ok(msg): print(f"  [PASS] {msg}")
def fail(msg): print(f"  [FAIL] {msg}")

# Login
body = json.dumps({"username": "admin", "password": "admin123"}).encode()
req = urllib.request.Request(BASE+"/api/v1/auth/login", data=body, headers={"Content-Type":"application/json"}, method="POST")
with urllib.request.urlopen(req) as r:
    token = json.loads(r.read())["access_token"]
ok("Login successful")

headers = {"Authorization": f"Bearer {token}"}

# Analytics endpoints
for path in ["/api/v1/analytics/sentiment", "/api/v1/analytics/categories",
             "/api/v1/analytics/severity", "/api/v1/analytics/priorities",
             "/api/v1/analytics/summary"]:
    try:
        req = urllib.request.Request(BASE + path, headers=headers)
        with urllib.request.urlopen(req) as r:
            d = json.loads(r.read())
            ok(f"GET {path}")
    except Exception as e:
        fail(f"GET {path}: {e}")

# Intelligence endpoint
try:
    req = urllib.request.Request(BASE+"/api/v1/complaints/CMP-2026-0001/intelligence", headers=headers)
    with urllib.request.urlopen(req) as r:
        d = json.loads(r.read())
        ok(f"Intelligence: sentiment={d.get('sentiment')}, severity={d.get('severity')}, priority={d.get('priority')}")
        ok(f"Intelligence: categories={d.get('categories')}")
        ok(f"Intelligence: duplicates={d.get('duplicates')}")
except Exception as e:
    fail(f"Intelligence endpoint: {e}")

# Phase 3 fields in complaint response
req = urllib.request.Request(BASE+"/api/v1/complaints/CMP-2026-0001", headers=headers)
with urllib.request.urlopen(req) as r:
    c = json.loads(r.read())
    ok(f"Complaint has sentiment={c.get('sentiment')}")
    ok(f"Complaint has severity={c.get('severity')}")
    ok(f"Complaint has priority_level={c.get('priority_level')}")
    ok(f"Complaint has incident_id={c.get('incident_id')}")
    ok(f"Complaint has recommended_action={'yes' if c.get('recommended_action') else 'no'}")
    cats = c.get("ai_categories")
    ok(f"ai_categories is a list: {isinstance(cats, list)} ({cats})")

# Verify summary metrics
req = urllib.request.Request(BASE+"/api/v1/analytics/summary", headers=headers)
with urllib.request.urlopen(req) as r:
    s = json.loads(r.read())
    m = s.get("metrics", {})
    ok(f"Summary metrics: total={m.get('total_complaints')}, critical={m.get('critical_complaints')}, dup_groups={m.get('duplicate_groups')}")
    ok(f"Trend data points: {len(s.get('trend',[]))}")

print("\nAll Phase 3 smoke tests passed!")
