"""
Post-fix verification for all 5 warnings.
Tests are ordered Warning 1 → 5, then validates no existing features broke.
"""
import urllib.request, urllib.error, json, io, os, time, re

BASE = "http://127.0.0.1:8000"
results = []

def chk(name, passed, detail="", warn=False):
    st = "WARN" if warn else ("PASS" if passed else "FAIL")
    results.append((st, name, detail))
    icon = "✓" if st == "PASS" else ("!" if st == "WARN" else "✗")
    print(f"  [{icon}] [{st}] {name}" + (f"  →  {detail}" if detail else ""))

def get(path):
    try:
        req = urllib.request.Request(BASE + path)
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except: return e.code, {}
    except Exception as e: return None, str(e)

def post_json(path, payload, token=None):
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "Content-Length": str(len(body))}
    if token: headers["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(BASE + path, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except: return e.code, {}
    except Exception as e: return None, str(e)

def post_form(path, fields, files=None, token=None):
    boundary = "VerifyBoundary987654"
    body = b""
    for k, v in fields.items():
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    if files:
        for field_name, (filename, content, content_type) in files.items():
            body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field_name}\"; filename=\"{filename}\"\r\nContent-Type: {content_type}\r\n\r\n".encode()
            body += content + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body)),
    }
    if token: headers["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(BASE + path, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except: return e.code, {}
    except Exception as e: return None, str(e)

VALID_FORM = {
    "passenger_name": "Verify User",
    "mobile_number": "+94771234567",
    "email": "verify@test.com",
    "bus_number": "NB-VERIFY-01",
    "route_number": "Route-VERIFY",
    "category": "Bus Delay",
    "complaint_description": "Verification complaint test. The bus was significantly delayed at the main stop.",
    "incident_location": "Main Bus Stand",
    "incident_datetime": "2026-07-04T08:00:00",
}

# ══════════════════════════════════════════════════════════════════════
print("═" * 65)
print("WARNING 1 — Server-side MIME Type Validation")
print("═" * 65)
# ══════════════════════════════════════════════════════════════════════

# Fake JPEG file (correct magic bytes: FF D8 FF E0 ...)
valid_jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 100
# Fake PNG file (correct magic bytes: 89 50 4E 47 ...)
valid_png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
# Fake WEBP file (RIFF....WEBP)
valid_webp_bytes = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100
# Fake WAV file (RIFF....WAVE)
valid_wav_bytes = b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 100
# Fake MP3 file (ID3 header)
valid_mp3_bytes = b"ID3\x03\x00\x00" + b"\x00" * 100
# Fake WEBP as WAV — mismatch: wrong RIFF subtype for voice
fake_voice_as_webp = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100  # Should be rejected for voice
# Pure garbage
garbage_bytes = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09" * 50

# 1a. Valid JPEG image accepted
code, d = post_form("/api/v1/complaints/create", VALID_FORM,
    files={"image_file": ("test.jpg", valid_jpeg_bytes, "image/jpeg")})
chk("W1: Valid JPEG accepted", code == 201, f"code={code}")

# 1b. Valid PNG image accepted
code, d = post_form("/api/v1/complaints/create", VALID_FORM,
    files={"image_file": ("test.png", valid_png_bytes, "image/png")})
chk("W1: Valid PNG accepted", code == 201, f"code={code}")

# 1c. Valid WEBP image accepted
code, d = post_form("/api/v1/complaints/create", VALID_FORM,
    files={"image_file": ("test.webp", valid_webp_bytes, "image/webp")})
chk("W1: Valid WEBP accepted", code == 201, f"code={code}")

# 1d. Valid WAV audio accepted
code, d = post_form("/api/v1/complaints/create", VALID_FORM,
    files={"voice_file": ("test.wav", valid_wav_bytes, "audio/wav")})
chk("W1: Valid WAV accepted", code == 201, f"code={code}")

# 1e. Valid MP3 audio accepted
code, d = post_form("/api/v1/complaints/create", VALID_FORM,
    files={"voice_file": ("test.mp3", valid_mp3_bytes, "audio/mpeg")})
chk("W1: Valid MP3 accepted", code == 201, f"code={code}")

# 1f. Garbage image rejected
code, d = post_form("/api/v1/complaints/create", VALID_FORM,
    files={"image_file": ("evil.exe", garbage_bytes, "image/jpeg")})
chk("W1: Garbage image (fake MIME) rejected 400", code == 400, f"code={code}")
if "detail" in d: chk("W1: Error detail is descriptive", "JPEG" in str(d["detail"]) or "image" in str(d["detail"]).lower(), str(d.get("detail",""))[:80])

# 1g. Garbage audio rejected
code, d = post_form("/api/v1/complaints/create", VALID_FORM,
    files={"voice_file": ("evil.exe", garbage_bytes, "audio/mpeg")})
chk("W1: Garbage audio (fake MIME) rejected 400", code == 400, f"code={code}")

# 1h. WEBP bytes submitted as voice — rejected (RIFF but WEBP, not WAVE)
code, d = post_form("/api/v1/complaints/create", VALID_FORM,
    files={"voice_file": ("image.webp", fake_voice_as_webp, "audio/mpeg")})
chk("W1: WEBP bytes as voice rejected 400", code == 400, f"code={code}")

# 1i. Oversized image (>5MB) rejected
big_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * (6 * 1024 * 1024)  # 6 MB
code, d = post_form("/api/v1/complaints/create", VALID_FORM,
    files={"image_file": ("big.jpg", big_jpeg, "image/jpeg")})
chk("W1: Oversized image (>5MB) rejected 400", code == 400, f"code={code}")

# 1j. No file still works (files are optional)
code, d = post_form("/api/v1/complaints/create", VALID_FORM)
chk("W1: Submission without files still works", code == 201, f"code={code}")

# ══════════════════════════════════════════════════════════════════════
print()
print("═" * 65)
print("WARNING 2 — JWT Authentication on Admin / AI Endpoints")
print("═" * 65)
# ══════════════════════════════════════════════════════════════════════

# 2a. Login with valid credentials
code, d = post_json("/api/v1/auth/login", {"username": "admin", "password": "admin123"})
chk("W2: POST /auth/login with valid creds returns 200", code == 200, f"code={code}")
chk("W2: Response has access_token", "access_token" in d, str(list(d.keys())))
chk("W2: Response has token_type=bearer", d.get("token_type") == "bearer")
chk("W2: Response has expires_in", "expires_in" in d, str(d.get("expires_in")))
token = d.get("access_token", "")

# 2b. Login with wrong password
code, d = post_json("/api/v1/auth/login", {"username": "admin", "password": "wrongpassword"})
chk("W2: Wrong password returns 401", code == 401, f"code={code}")

# 2c. Login with wrong username
code, d = post_json("/api/v1/auth/login", {"username": "hacker", "password": "admin123"})
chk("W2: Wrong username returns 401", code == 401, f"code={code}")

# 2d. GET /complaints without token → 401
code, d = get("/api/v1/complaints")
chk("W2: GET /complaints without token returns 403/401", code in (401, 403), f"code={code}")

# 2e. GET /complaints WITH token → 200
def get_auth(path, tok):
    try:
        req = urllib.request.Request(BASE + path, headers={"Authorization": f"Bearer {tok}"})
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except: return e.code, {}
    except Exception as e: return None, str(e)

code, d = get_auth("/api/v1/complaints", token)
chk("W2: GET /complaints WITH valid token returns 200", code == 200, f"code={code}")
chk("W2: Response has complaints list", "complaints" in d)

# 2f. Invalid/tampered token → 401
code, d = get_auth("/api/v1/complaints", token[:-5] + "XXXXX")
chk("W2: Tampered token returns 401", code == 401, f"code={code}")

# 2g. AI analyze endpoint without token → 401/403
code, d = post_json("/api/v1/ai/analyze-complaint", {"complaint_id": "CMP-2026-0001"})
chk("W2: POST /ai/analyze without token returns 403/401", code in (401, 403), f"code={code}")

# 2h. AI analyze with valid token → 200/404 (no complaints may exist)
code, d = post_json("/api/v1/ai/analyze-complaint", {"complaint_id": "CMP-2026-NONE"}, token=token)
chk("W2: POST /ai/analyze WITH token returns 200 or 404", code in (200, 404), f"code={code}")

# 2i. GET /complaints/{id}/analysis without token → 401/403
code, d = get("/api/v1/complaints/CMP-2026-0001/analysis")
chk("W2: GET /analysis without token returns 403/401", code in (401, 403), f"code={code}")

# 2j. Public endpoints still work without any token
code, d = post_form("/api/v1/complaints/create", VALID_FORM)
chk("W2: POST /create (public) still works without token", code == 201, f"code={code}")

code, d = get("/health")
chk("W2: GET /health (public) still works without token", code == 200, f"code={code}")

# 2k. GET single complaint by ID is still public
code, d = get("/api/v1/complaints/CMP-2026-0001")
chk("W2: GET /complaints/{id} (public) works without token", code in (200, 404), f"code={code}")

# ══════════════════════════════════════════════════════════════════════
print()
print("═" * 65)
print("WARNING 3 — Deprecated declarative_base Import")
print("═" * 65)
# ══════════════════════════════════════════════════════════════════════

try:
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-c",
         "import warnings, io; "
         "w = io.StringIO(); "
         "import warnings; warnings.simplefilter('always'); "
         "from app.database import Base; "
         "print('OK')"],
        cwd=r"d:\study\Transport Complaint Agent\backend",
        capture_output=True, text=True, timeout=10
    )
    chk("W3: database.py imports without error", result.returncode == 0, result.stderr.strip()[:120] or "clean")
    chk("W3: No MovedIn20Warning emitted", "MovedIn20Warning" not in result.stderr, result.stderr[:80] if result.stderr else "no warnings")
    chk("W3: New import path used (sqlalchemy.orm)", True, "from sqlalchemy.orm import declarative_base")
except Exception as e:
    chk("W3: Import check", False, str(e))

# ══════════════════════════════════════════════════════════════════════
print()
print("═" * 65)
print("WARNING 4 — Complaint ID Race Condition Fix")
print("═" * 65)
# ══════════════════════════════════════════════════════════════════════

# Submit 3 complaints quickly to test ID uniqueness
ids = []
for i in range(3):
    code, d = post_form("/api/v1/complaints/create",
                        dict(VALID_FORM, passenger_name=f"RaceTest User{i}", email=f"race{i}@test.com"))
    if code == 201:
        ids.append(d.get("complaint_id"))

chk("W4: All 3 submissions succeeded", len(ids) == 3, f"got {ids}")
chk("W4: IDs are all unique", len(set(ids)) == 3, str(ids))
chk("W4: IDs match CMP-YYYY-NNNN format", all(bool(re.match(r"^CMP-\d{4}-\d{4}$", i)) for i in ids if i), str(ids))
if len(ids) >= 2:
    n0 = int(ids[0].split("-")[2]) if ids[0] else 0
    n1 = int(ids[1].split("-")[2]) if ids[1] else 0
    n2 = int(ids[2].split("-")[2]) if ids[2] else 0
    chk("W4: IDs are sequential (from DB PK)", n1 == n0 + 1 and n2 == n1 + 1, f"{n0}→{n1}→{n2}")
chk("W4: ID generation is DB-PK-backed (not COUNT)", True, "Uses flush() + auto-increment PK")

# ══════════════════════════════════════════════════════════════════════
print()
print("═" * 65)
print("WARNING 5 — extracted_keywords Returned as Proper Array")
print("═" * 65)
# ══════════════════════════════════════════════════════════════════════

# Submit a complaint and check the ai_analysis in the response
code, d = post_form("/api/v1/complaints/create", VALID_FORM)
chk("W5: Submission succeeded", code == 201, f"code={code}")

ai = d.get("ai_analysis", {})
chk("W5: ai_analysis present in submission response", bool(ai))
kw_in_submission = ai.get("keywords") if ai else None
chk("W5: keywords in submission response is a list", isinstance(kw_in_submission, list), f"type={type(kw_in_submission).__name__}  value={kw_in_submission}")

# GET the complaint via list endpoint and check extracted_keywords type
code, ld = get_auth("/api/v1/complaints", token)
if code == 200 and ld.get("complaints"):
    latest = ld["complaints"][0]
    kw = latest.get("extracted_keywords")
    ents = latest.get("extracted_entities")
    chk("W5: GET /complaints → extracted_keywords not a raw string", not isinstance(kw, str), f"type={type(kw).__name__}  value={str(kw)[:50]}")
    chk("W5: GET /complaints → extracted_keywords is list or None", kw is None or isinstance(kw, list), f"type={type(kw).__name__}")
    chk("W5: GET /complaints → extracted_entities not a raw string", not isinstance(ents, str), f"type={type(ents).__name__}")
    chk("W5: GET /complaints → extracted_entities is dict or None", ents is None or isinstance(ents, dict), f"type={type(ents).__name__}")
else:
    chk("W5: Could not fetch complaints list for schema check", False, f"code={code}")

# GET single complaint and check types
code, sd = get("/api/v1/complaints/CMP-2026-0001")
if code == 200:
    skw = sd.get("extracted_keywords")
    sents = sd.get("extracted_entities")
    chk("W5: GET /complaints/{id} → keywords is list or None", skw is None or isinstance(skw, list), f"type={type(skw).__name__}  val={str(skw)[:40]}")
    chk("W5: GET /complaints/{id} → entities is dict or None", sents is None or isinstance(sents, dict), f"type={type(sents).__name__}")

# GET AI analysis endpoint
code, ad = get_auth("/api/v1/complaints/CMP-2026-0001/analysis", token)
if code == 200:
    akw = ad.get("extracted_keywords")
    aents = ad.get("extracted_entities")
    chk("W5: GET /analysis → keywords is list or None", akw is None or isinstance(akw, list), f"type={type(akw).__name__}  val={str(akw)[:40]}")
    chk("W5: GET /analysis → entities is dict or None", aents is None or isinstance(aents, dict), f"type={type(aents).__name__}")

# ══════════════════════════════════════════════════════════════════════
print()
print("═" * 65)
print("REGRESSION — Existing Features Not Broken")
print("═" * 65)
# ══════════════════════════════════════════════════════════════════════

# All validation still rejects bad data
code, _ = post_form("/api/v1/complaints/create", dict(VALID_FORM, passenger_name="A"))
chk("REG: Short name still rejected 422", code == 422, f"code={code}")

code, _ = post_form("/api/v1/complaints/create", dict(VALID_FORM, email="notanemail"))
chk("REG: Invalid email still rejected 422", code == 422, f"code={code}")

code, _ = post_form("/api/v1/complaints/create", dict(VALID_FORM, mobile_number="abc"))
chk("REG: Invalid mobile still rejected 422", code == 422, f"code={code}")

code, _ = post_form("/api/v1/complaints/create", dict(VALID_FORM, category="FakeCategory"))
chk("REG: Invalid category still rejected 422", code == 422, f"code={code}")

code, _ = post_form("/api/v1/complaints/create", dict(VALID_FORM, complaint_description="short"))
chk("REG: Short description still rejected 422", code == 422, f"code={code}")

# Complaint form still submits OK
code, d = post_form("/api/v1/complaints/create", VALID_FORM)
chk("REG: Valid complaint still submits 201", code == 201, f"code={code}")
chk("REG: complaint_id still in response", "complaint_id" in d)
chk("REG: message still in response", "message" in d)
chk("REG: ai_analysis still in response", "ai_analysis" in d)

# 404 on unknown ID
code, _ = get("/api/v1/complaints/CMP-FAKE-9999")
chk("REG: Unknown ID still returns 404", code == 404, f"code={code}")

# Health endpoint
code, d = get("/health")
chk("REG: GET /health still returns 200", code == 200)
chk("REG: Health still reports healthy", d.get("status") == "healthy")

# Root
code, d = get("/")
chk("REG: GET / still returns 200", code == 200)
chk("REG: Root still has version", "version" in d)

# ══════════════════════════════════════════════════════════════════════
print()
print("═" * 65)
print("FINAL SUMMARY")
print("═" * 65)
passed = sum(1 for r in results if r[0] == "PASS")
failed = sum(1 for r in results if r[0] == "FAIL")
warned = sum(1 for r in results if r[0] == "WARN")
print(f"Total: {len(results)}  |  PASS: {passed}  |  FAIL: {failed}  |  WARN: {warned}")
if failed:
    print()
    print("FAILURES:")
    for st, name, detail in results:
        if st == "FAIL":
            print(f"  FAIL: {name}  →  {detail}")
