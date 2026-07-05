"""
Phase 3 Backfill — Re-analyze all existing complaints to add Phase 3 fields.
Run once after deploying Phase 3.
"""
import urllib.request, urllib.error, json, sys

BASE = "http://127.0.0.1:8000"

# 1. Login to get a token
def login():
    body = json.dumps({"username": "admin", "password": "admin123"}).encode()
    req = urllib.request.Request(BASE + "/api/v1/auth/login", data=body,
                                  headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())["access_token"]

# 2. Get all complaints
def get_complaints(token):
    req = urllib.request.Request(BASE + "/api/v1/complaints",
                                  headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())["complaints"]

# 3. Re-analyze one complaint
def reanalyze(token, complaint_id):
    body = json.dumps({"complaint_id": complaint_id}).encode()
    req = urllib.request.Request(BASE + "/api/v1/ai/analyze-complaint", data=body,
                                  headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

token = login()
complaints = get_complaints(token)
print(f"Found {len(complaints)} complaints to backfill...")

ok = fail = 0
for c in complaints:
    cid = c["complaint_id"]
    # Only backfill if Phase 3 fields are empty
    if not c.get("sentiment"):
        try:
            reanalyze(token, cid)
            print(f"  ✓ {cid}")
            ok += 1
        except Exception as e:
            print(f"  ✗ {cid}: {e}")
            fail += 1
    else:
        print(f"  - {cid} (already has Phase 3 data, skipping)")

print(f"\nBackfill complete: {ok} updated, {fail} failed")
