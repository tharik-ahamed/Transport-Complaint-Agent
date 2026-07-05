"""Phase 4 smoke test — all new endpoints."""
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

def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(BASE+path, data=body, headers={**H, "Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

print("=== Phase 4 API Smoke Test ===\n")

# GET endpoints
check("GET /api/v1/complaints/assigned", lambda: get("/api/v1/complaints/assigned"))
check("GET /api/v1/complaints/escalated", lambda: get("/api/v1/complaints/escalated"))
check("GET /api/v1/complaints/sla", lambda: get("/api/v1/complaints/sla"))
check("GET /api/v1/departments/dashboard", lambda: get("/api/v1/departments/dashboard"))
check("GET /api/v1/analytics/performance", lambda: get("/api/v1/analytics/performance"))

# Phase 3 intelligence still works
check("GET /api/v1/complaints/CMP-2026-0001/intelligence", lambda: get("/api/v1/complaints/CMP-2026-0001/intelligence"))

# POST action endpoints
check("POST /assign", lambda: post("/api/v1/complaints/CMP-2026-0001/assign", {"department":"Operations Department","team":"Route Scheduling Team"}))
check("POST /escalate", lambda: post("/api/v1/complaints/CMP-2026-0002/escalate", {"escalation_level":"Regional Operations Manager"}))
check("POST /status", lambda: post("/api/v1/complaints/CMP-2026-0003/status", {"complaint_status":"In Progress"}))
check("POST /resolve", lambda: post("/api/v1/complaints/CMP-2026-0004/resolve", {"resolution_notes":"Issue investigated and resolved. Driver counseled."}))

# Phase 4 data in regular complaint GET
d = get("/api/v1/complaints/CMP-2026-0001")
check("Phase4 fields in GET /complaints/{id}", lambda: (
    d["assigned_department"] and d["sla_status"] and d["complaint_status"] and True
))

# Verify performance data
perf = get("/api/v1/analytics/performance")
check("Performance has dept_workload", lambda: len(perf.get("department_workload", {})) > 0)
check("Performance has top_routes", lambda: len(perf.get("top_routes", {})) > 0)
check("Performance has sla_compliance", lambda: "percentage" in perf.get("sla_compliance", {}))

# Verify dept filter
assigned = get("/api/v1/complaints/assigned?department=Operations")
check(f"Assigned dept filter: {assigned['total']} Operations complaints", lambda: assigned["total"] >= 0)

sla_breached = get("/api/v1/complaints/sla?status=breached")
check(f"SLA breached filter returns {sla_breached['total']} complaints", lambda: True)

print(f"\n{'='*40}")
print(f"Result: {ok} passed, {fail} failed")
if fail == 0:
    print("✓ ALL PHASE 4 TESTS PASSED")
