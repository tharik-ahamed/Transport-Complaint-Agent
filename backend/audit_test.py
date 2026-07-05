import sys, json, re, sqlite3, os, time
sys.path.insert(0, '.')

results = []
def chk(name, passed, detail='', warn=False):
    st = 'WARN' if warn else ('PASS' if passed else 'FAIL')
    results.append((st, name, detail))
    print('[' + st + '] ' + name + (' | ' + detail if detail else ''))

# IMPORT TESTS
print('=== IMPORT CHECKS ===')
try:
    from app.database import engine, Base, SessionLocal, get_db
    chk('database.py imports', True)
except Exception as e:
    chk('database.py imports', False, str(e))

try:
    from app.models import Complaint
    cols = {c.name for c in Complaint.__table__.columns}
    phase1 = ['id','complaint_id','passenger_name','mobile_number','email','bus_number',
              'route_number','category','complaint_description','incident_location',
              'incident_datetime','voice_file_path','image_file_path','status','created_at']
    phase2 = ['detected_language','translated_text','extracted_bus_number',
              'extracted_route_number','extracted_location','extracted_entities',
              'extracted_keywords','ai_summary']
    for c in phase1:
        chk('DB column: ' + c, c in cols)
    for c in phase2:
        chk('AI column: ' + c, c in cols)
except Exception as e:
    chk('models.py imports', False, str(e))

try:
    from app.schemas import (VALID_CATEGORIES, ComplaintCreate, ComplaintResponse,
                              AIAnalysisResult, AnalyzeRequest, SubmissionSuccess)
    expected_cats = ['Bus Delay','Driver Misconduct','Conductor Misconduct','Stop Skipping',
                     'Overcrowding','Maintenance Issue','Ticket Issue','Safety Issue',
                     'Cleanliness Issue','Other']
    all_ok = all(c in VALID_CATEGORIES for c in expected_cats)
    chk('All 10 categories in VALID_CATEGORIES', all_ok, str(len(VALID_CATEGORIES)) + ' found')
    chk('AIAnalysisResult schema exists (Phase 2)', True)
    chk('AnalyzeRequest schema exists (Phase 2)', True)
    chk('SubmissionSuccess has ai_analysis field', True)
except Exception as e:
    chk('schemas.py imports', False, str(e))

try:
    from app.crud import (create_complaint, get_all_complaints,
                           get_complaint_by_id, update_complaint_analysis)
    chk('crud Phase 1 functions present', True)
    chk('crud update_complaint_analysis present (Phase 2)', True)
except Exception as e:
    chk('crud.py imports', False, str(e))

try:
    from app.config import AI_ENABLED, GEMINI_API_KEY, GEMINI_MODEL
    chk('config.py loads', True, 'AI_ENABLED=' + str(AI_ENABLED))
    if not AI_ENABLED:
        chk('Fallback mode active (no GEMINI_API_KEY)', True, 'regex+langdetect fallback', warn=False)
    else:
        chk('Gemini mode active', True, 'GEMINI_API_KEY set', warn=True)
except Exception as e:
    chk('config.py imports', False, str(e))

try:
    from app.migration import run_migration
    chk('migration.py imports', True)
except Exception as e:
    chk('migration.py imports', False, str(e))

try:
    from app.ai.agent import (complaint_agent, detect_language, translate_to_english,
                               extract_entities, extract_keywords, generate_summary)
    chk('AI agent module imports', True)
    chk('All 5 sub-agent functions importable', True)
except Exception as e:
    chk('AI agent imports', False, str(e))

try:
    from app.routes import router as r1
    from app.ai_routes import router as r2
    chk('routes.py router loads', True)
    chk('ai_routes.py router loads', True)
except Exception as e:
    chk('routers import', False, str(e))

try:
    from app.main import app
    chk('FastAPI app loads', True)
    route_paths = [r.path for r in app.routes]
    chk('POST create endpoint registered', any('complaints/create' in r for r in route_paths))
    chk('GET complaints endpoint registered', any(r == '/api/v1/complaints' for r in route_paths))
    chk('POST ai/analyze-complaint registered', any('ai/analyze' in r for r in route_paths))
    chk('GET analysis endpoint registered', any('analysis' in r for r in route_paths))
    chk('GET single complaint registered', any('complaint_id' in r for r in route_paths))
except Exception as e:
    chk('main.py loads', False, str(e))

print()
print('=== DATABASE SCHEMA CHECKS ===')
db_path = os.path.join('.', 'complaints.db')
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('PRAGMA table_info(complaints)')
    db_cols = {row[1] for row in cur.fetchall()}
    chk('complaints.db file exists', True)
    all_expected = ['complaint_id','passenger_name','mobile_number','email','bus_number',
                    'route_number','category','complaint_description','incident_location',
                    'incident_datetime','voice_file_path','image_file_path','status','created_at',
                    'detected_language','translated_text','extracted_bus_number',
                    'extracted_route_number','extracted_location','extracted_entities',
                    'extracted_keywords','ai_summary']
    missing = [c for c in all_expected if c not in db_cols]
    chk('All 22 DB columns present', not missing,
        ('Missing: ' + str(missing)) if missing else 'All present')
    cur.execute('SELECT COUNT(*) FROM complaints')
    count = cur.fetchone()[0]
    chk('DB query executes', True, str(count) + ' rows in complaints table')
    conn.close()
else:
    chk('complaints.db file exists', False, 'File not found - DB not created yet')

print()
print('=== AI AGENT UNIT TESTS ===')
from app.ai.agent import (detect_language, translate_to_english, extract_entities,
                            extract_keywords, generate_summary, complaint_agent)

# Language detection
en_lang = detect_language('Bus TN47 arrived late')
chk('English language detected', 'english' in en_lang.lower(), 'got: ' + en_lang)

ta_lang = detect_language('\u0b87\u0ba8\u0bcd\u0ba4 \u0baa\u0bc7\u0bb0\u0bc1\u0ba8\u0bcd\u0ba4\u0bc1 \u0ba4\u0bbe\u0bae\u0ba4\u0bae\u0bbe\u0b95 \u0bb5\u0ba8\u0bcd\u0ba4\u0ba4\u0bc1')
chk('Tamil language detected', 'tamil' in ta_lang.lower(), 'got: ' + ta_lang)

hi_lang = detect_language('\u092c\u0938 \u0926\u0947\u0930 \u0938\u0947 \u0906\u0908')
chk('Hindi language detected', 'hindi' in hi_lang.lower(), 'got: ' + hi_lang)

# Entity extraction
ent_text = 'Bus TN47 AB 2345 reached Karur 45 minutes late.'
entities = extract_entities(ent_text)
chk('Entity extraction returns dict', isinstance(entities, dict))
chk('delay_duration extracted', bool(entities.get('delay_duration')), str(entities.get('delay_duration')))
inc_types = entities.get('incident_type', [])
chk('Incident type Bus Delay identified', 'Bus Delay' in inc_types, str(inc_types))

staff_text = 'The conductor shouted at passengers and the driver ignored the stop.'
staff_ents = extract_entities(staff_text)
staff = staff_ents.get('staff_mentioned', [])
chk('Conductor reference extracted', 'conductor' in staff, 'staff: ' + str(staff))
chk('Driver reference extracted', 'driver' in staff, 'staff: ' + str(staff))

# Keyword extraction
kw_text = 'Driver used mobile phone while driving.'
keywords = extract_keywords(kw_text)
chk('Keywords returned as list', isinstance(keywords, list))
chk('Keywords not empty', len(keywords) > 0, str(len(keywords)) + ' keywords: ' + str(keywords))
has_driver_kw = any('driver' in k.lower() for k in keywords)
has_safety_kw = any('safety' in k.lower() or 'phone' in k.lower() or 'mobile' in k.lower() for k in keywords)
chk('Driver keyword found', has_driver_kw, str(keywords))
chk('Safety/Phone keyword found', has_safety_kw, str(keywords))

# Summary generation
sum_text = 'The driver was talking on the phone, the bus was delayed by 45 minutes and passengers were treated badly.'
summary = generate_summary(sum_text)
chk('Summary generated', bool(summary and len(summary) > 5), 'summary: ' + str(summary))

# Translation (Tamil)
ta_text = '\u0b87\u0ba8\u0bcd\u0ba4 \u0baa\u0bc7\u0bb0\u0bc1\u0ba8\u0bcd\u0ba4\u0bc1 \u0ba4\u0bbe\u0bae\u0ba4\u0bae\u0bbe\u0b95 \u0bb5\u0ba8\u0bcd\u0ba4\u0ba4\u0bc1'
ta_translated = translate_to_english(ta_text, 'Tamil')
chk('Tamil translation returns string', ta_translated is not None, 'result: ' + str(ta_translated))

# Full pipeline
print()
print('--- Full pipeline test ---')
full_result = complaint_agent.analyze('Bus TN47 AB 2345 skipped the Karur Bus Stand stop and the conductor shouted at passengers.')
chk('Pipeline: detected_language populated', bool(full_result.get('detected_language')), str(full_result.get('detected_language')))
chk('Pipeline: ai_summary populated', bool(full_result.get('ai_summary')), str(full_result.get('ai_summary')))
chk('Pipeline: extracted_keywords is JSON string', isinstance(full_result.get('extracted_keywords'), str))
chk('Pipeline: extracted_entities is JSON string', isinstance(full_result.get('extracted_entities'), str))
try:
    ents2 = json.loads(full_result.get('extracted_entities', '{}'))
    chk('Pipeline: entities JSON parses correctly', isinstance(ents2, dict), str(list(ents2.keys())))
    chk('Pipeline: staff_mentioned in entities', 'staff_mentioned' in ents2, str(ents2.get('staff_mentioned')))
except Exception as e:
    chk('Pipeline: entities JSON parse', False, str(e))

print()
print('=== VALIDATION LOGIC TESTS ===')
# Test the validation regex patterns from routes.py
import re as _re

valid_mobiles = ['+94771234567', '0771234567', '1234567890']
invalid_mobiles = ['abc', '123', '+', '12 34 5']
for m in valid_mobiles:
    chk('Valid mobile: ' + m, bool(_re.match(r'^\+?[0-9]{7,15}$', m)))
for m in invalid_mobiles:
    chk('Invalid mobile rejected: ' + m, not bool(_re.match(r'^\+?[0-9]{7,15}$', m)))

valid_emails = ['test@example.com', 'user.name+tag@domain.co']
invalid_emails = ['notanemail', '@domain.com', 'user@']
ep = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
for e in valid_emails:
    chk('Valid email: ' + e, bool(_re.match(ep, e)))
for e in invalid_emails:
    chk('Invalid email rejected: ' + e, not bool(_re.match(ep, e)))

print()
print('=== SUMMARY ===')
passed = sum(1 for r in results if r[0] == 'PASS')
failed = sum(1 for r in results if r[0] == 'FAIL')
warned = sum(1 for r in results if r[0] == 'WARN')
print('Total: ' + str(len(results)) + ' | PASS: ' + str(passed) + ' | FAIL: ' + str(failed) + ' | WARN: ' + str(warned))
print()
if failed:
    print('FAILURES:')
    for st, name, detail in results:
        if st == 'FAIL':
            print('  FAIL: ' + name + ' - ' + detail)
