"""Phase 6 smoke test."""
import urllib.request, urllib.error, json

BASE = "http://127.0.0.1:8000"
ok = fail = 0

def check(label, fn):
    global ok, fail
    try:
        fn()
        print(f"  [PASS] {label}")
        ok += 1
    except Exception as e:
        print(f"  [FAIL] {label}: {e}")
        fail += 1

# Login
body = json.dumps({"username":"admin","password":"admin123"}).encode()
req = urllib.request.Request(BASE+"/api/v1/auth/login", data=body, headers={"Content-Type":"application/json"}, method="POST")
with urllib.request.urlopen(req) as r:
    token = json.loads(r.read())["access_token"]
H = {"Authorization": f"Bearer {token}"}

def get(path):
    req = urllib.request.Request(BASE+path, headers=H)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def get_binary(path):
    req = urllib.request.Request(BASE+path, headers=H)
    with urllib.request.urlopen(req) as r:
        return r.read()

def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(BASE+path, data=body, headers={**H, "Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

print("=== Phase 6 API Smoke Test ===\n")

# Executive routes
check("GET /api/v1/health-index", lambda: get("/api/v1/health-index"))
check("GET /api/v1/governance/recommendations", lambda: get("/api/v1/governance/recommendations"))
check("GET /api/v1/heatmap", lambda: get("/api/v1/heatmap"))
check("GET /api/v1/explanations/CMP-2026-0001", lambda: get("/api/v1/explanations/CMP-2026-0001"))

# Copilot natural language
check("POST /api/v1/copilot/query", lambda: post("/api/v1/copilot/query", {"question": "Which routes received the highest complaints?"}))

# Report builders
check("GET /api/v1/reports/daily (PDF)", lambda: len(get_binary("/api/v1/reports/daily?format=pdf")) > 100)
check("GET /api/v1/reports/daily (DOCX)", lambda: len(get_binary("/api/v1/reports/daily?format=docx")) > 100)
check("GET /api/v1/reports/weekly (PDF)", lambda: len(get_binary("/api/v1/reports/weekly?format=pdf")) > 100)
check("GET /api/v1/reports/monthly (PDF)", lambda: len(get_binary("/api/v1/reports/monthly?format=pdf")) > 100)

print(f"\n{'='*40}")
print(f"Result: {ok} passed, {fail} failed")
if fail == 0:
    print("✓ ALL PHASE 6 ENDPOINTS VERIFIED AND RUNNING")
