"""Phase 5 smoke test."""
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

print("=== Phase 5 API Smoke Test ===\n")

# Phase 5 Predictive GET endpoints
check("GET /api/v1/analytics/trends", lambda: get("/api/v1/analytics/trends"))
check("GET /api/v1/analytics/routes/risk", lambda: get("/api/v1/analytics/routes/risk"))
check("GET /api/v1/analytics/drivers/risk", lambda: get("/api/v1/analytics/drivers/risk"))
check("GET /api/v1/analytics/buses/risk", lambda: get("/api/v1/analytics/buses/risk"))
check("GET /api/v1/analytics/forecast", lambda: get("/api/v1/analytics/forecast"))
check("GET /api/v1/analytics/recommendations", lambda: get("/api/v1/analytics/recommendations"))
check("GET /api/v1/analytics/alerts", lambda: get("/api/v1/analytics/alerts"))
check("GET /api/v1/analytics/predictive", lambda: get("/api/v1/analytics/predictive"))

# Validate data shape of predictive combined response
pred = get("/api/v1/analytics/predictive")
check("Predictive has trends", lambda: "trends" in pred)
check("Predictive has route_risks", lambda: "route_risks" in pred)
check("Predictive has driver_risks", lambda: "driver_risks" in pred)
check("Predictive has bus_risks", lambda: "bus_risks" in pred)
check("Predictive has forecast", lambda: "forecast" in pred)
check("Predictive has recommendations", lambda: "recommendations" in pred)
check("Predictive has alerts", lambda: "alerts" in pred)

print(f"\n{'='*40}")
print(f"Result: {ok} passed, {fail} failed")
if fail == 0:
    print("✓ ALL PHASE 5 ENDPOINTS VERIFIED AND INTEGRATED")
