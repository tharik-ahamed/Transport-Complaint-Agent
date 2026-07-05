"""
Complaint Analysis Agent — Phase 2
===================================
Orchestrates all AI sub-agents:
  1. Language Detection Agent
  2. Translation Agent
  3. Entity Extraction Agent
  4. Keyword Extraction Agent
  5. AI Summary Agent

Works in two modes:
  - GEMINI mode  : Uses Google Gemini 1.5 Flash (requires GEMINI_API_KEY in .env)
  - FALLBACK mode: Regex + langdetect + deep-translator (no API key needed)
"""

from __future__ import annotations

import json
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Gemini setup (optional)
# ──────────────────────────────────────────────
try:
    import google.generativeai as genai
    from app.config import GEMINI_API_KEY, AI_ENABLED, GEMINI_MODEL
    if AI_ENABLED:
        genai.configure(api_key=GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel(GEMINI_MODEL)
    else:
        _gemini_model = None
except Exception:
    AI_ENABLED = False
    _gemini_model = None


# ──────────────────────────────────────────────
# langdetect (offline, no API needed)
# ──────────────────────────────────────────────
try:
    from langdetect import detect as _langdetect
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

# ──────────────────────────────────────────────
# deep-translator (free, uses Google Translate)
# ──────────────────────────────────────────────
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False


# ──────────────────────────────────────────────
# Language code → display name mapping
# ──────────────────────────────────────────────
LANG_MAP = {
    "en": "English",
    "ta": "Tamil",
    "hi": "Hindi",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "ar": "Arabic",
    "zh-cn": "Chinese",
    "zh-tw": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "pt": "Portuguese",
    "ru": "Russian",
    "ur": "Urdu",
    "ml": "Malayalam",
    "te": "Telugu",
    "kn": "Kannada",
    "bn": "Bengali",
    "mr": "Marathi",
    "gu": "Gujarati",
}

# ──────────────────────────────────────────────
# Regex patterns for fallback extraction
# ──────────────────────────────────────────────
BUS_NUMBER_PATTERNS = [
    r'\b([A-Z]{2,3}[-\s]?\d{1,2}[A-Z]{0,2}[-\s]?\d{3,4})\b',
    r'\bbus\s+(?:number|no\.?|#)?\s*([A-Z0-9\-\s]{3,12})\b',
    r'\b(\d{1,3}[A-Z]{0,2})\b(?=\s+(?:bus|route))',
    r'(?:bus|vehicle)\s+([A-Z0-9\-]{2,12})',
]

ROUTE_NUMBER_PATTERNS = [
    r'\broute\s+(?:number|no\.?)?\s*([A-Z0-9\-]{1,10})\b',
    r'\bline\s+(?:number|no\.?)?\s*([A-Z0-9\-]{1,10})\b',
    r'\b([0-9]{1,3}[A-Z]?)\s+(?:route|line)\b',
]

LOCATION_PATTERNS = [
    r'(?:at|near|from|to|in|by|around)\s+(?:the\s+)?([A-Z][a-zA-Z\s]{3,40}(?:bus\s+stand|stop|station|stand|junction|road|street|area|town|city))',
    r'([A-Z][a-zA-Z\s]{2,30}(?:bus\s+stand|bus\s+stop|bus\s+station|stop|station|junction))',
    r'(?:at|near|from|to|in)\s+([A-Z][a-zA-Z\s]{3,30})\b',
]

DELAY_PATTERNS = [
    r'(\d+)\s*(?:hours?|hrs?|minutes?|mins?)\s*(?:late|delay|delayed)',
    r'(?:late|delay(?:ed)?)\s+(?:by\s+)?(\d+)\s*(?:hours?|hrs?|minutes?|mins?)',
    r'delayed?\s+(?:by\s+)?(\d+)\s*(?:hours?|minutes?)',
]

TIME_PATTERNS = [
    r'\b(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)\b',
    r'\b(morning|afternoon|evening|night|midnight|noon)\b',
    r'\b(\d{1,2}\s*(?:AM|PM|am|pm))\b',
]

STAFF_PATTERNS = {
    "driver": r'\b(?:driver|operator)\b',
    "conductor": r'\bconductor\b',
}

SAFETY_KEYWORDS = ["phone", "mobile", "drunk", "rash", "speed", "reckless", "accident", "dangerous", "unsafe"]
MISCONDUCT_KEYWORDS = ["shout", "abuse", "rude", "misbehave", "misconduct", "harass", "threaten", "fight"]


def _safe_json_parse(text: str) -> dict | list | None:
    """Attempt to parse JSON from Gemini response, handling markdown fences."""
    text = text.strip()
    # Remove markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _gemini_call(prompt: str) -> Optional[str]:
    """Make a Gemini API call and return the text response."""
    if not AI_ENABLED or _gemini_model is None:
        return None
    try:
        response = _gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.warning(f"Gemini API call failed: {e}")
        return None


# ══════════════════════════════════════════════
# AGENT 1: Language Detection
# ══════════════════════════════════════════════
def detect_language(text: str) -> str:
    """
    Detect the language of the complaint text.
    Returns a human-readable language name.
    Priority: Gemini → langdetect → 'Unknown'
    """
    # Try Gemini first
    if AI_ENABLED:
        prompt = f"""Detect the language of the following text. Return ONLY a valid JSON object with a single key "language" whose value is one of: "English", "Tamil", "Hindi", or the actual language name if different.

Text: "{text}"

Return only the JSON object, nothing else."""
        result = _gemini_call(prompt)
        if result:
            parsed = _safe_json_parse(result)
            if parsed and isinstance(parsed, dict) and "language" in parsed:
                return parsed["language"]

    # Fallback: langdetect
    if LANGDETECT_AVAILABLE:
        try:
            lang_code = _langdetect(text)
            return LANG_MAP.get(lang_code, f"Other ({lang_code})")
        except Exception:
            pass

    return "Unknown"


# ══════════════════════════════════════════════
# AGENT 2: Translation
# ══════════════════════════════════════════════
def translate_to_english(text: str, source_language: str) -> Optional[str]:
    """
    Translate complaint text to English.
    Returns None if already English or translation fails.
    Priority: Gemini → deep-translator → None
    """
    if source_language.lower() in ("english", "unknown"):
        return None

    # Try Gemini first
    if AI_ENABLED:
        prompt = f"""Translate the following text to English. Return ONLY the translated English text, nothing else.

Text: "{text}" """
        result = _gemini_call(prompt)
        if result:
            # Clean any surrounding quotes
            return result.strip('"').strip("'").strip()

    # Fallback: deep-translator
    if TRANSLATOR_AVAILABLE:
        try:
            translated = GoogleTranslator(source="auto", target="en").translate(text)
            return translated
        except Exception as e:
            logger.warning(f"Translation failed: {e}")

    return None


# ══════════════════════════════════════════════
# AGENT 3: Entity Extraction
# ══════════════════════════════════════════════
def extract_entities(text: str) -> dict:
    """
    Extract structured entities from complaint text.
    Returns dict with bus_number, route_number, location, delay, staff, time_reference.
    Priority: Gemini → Regex
    """
    # Try Gemini first
    if AI_ENABLED:
        prompt = f"""Extract structured information from this transport complaint text. Return ONLY a valid JSON object with exactly these keys (use null if not found):
{{
  "bus_number": "string or null",
  "route_number": "string or null",
  "incident_location": "string or null",
  "delay_duration": "string or null",
  "staff_mentioned": ["list of strings: driver/conductor"],
  "time_reference": "string or null",
  "incident_type": ["list of complaint types identified"]
}}

Text: "{text}"

Return only the JSON object, nothing else."""
        result = _gemini_call(prompt)
        if result:
            parsed = _safe_json_parse(result)
            if parsed and isinstance(parsed, dict):
                return parsed

    # Fallback: regex-based extraction
    return _regex_extract_entities(text)


def _regex_extract_entities(text: str) -> dict:
    """Regex-based entity extraction fallback."""
    result = {
        "bus_number": None,
        "route_number": None,
        "incident_location": None,
        "delay_duration": None,
        "staff_mentioned": [],
        "time_reference": None,
        "incident_type": [],
    }

    # Extract bus number
    for pattern in BUS_NUMBER_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["bus_number"] = match.group(1).strip()
            break

    # Extract route number
    for pattern in ROUTE_NUMBER_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["route_number"] = match.group(1).strip()
            break

    # Extract location
    for pattern in LOCATION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["incident_location"] = match.group(1).strip()
            break

    # Extract delay duration
    for pattern in DELAY_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["delay_duration"] = match.group(0).strip()
            break

    # Extract time reference
    for pattern in TIME_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["time_reference"] = match.group(1).strip()
            break

    # Extract staff mentioned
    staff = []
    for role, pattern in STAFF_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            staff.append(role)
    result["staff_mentioned"] = staff

    # Detect incident types
    incident_types = []
    text_lower = text.lower()
    if any(w in text_lower for w in ["late", "delay", "delayed", "minutes late", "hours late"]):
        incident_types.append("Bus Delay")
    if any(w in text_lower for w in ["skip", "skipped", "missed", "didn't stop", "did not stop"]):
        incident_types.append("Stop Skipping")
    if "driver" in text_lower and any(w in text_lower for w in MISCONDUCT_KEYWORDS + ["phone", "mobile"]):
        incident_types.append("Driver Misconduct")
    if "conductor" in text_lower and any(w in text_lower for w in MISCONDUCT_KEYWORDS):
        incident_types.append("Conductor Misconduct")
    if any(w in text_lower for w in ["crowd", "overcrowd", "packed", "no space", "standing"]):
        incident_types.append("Overcrowding")
    if any(w in text_lower for w in SAFETY_KEYWORDS):
        incident_types.append("Safety Issue")
    if any(w in text_lower for w in ["dirty", "clean", "smell", "filth", "hygiene"]):
        incident_types.append("Cleanliness Issue")
    if any(w in text_lower for w in ["ticket", "overcharge", "fare", "extra charge"]):
        incident_types.append("Ticket Issue")
    if any(w in text_lower for w in ["broken", "repair", "engine", "tyre", "tire", "AC", "air condition"]):
        incident_types.append("Maintenance Issue")
    result["incident_type"] = incident_types

    return result


# ══════════════════════════════════════════════
# AGENT 4: Keyword Extraction
# ══════════════════════════════════════════════
def extract_keywords(text: str) -> list[str]:
    """
    Extract important keywords from complaint text.
    Priority: Gemini → Rule-based
    """
    # Try Gemini first
    if AI_ENABLED:
        prompt = f"""Extract 4 to 8 important keywords or short phrases from this transport complaint. Return ONLY a valid JSON array of strings.

Text: "{text}"

Return only the JSON array, nothing else. Example: ["bus delay", "rude conductor", "Main Street stop"]"""
        result = _gemini_call(prompt)
        if result:
            parsed = _safe_json_parse(result)
            if parsed and isinstance(parsed, list):
                return [str(k) for k in parsed]

    # Fallback: rule-based keyword extraction
    return _rule_based_keywords(text)


def _rule_based_keywords(text: str) -> list[str]:
    """Extract keywords using rules and stop-word filtering."""
    STOP_WORDS = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "to", "of", "in",
        "on", "at", "by", "for", "with", "about", "from", "into", "through",
        "and", "but", "or", "nor", "so", "yet", "both", "either", "neither",
        "not", "no", "this", "that", "these", "those", "my", "your", "his",
        "her", "its", "our", "their", "i", "me", "we", "you", "he", "she",
        "it", "they", "what", "which", "who", "whom", "when", "where", "why",
        "how", "all", "each", "every", "both", "few", "more", "most", "other",
        "some", "such", "than", "too", "very", "just", "because", "as", "until",
        "while", "also", "very", "so",
    }

    # Predefined transport keywords to look for
    IMPORTANT_KEYWORDS = {
        "bus delay": ["late", "delay", "delayed", "minutes late", "hours late"],
        "stop skipping": ["skip", "skipped", "missed stop", "didn't stop"],
        "driver misconduct": ["driver"],
        "conductor misconduct": ["conductor"],
        "overcrowding": ["crowd", "overcrowded", "packed", "standing"],
        "safety issue": ["safety", "unsafe", "accident", "reckless", "drunk", "phone", "mobile"],
        "cleanliness": ["dirty", "clean", "smell", "filth"],
        "ticket issue": ["ticket", "overcharge", "fare"],
        "maintenance": ["broken", "repair", "AC", "tyre"],
        "passenger": ["passenger", "passengers"],
        "abuse": ["abuse", "abused", "shout", "shouted"],
        "rude": ["rude", "rudely"],
        "phone": ["phone", "mobile"],
        "accident": ["accident", "crash"],
    }

    found_keywords = []
    text_lower = text.lower()

    for keyword, triggers in IMPORTANT_KEYWORDS.items():
        if any(t in text_lower for t in triggers):
            found_keywords.append(keyword.title())

    # Extract proper nouns (capitalized words not at sentence start)
    words = re.findall(r'\b([A-Z][a-z]{2,})\b', text)
    for word in words:
        if word.lower() not in STOP_WORDS and word not in found_keywords:
            found_keywords.append(word)

    return list(dict.fromkeys(found_keywords))[:8]  # dedupe, max 8


# ══════════════════════════════════════════════
# AGENT 5: AI Summary
# ══════════════════════════════════════════════
def generate_summary(text: str) -> str:
    """
    Generate a concise summary of the complaint.
    Priority: Gemini → Extractive fallback
    """
    # Try Gemini first
    if AI_ENABLED:
        prompt = f"""Write a concise one-sentence summary (maximum 25 words) of this transport complaint. Be specific about the issue.

Text: "{text}"

Return only the summary sentence, nothing else."""
        result = _gemini_call(prompt)
        if result:
            return result.strip('"').strip("'").strip()

    # Fallback: extractive summary (first sentence, truncated)
    return _extractive_summary(text)


def _extractive_summary(text: str) -> str:
    """Extract the first meaningful sentence as a summary."""
    sentences = re.split(r'[.!?]+', text.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 15]
    if sentences:
        first = sentences[0]
        if len(first) > 120:
            first = first[:120].rsplit(' ', 1)[0] + "..."
        return first
    return text[:100] + ("..." if len(text) > 100 else "")


# ══════════════════════════════════════════════
# PHASE 3 AGENTS
# ══════════════════════════════════════════════

# ── Agent 6: Sentiment Analysis ─────────────────────────────────────
def analyze_sentiment(text: str) -> dict:
    """
    Determine the emotional tone of the complaint.
    Returns dict: {"sentiment": str, "confidence_score": float}
    Sentiments: "Positive", "Neutral", "Negative", "Highly Negative"
    """
    if AI_ENABLED:
        prompt = f"""Analyze the sentiment of the following complaint text. Return ONLY a valid JSON object with exactly these keys:
{{
  "sentiment": "one of: Positive, Neutral, Negative, Highly Negative",
  "confidence_score": a float between 0.0 and 1.0
}}

Text: "{text}"

Return only the JSON object, nothing else."""
        result = _gemini_call(prompt)
        if result:
            parsed = _safe_json_parse(result)
            if parsed and isinstance(parsed, dict) and "sentiment" in parsed:
                return {
                    "sentiment": parsed["sentiment"],
                    "confidence_score": float(parsed.get("confidence_score", 0.85))
                }

    # Fallback rule-based sentiment
    text_lower = text.lower()
    pos_words = ["good", "excellent", "helpful", "clean", "polite", "friendly", "satisfied", "politely", "kind"]
    neg_words = ["late", "delay", "rude", "shouted", "crowded", "dirty", "slow", "missed", "skip", "overcharge", "bad", "worst"]
    highly_neg_words = ["abuse", "drunk", "fight", "harass", "accident", "unsafe", "reckless", "threaten", "danger", "violent", "stole", "steal"]

    pos_count = sum(1 for w in pos_words if w in text_lower)
    neg_count = sum(1 for w in neg_words if w in text_lower)
    highly_neg_count = sum(1 for w in highly_neg_words if w in text_lower)

    score = pos_count - neg_count - (highly_neg_count * 2)

    if score >= 1:
        sentiment = "Positive"
    elif score == 0:
        sentiment = "Neutral"
    elif score in (-1, -2):
        sentiment = "Negative"
    else:
        sentiment = "Highly Negative"

    return {
        "sentiment": sentiment,
        "confidence_score": 0.85
    }


# ── Agent 7: Complaint Classification ───────────────────────────────
def classify_categories(text: str) -> list[str]:
    """
    Classify complaints into one or more categories.
    Categories: "Bus Delay", "Driver Misconduct", "Conductor Misconduct",
    "Stop Skipping", "Overcrowding", "Maintenance Issue", "Ticket Issue",
    "Safety Issue", "Cleanliness Issue", "Route Deviation", "Other"
    """
    if AI_ENABLED:
        prompt = f"""Classify this transport complaint into one or more of these categories:
"Bus Delay", "Driver Misconduct", "Conductor Misconduct", "Stop Skipping", "Overcrowding", "Maintenance Issue", "Ticket Issue", "Safety Issue", "Cleanliness Issue", "Route Deviation", "Other".

Return ONLY a valid JSON object with a single key "categories" containing a list of strings.

Text: "{text}"

Return only the JSON object, nothing else."""
        result = _gemini_call(prompt)
        if result:
            parsed = _safe_json_parse(result)
            if parsed and isinstance(parsed, dict) and "categories" in parsed:
                return [str(c) for c in parsed["categories"] if c in [
                    "Bus Delay", "Driver Misconduct", "Conductor Misconduct",
                    "Stop Skipping", "Overcrowding", "Maintenance Issue", "Ticket Issue",
                    "Safety Issue", "Cleanliness Issue", "Route Deviation", "Other"
                ]]

    # Fallback rule-based classification
    categories = []
    text_lower = text.lower()

    if any(w in text_lower for w in ["late", "delay", "delayed", "behind schedule", "hours late", "minutes late"]):
        categories.append("Bus Delay")
    if "driver" in text_lower and any(w in text_lower for w in ["rude", "shout", "misbehave", "ignore", "abuse", "argument", "fight"]):
        categories.append("Driver Misconduct")
    if "conductor" in text_lower and any(w in text_lower for w in ["rude", "shout", "misbehave", "abuse", "argument", "fight", "ticket"]):
        categories.append("Conductor Misconduct")
    if any(w in text_lower for w in ["skip", "skipped", "didn't stop", "did not stop", "missed stop"]):
        categories.append("Stop Skipping")
    if any(w in text_lower for w in ["crowd", "overcrowd", "packed", "standing only", "no seats", "no seat"]):
        categories.append("Overcrowding")
    if any(w in text_lower for w in ["broken", "repair", "window", "engine", "tyre", "tire", "door", "AC", "air condition"]):
        categories.append("Maintenance Issue")
    if any(w in text_lower for w in ["ticket", "fare", "charge", "overcharge", "change", "no balance", "refund"]):
        categories.append("Ticket Issue")
    if any(w in text_lower for w in ["drunk", "reckless", "speeding", "rash", "dangerous", "accident", "unsafe", "brakes"]):
        categories.append("Safety Issue")
    if any(w in text_lower for w in ["dirty", "clean", "smell", "filth", "litter", "rubbish", "dusty"]):
        categories.append("Cleanliness Issue")
    if any(w in text_lower for w in ["deviate", "route change", "wrong route", "different way", "different road", "avoided route", "deviation"]):
        categories.append("Route Deviation")

    if not categories:
        categories.append("Other")

    return categories


# ── Agent 8: Severity Assessment ───────────────────────────────────
def assess_severity(text: str, categories: list[str]) -> dict:
    """
    Assign a severity level: "Low", "Medium", "High", "Critical".
    Returns dict: {"severity": str, "severity_score": float}
    """
    if AI_ENABLED:
        prompt = f"""Assess the severity of the following complaint. Return ONLY a valid JSON object with exactly these keys:
{{
  "severity": "one of: Low, Medium, High, Critical",
  "severity_score": a float between 0.0 and 1.0 (Low is ~0.2, Medium is ~0.5, High is ~0.8, Critical is ~1.0)
}}

Text: "{text}"

Return only the JSON object, nothing else."""
        result = _gemini_call(prompt)
        if result:
            parsed = _safe_json_parse(result)
            if parsed and isinstance(parsed, dict) and "severity" in parsed:
                return {
                    "severity": parsed["severity"],
                    "severity_score": float(parsed.get("severity_score", 0.5))
                }

    # Fallback severity
    if "Safety Issue" in categories or any(w in text.lower() for w in ["drunk", "reckless", "speeding", "accident", "dangerous", "violent"]):
        return {"severity": "Critical", "severity_score": 0.95}
    elif "Driver Misconduct" in categories or "Conductor Misconduct" in categories or "Route Deviation" in categories or "abuse" in text.lower():
        return {"severity": "High", "severity_score": 0.75}
    elif "Bus Delay" in categories or "Stop Skipping" in categories or "Overcrowding" in categories or "Ticket Issue" in categories:
        return {"severity": "Medium", "severity_score": 0.50}
    else:
        return {"severity": "Low", "severity_score": 0.20}


# ── Agent 9: Priority Ranking ──────────────────────────────────────
def calculate_priority(severity: str, sentiment: str, categories: list[str]) -> str:
    """
    Assign priority level: "P1" (Immediate), "P2" (High), "P3" (Normal), "P4" (Low).
    """
    if severity == "Critical" or "Safety Issue" in categories:
        return "P1"
    elif severity == "High" or (severity == "Medium" and sentiment == "Highly Negative"):
        return "P2"
    elif severity == "Medium" or sentiment in ("Negative", "Highly Negative"):
        return "P3"
    else:
        return "P4"


# ── Agent 10: Recommendation Agent ──────────────────────────────────
def generate_recommendation(text: str, categories: list[str]) -> str:
    """
    Generate actionable next steps based on complaint details.
    """
    if AI_ENABLED:
        prompt = f"""Generate a recommended action for transport operators based on the following complaint text. Keep it concise, professional, and actionable. Return ONLY a valid JSON object with key "recommended_action".

Text: "{text}"

Return only the JSON object, nothing else."""
        result = _gemini_call(prompt)
        if result:
            parsed = _safe_json_parse(result)
            if parsed and isinstance(parsed, dict) and "recommended_action" in parsed:
                return parsed["recommended_action"]

    # Fallback recommendation rules
    if "Safety Issue" in categories or "drunk" in text.lower() or "reckless" in text.lower():
        return "Initiate immediate safety investigation, suspend driver pending drug/alcohol test, and contact law enforcement if necessary."
    elif "Driver Misconduct" in categories or "Conductor Misconduct" in categories:
        return "Escalate to the operations manager for disciplinary review and schedule staff behavioral counseling."
    elif "Route Deviation" in categories:
        return "Audit GPS route telemetry, request driver logs, and issue formal warning regarding unauthorized path deviation."
    elif "Bus Delay" in categories or "Stop Skipping" in categories:
        return "Review schedule adherence reports for this route and optimize driver scheduling during peak congestion."
    elif "Overcrowding" in categories:
        return "Audit passenger counts for this route and allocate additional dispatch runs or larger double-decker buses."
    elif "Maintenance Issue" in categories:
        return "Flag bus ID for urgent depot maintenance inspection. Schedule repair of AC/seats/doors within 24 hours."
    elif "Ticket Issue" in categories:
        return "Audit electronic billing records for the trip and refund any fare discrepancy to the passenger."
    elif "Cleanliness Issue" in categories:
        return "Schedule immediate interior deep cleaning and cleanliness inspection at the next depot stop."
    else:
        return "Review passenger complaint details and contact complainant to gather additional incident feedback."


# ══════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ══════════════════════════════════════════════
class ComplaintAnalysisAgent:
    """
    Main AI agent that orchestrates all sub-agents.
    Returns a structured analysis dict ready for DB storage.
    """

    def analyze(self, complaint_text: str) -> dict:
        """
        Run full analysis pipeline on complaint text.
        Returns dict matching all new DB columns.
        """
        if not complaint_text or len(complaint_text.strip()) < 3:
            return self._empty_result()

        text = complaint_text.strip()

        # 1. Detect language
        detected_language = detect_language(text)

        # 2. Translate if not English
        translated_text = None
        analysis_text = text  # text to use for further analysis
        if detected_language.lower() not in ("english", "unknown"):
            translated_text = translate_to_english(text, detected_language)
            if translated_text:
                analysis_text = translated_text

        # 3. Extract entities
        entities = extract_entities(analysis_text)

        # 4. Extract keywords
        keywords = extract_keywords(analysis_text)

        # 5. Generate summary
        ai_summary = generate_summary(analysis_text)

        # ── Phase 3 Agents ──

        # 6. Sentiment Analysis
        sentiment_res = analyze_sentiment(analysis_text)
        sentiment = sentiment_res["sentiment"]
        sentiment_score = sentiment_res["confidence_score"]

        # 7. Complaint Classification
        ai_cats = classify_categories(analysis_text)

        # 8. Severity Assessment
        severity_res = assess_severity(analysis_text, ai_cats)
        severity = severity_res["severity"]
        severity_score = severity_res["severity_score"]

        # 9. Priority Ranking
        priority_level = calculate_priority(severity, sentiment, ai_cats)

        # 10. Recommendation Agent
        recommended_action = generate_recommendation(analysis_text, ai_cats)

        return {
            "detected_language": detected_language,
            "translated_text": translated_text,
            "extracted_bus_number": entities.get("bus_number"),
            "extracted_route_number": entities.get("route_number"),
            "extracted_location": entities.get("incident_location"),
            "extracted_entities": json.dumps(entities, ensure_ascii=False),
            "extracted_keywords": json.dumps(keywords, ensure_ascii=False),
            "ai_summary": ai_summary,
            # Phase 3
            "sentiment": sentiment,
            "sentiment_score": float(sentiment_score),
            "ai_categories": json.dumps(ai_cats, ensure_ascii=False),
            "severity": severity,
            "severity_score": float(severity_score),
            "priority_level": priority_level,
            "recommended_action": recommended_action,
        }

    def _empty_result(self) -> dict:
        return {
            "detected_language": "Unknown",
            "translated_text": None,
            "extracted_bus_number": None,
            "extracted_route_number": None,
            "extracted_location": None,
            "extracted_entities": json.dumps({}),
            "extracted_keywords": json.dumps([]),
            "ai_summary": None,
            # Phase 3
            "sentiment": "Neutral",
            "sentiment_score": 0.5,
            "ai_categories": json.dumps(["Other"]),
            "severity": "Low",
            "severity_score": 0.2,
            "priority_level": "P4",
            "recommended_action": "Review passenger complaint details and request passenger feedback.",
        }


# Singleton instance
complaint_agent = ComplaintAnalysisAgent()

