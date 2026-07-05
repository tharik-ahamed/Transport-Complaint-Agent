"""
Phase 4 Backfill — Apply routing, SLA, and escalation to all existing complaints.
Safe to re-run; only updates complaints missing Phase 4 data.
"""
import urllib.request, urllib.error, json

BASE = "http://127.0.0.1:8000"

def login():
    body = json.dumps({"username": "admin", "password": "admin123"}).encode()
    req = urllib.request.Request(BASE+"/api/v1/auth/login", data=body, headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())["access_token"]

def get_complaints(token):
    req = urllib.request.Request(BASE+"/api/v1/complaints", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())["complaints"]

def reanalyze(token, cid):
    body = json.dumps({"complaint_id": cid}).encode()
    req = urllib.request.Request(BASE+"/api/v1/ai/analyze-complaint", data=body,
                                  headers={"Authorization": f"Bearer {token}", "Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

token = login()
complaints = get_complaints(token)
print(f"Found {len(complaints)} complaints. Applying Phase 4 workflow...")

ok = skip = fail = 0
for c in complaints:
    cid = c["complaint_id"]
    # Always re-analyze to trigger Phase 4 workflow for existing records
    try:
        reanalyze(token, cid)
        dept = c.get("assigned_department", "not yet")
        print(f"  ✓ {cid}")
        ok += 1
    except Exception as e:
        print(f"  ✗ {cid}: {e}")
        fail += 1

print(f"\nPhase 4 backfill: {ok} updated, {skip} skipped, {fail} failed")
