"""
Phase 5 Predictive Analytics Engine
=====================================
Rule-based + statistical analytics engine.
Falls back to simple averages / linear extrapolation when data is sparse.
Does NOT require scikit-learn or pandas — pure Python + stdlib.

Public API:
    run_all_analytics(db)  ->  dict with all results
    compute_route_risks(complaints)
    compute_driver_risks(complaints)
    compute_bus_risks(complaints)
    compute_trends(complaints)
    compute_forecast(complaints)
    generate_recommendations(route_risks, driver_risks, bus_risks)
    generate_smart_alerts(complaints, route_risks, driver_risks)
"""
from __future__ import annotations

import json
import logging
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ── Risk thresholds ────────────────────────────────────────────────────
def _risk_level(score: float) -> str:
    if score >= 0.75: return "Critical"
    if score >= 0.50: return "High"
    if score >= 0.25: return "Medium"
    return "Low"


def _parse_json(value: Optional[str], fallback: list) -> list:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


# ══════════════════════════════════════════════════════════════════════
# FEATURE 1 — Trend Analysis
# ══════════════════════════════════════════════════════════════════════

def compute_trends(complaints: list) -> list[dict]:
    """
    Generates trend insights from complaint history.
    Returns list of trend dicts sorted by score desc.
    """
    total = len(complaints)
    if total == 0:
        return []

    trends: list[dict] = []
    now = datetime.now()

    # ── 1. Top route trend ─────────────────────────────────────────────
    route_counter: Counter = Counter()
    for c in complaints:
        if c.route_number:
            route_counter[c.route_number] += 1

    if route_counter:
        top_route, top_count = route_counter.most_common(1)[0]
        avg = total / max(len(route_counter), 1)
        pct_above = (top_count - avg) / avg * 100 if avg > 0 else 0
        score = min(top_count / total, 1.0)
        trends.append({
            "trend_type": "route",
            "subject": f"Route {top_route}",
            "trend_description": f"Route {top_route} accounts for {top_count} complaints ({round(top_count/total*100)}% of total), "
                                  f"{round(abs(pct_above))}% {'above' if pct_above > 0 else 'below'} average.",
            "trend_score": round(score, 3),
            "metadata": {"route": top_route, "count": top_count, "pct_of_total": round(top_count/total*100, 1)},
        })

    # ── 2. Top bus trend ───────────────────────────────────────────────
    bus_counter: Counter = Counter()
    for c in complaints:
        if c.bus_number:
            bus_counter[c.bus_number] += 1

    if bus_counter:
        top_bus, bus_count = bus_counter.most_common(1)[0]
        score = min(bus_count / total, 1.0)
        trends.append({
            "trend_type": "bus",
            "subject": f"Bus {top_bus}",
            "trend_description": f"Bus {top_bus} has {bus_count} complaints, the highest of any vehicle ({round(bus_count/total*100)}% of total).",
            "trend_score": round(score, 3),
            "metadata": {"bus": top_bus, "count": bus_count},
        })

    # ── 3. Weekday vs Weekend trend ────────────────────────────────────
    weekend_count = weekday_count = 0
    for c in complaints:
        if c.created_at:
            if c.created_at.weekday() >= 5:
                weekend_count += 1
            else:
                weekday_count += 1

    if weekend_count + weekday_count > 0:
        weekend_days = 2  # days in a week
        weekday_days = 5
        weekend_rate = weekend_count / weekend_days if weekend_days else 0
        weekday_rate = weekday_count / weekday_days if weekday_days else 0
        if weekday_rate > 0 and weekend_rate > 0:
            ratio = weekend_rate / weekday_rate
            if ratio > 1.2:
                desc = f"Complaint rate is {round((ratio-1)*100)}% higher on weekends than weekdays."
            elif ratio < 0.8:
                desc = f"Complaint rate is {round((1-ratio)*100)}% lower on weekends than weekdays."
            else:
                desc = f"Complaint rate is consistent across weekdays and weekends (ratio: {round(ratio, 2)})."
            score = min(abs(ratio - 1), 1.0)
            trends.append({
                "trend_type": "time",
                "subject": "Weekend Pattern",
                "trend_description": desc,
                "trend_score": round(score, 3),
                "metadata": {"weekend": weekend_count, "weekday": weekday_count, "ratio": round(ratio, 2)},
            })

    # ── 4. Category surge trend ────────────────────────────────────────
    cat_counter: Counter = Counter()
    for c in complaints:
        cats = _parse_json(c.ai_categories, [c.category] if c.category else [])
        for cat in cats:
            if cat:
                cat_counter[cat] += 1

    if cat_counter:
        top_cat, cat_count = cat_counter.most_common(1)[0]
        total_tags = sum(cat_counter.values())
        score = min(cat_count / total_tags, 1.0) if total_tags else 0
        trends.append({
            "trend_type": "category",
            "subject": top_cat,
            "trend_description": f'"{top_cat}" is the dominant complaint type with {cat_count} occurrences ({round(cat_count/total_tags*100)}% of all tags).',
            "trend_score": round(score, 3),
            "metadata": {"category": top_cat, "count": cat_count, "distribution": dict(cat_counter.most_common(5))},
        })

    # ── 5. Location trend ──────────────────────────────────────────────
    loc_counter: Counter = Counter()
    for c in complaints:
        if c.incident_location:
            # Normalize: first 30 chars
            loc_counter[c.incident_location[:30].strip()] += 1

    if len(loc_counter) > 0:
        top_loc, loc_count = loc_counter.most_common(1)[0]
        if loc_count > 1:  # Only report if more than one complaint at same location
            score = min(loc_count / total, 1.0)
            trends.append({
                "trend_type": "location",
                "subject": top_loc,
                "trend_description": f'Location "{top_loc}" has {loc_count} complaint(s), the highest concentration.',
                "trend_score": round(score, 3),
                "metadata": {"location": top_loc, "count": loc_count},
            })

    # ── 6. Severity trend ──────────────────────────────────────────────
    critical_count = sum(1 for c in complaints if c.severity == "Critical")
    high_count = sum(1 for c in complaints if c.severity == "High")
    serious = critical_count + high_count
    if serious > 0 and total > 0:
        pct = round(serious / total * 100)
        score = min(serious / total * 2, 1.0)
        trends.append({
            "trend_type": "severity",
            "subject": "High Severity Rate",
            "trend_description": f"{pct}% of complaints are High or Critical severity ({serious} of {total}).",
            "trend_score": round(score, 3),
            "metadata": {"critical": critical_count, "high": high_count, "total": total, "pct": pct},
        })

    # ── 7. Recent spike trend (last 7 days vs previous 7 days) ─────────
    cutoff_7d = now - timedelta(days=7)
    cutoff_14d = now - timedelta(days=14)
    recent = [c for c in complaints if c.created_at and c.created_at >= cutoff_7d]
    prev = [c for c in complaints if c.created_at and cutoff_14d <= c.created_at < cutoff_7d]

    if len(prev) > 0:
        change_pct = (len(recent) - len(prev)) / len(prev) * 100
        if abs(change_pct) > 20:
            direction = "increased" if change_pct > 0 else "decreased"
            score = min(abs(change_pct) / 100, 1.0)
            trends.append({
                "trend_type": "time",
                "subject": "Weekly Volume",
                "trend_description": f"Complaint volume {direction} by {round(abs(change_pct))}% this week ({len(recent)} vs {len(prev)} previous week).",
                "trend_score": round(score, 3),
                "metadata": {"recent_7d": len(recent), "prev_7d": len(prev), "change_pct": round(change_pct, 1)},
            })

    return sorted(trends, key=lambda x: -x["trend_score"])


# ══════════════════════════════════════════════════════════════════════
# FEATURE 2 — Route Risk Prediction
# ══════════════════════════════════════════════════════════════════════

def compute_route_risks(complaints: list) -> list[dict]:
    total = len(complaints)
    if total == 0:
        return []

    route_stats: dict[str, dict] = defaultdict(lambda: {
        "total": 0, "critical": 0, "high": 0, "safety": 0,
        "maintenance": 0, "delay": 0, "categories": Counter(),
    })

    for c in complaints:
        r = c.route_number or "Unknown"
        stats = route_stats[r]
        stats["total"] += 1
        if c.severity == "Critical":
            stats["critical"] += 1
        elif c.severity == "High":
            stats["high"] += 1

        cats = _parse_json(c.ai_categories, [c.category] if c.category else [])
        stats["categories"].update(cats)
        for cat in cats:
            if cat in ("Safety Issue",):
                stats["safety"] += 1
            elif cat in ("Maintenance Issue",):
                stats["maintenance"] += 1
            elif cat in ("Bus Delay", "Stop Skipping", "Route Deviation"):
                stats["delay"] += 1

    max_count = max(s["total"] for s in route_stats.values())
    results = []

    for route, stats in sorted(route_stats.items(), key=lambda x: -x[1]["total"]):
        freq_score = stats["total"] / max_count
        sev_score = ((stats["critical"] * 4 + stats["high"] * 2) / (stats["total"] * 4)) if stats["total"] else 0
        safety_score = min((stats["safety"] / stats["total"]) * 2, 1.0) if stats["total"] else 0
        risk_score = round(freq_score * 0.40 + sev_score * 0.35 + safety_score * 0.25, 3)

        top_cats = [c for c, _ in stats["categories"].most_common(3)]
        results.append({
            "route": route,
            "risk_score": risk_score,
            "risk_level": _risk_level(risk_score),
            "route_risk_score": risk_score,
            "route_risk_level": _risk_level(risk_score),
            "complaint_count": stats["total"],
            "safety_count": stats["safety"],
            "severe_count": stats["critical"] + stats["high"],
            "delay_count": stats["delay"],
            "maintenance_count": stats["maintenance"],
            "top_categories": top_cats,
        })

    return sorted(results, key=lambda x: -x["risk_score"])


# ══════════════════════════════════════════════════════════════════════
# FEATURE 3 — Driver Risk Assessment (proxy: bus_number)
# ══════════════════════════════════════════════════════════════════════

_DRIVER_RECS = {
    "Critical": "Immediate suspension pending investigation. Mandatory retraining and performance review required.",
    "High": "Urgent performance review required. Schedule safety training within 48 hours.",
    "Medium": "Schedule performance counselling. Monitor for next 30 days.",
    "Low": "Routine monitoring. No immediate action required.",
}


def compute_driver_risks(complaints: list) -> list[dict]:
    """Uses bus_number as driver proxy (same vehicle = same operator shift)."""
    total = len(complaints)
    if total == 0:
        return []

    bus_stats: dict[str, dict] = defaultdict(lambda: {
        "total": 0, "misconduct": 0, "safety": 0, "aggression": 0, "categories": Counter(),
    })

    for c in complaints:
        key = c.bus_number or "Unknown"
        stats = bus_stats[key]
        stats["total"] += 1
        cats = _parse_json(c.ai_categories, [c.category] if c.category else [])
        stats["categories"].update(cats)
        for cat in cats:
            if cat in ("Driver Misconduct", "Conductor Misconduct"):
                stats["misconduct"] += 1
            if cat == "Safety Issue":
                stats["safety"] += 1

    max_count = max(s["total"] for s in bus_stats.values())
    results = []

    for bus, stats in sorted(bus_stats.items(), key=lambda x: -x[1]["total"]):
        freq_score = stats["total"] / max_count
        misconduct_score = min((stats["misconduct"] / stats["total"]) * 2, 1.0) if stats["total"] else 0
        safety_score = min((stats["safety"] / stats["total"]) * 2, 1.0) if stats["total"] else 0
        risk_score = round(freq_score * 0.30 + misconduct_score * 0.45 + safety_score * 0.25, 3)
        level = _risk_level(risk_score)

        results.append({
            "driver_identifier": bus,
            "risk_score": risk_score,
            "risk_level": level,
            "driver_risk_score": risk_score,
            "driver_risk_level": level,
            "complaint_count": stats["total"],
            "misconduct_count": stats["misconduct"],
            "safety_count": stats["safety"],
            "top_categories": [c for c, _ in stats["categories"].most_common(3)],
            "recommendation": _DRIVER_RECS.get(level, _DRIVER_RECS["Low"]),
        })

    return sorted(results, key=lambda x: -x["risk_score"])


# ══════════════════════════════════════════════════════════════════════
# FEATURE 4 — Bus Health Intelligence
# ══════════════════════════════════════════════════════════════════════

def compute_bus_risks(complaints: list) -> list[dict]:
    total = len(complaints)
    if total == 0:
        return []

    bus_stats: dict[str, dict] = defaultdict(lambda: {
        "total": 0, "maintenance": 0, "overcrowding": 0, "breakdown": 0, "categories": Counter(),
    })

    for c in complaints:
        key = c.bus_number or "Unknown"
        stats = bus_stats[key]
        stats["total"] += 1
        cats = _parse_json(c.ai_categories, [c.category] if c.category else [])
        stats["categories"].update(cats)
        for cat in cats:
            if cat == "Maintenance Issue":
                stats["maintenance"] += 1
            elif cat == "Overcrowding":
                stats["overcrowding"] += 1

    max_count = max(s["total"] for s in bus_stats.values())
    results = []

    for bus, stats in sorted(bus_stats.items(), key=lambda x: -x[1]["total"]):
        maint_score = min((stats["maintenance"] / stats["total"]) * 3, 1.0) if stats["total"] else 0
        over_score = min((stats["overcrowding"] / stats["total"]) * 1.5, 1.0) if stats["total"] else 0
        freq_score = stats["total"] / max_count
        risk_score = round(maint_score * 0.50 + over_score * 0.25 + freq_score * 0.25, 3)

        results.append({
            "bus_number": bus,
            "maintenance_risk": _risk_level(risk_score),
            "risk_score": risk_score,
            "complaint_count": stats["total"],
            "maintenance_count": stats["maintenance"],
            "overcrowding_count": stats["overcrowding"],
            "top_categories": [c for c, _ in stats["categories"].most_common(3)],
        })

    return sorted(results, key=lambda x: -x["risk_score"])


# ══════════════════════════════════════════════════════════════════════
# FEATURE 5 — Complaint Forecasting (linear extrapolation)
# ══════════════════════════════════════════════════════════════════════

def compute_forecast(complaints: list) -> dict:
    daily: dict[str, int] = defaultdict(int)
    for c in complaints:
        if c.created_at:
            daily[c.created_at.date().isoformat()] += 1

    history = [{"date": d, "count": daily[d]} for d in sorted(daily.keys())]
    n = len(history)

    if n == 0:
        return {"daily_forecast": 0, "weekly_forecast": 0, "monthly_forecast": 0, "trend": "stable", "confidence": "Low", "history": []}

    if n < 3:
        avg = sum(h["count"] for h in history) / n
        return {
            "daily_forecast": round(avg, 1),
            "weekly_forecast": round(avg * 7, 0),
            "monthly_forecast": round(avg * 30, 0),
            "trend": "stable",
            "confidence": "Low",
            "note": "Insufficient historical data — using simple average.",
            "history": history,
        }

    # Linear regression: y = a + b*x
    x = list(range(n))
    y = [h["count"] for h in history]
    mean_x = sum(x) / n
    mean_y = sum(y) / n

    num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    den = sum((x[i] - mean_x) ** 2 for i in range(n))
    slope = num / den if den != 0 else 0
    intercept = mean_y - slope * mean_x

    next_x = n
    daily_forecast = max(intercept + slope * next_x, 0)
    weekly_forecast = sum(max(intercept + slope * (next_x + i), 0) for i in range(7))
    monthly_forecast = sum(max(intercept + slope * (next_x + i), 0) for i in range(30))

    # Next 14 days projected
    projection = [
        {"date": (datetime.now() + timedelta(days=i)).date().isoformat(),
         "predicted": round(max(intercept + slope * (next_x + i), 0), 1)}
        for i in range(14)
    ]

    trend = "increasing" if slope > 0.1 else ("decreasing" if slope < -0.1 else "stable")
    confidence = "High" if n >= 14 else ("Medium" if n >= 7 else "Low")

    return {
        "daily_forecast": round(daily_forecast, 1),
        "weekly_forecast": round(weekly_forecast, 0),
        "monthly_forecast": round(monthly_forecast, 0),
        "trend": trend,
        "slope": round(slope, 3),
        "confidence": confidence,
        "data_points": n,
        "history": history,
        "projection": projection,
    }


# ══════════════════════════════════════════════════════════════════════
# FEATURE 6 — Preventive Recommendations
# ══════════════════════════════════════════════════════════════════════

def generate_recommendations(
    route_risks: list[dict],
    driver_risks: list[dict],
    bus_risks: list[dict],
    forecast: dict,
    trends: list[dict],
) -> list[dict]:
    recs: list[dict] = []

    # From route risks
    for r in route_risks:
        if r["risk_level"] in ("Critical", "High"):
            recs.append({
                "rec_type": "route",
                "subject": f"Route {r['route']}",
                "recommendation": _route_rec(r),
                "priority": r["risk_level"],
            })

    # From driver risks
    for d in driver_risks:
        if d["risk_level"] in ("Critical", "High"):
            recs.append({
                "rec_type": "driver",
                "subject": f"Bus {d['driver_identifier']} (Operator)",
                "recommendation": d["recommendation"],
                "priority": d["risk_level"],
            })

    # From bus risks
    for b in bus_risks:
        if b["maintenance_risk"] in ("Critical", "High"):
            recs.append({
                "rec_type": "bus",
                "subject": f"Bus {b['bus_number']}",
                "recommendation": _bus_rec(b),
                "priority": b["maintenance_risk"],
            })

    # From forecast
    if forecast.get("trend") == "increasing":
        recs.append({
            "rec_type": "system",
            "subject": "Complaint Volume",
            "recommendation": f"Complaint volume is trending upward (slope: +{forecast.get('slope', 0)} per day). "
                               f"Forecast: {int(forecast.get('weekly_forecast', 0))} complaints next week. "
                               "Consider increasing monitoring and response capacity.",
            "priority": "High",
        })

    # From trends
    for t in trends:
        if t["trend_score"] >= 0.6 and t["trend_type"] == "severity":
            recs.append({
                "rec_type": "system",
                "subject": "High Severity Rate",
                "recommendation": t["trend_description"] + " Immediate review of operational standards recommended.",
                "priority": "Critical",
            })

    if not recs:
        recs.append({
            "rec_type": "system",
            "subject": "General Operations",
            "recommendation": "No critical risk indicators detected. Continue routine monitoring and quality checks.",
            "priority": "Low",
        })

    return sorted(recs, key=lambda x: ["Critical", "High", "Medium", "Low"].index(x["priority"]))


def _route_rec(r: dict) -> str:
    parts = []
    if r["safety_count"] > 0:
        parts.append(f"Conduct safety inspection on Route {r['route']}")
    if r["delay_count"] > 0:
        parts.append(f"Review scheduling and increase frequency on Route {r['route']}")
    parts.append(f"Deploy additional supervisors on Route {r['route']} for the next 30 days")
    return ". ".join(parts) + "."


def _bus_rec(b: dict) -> str:
    parts = [f"Schedule immediate maintenance inspection for Bus {b['bus_number']}"]
    if b["maintenance_count"] >= 2:
        parts.append("Consider temporarily removing from service until inspection is complete")
    if b["overcrowding_count"] > 0:
        parts.append("Review passenger capacity management procedures")
    return ". ".join(parts) + "."


# ══════════════════════════════════════════════════════════════════════
# FEATURE 8 — Smart Alerts
# ══════════════════════════════════════════════════════════════════════

ALERT_THRESHOLDS = {
    "route_spike_pct": 50,       # % increase triggers alert
    "driver_risk_threshold": 0.5, # risk_score above this triggers alert
    "bus_risk_threshold": 0.5,
    "safety_spike_pct": 20,
    "volume_spike_pct": 40,
}


def generate_smart_alerts(
    complaints: list,
    route_risks: list[dict],
    driver_risks: list[dict],
    bus_risks: list[dict],
    forecast: dict,
) -> list[dict]:
    alerts: list[dict] = []
    now = datetime.now()
    cutoff_7d = now - timedelta(days=7)
    cutoff_14d = now - timedelta(days=14)

    recent = [c for c in complaints if c.created_at and c.created_at >= cutoff_7d]
    prev = [c for c in complaints if c.created_at and cutoff_14d <= c.created_at < cutoff_7d]

    # ── Volume spike alert ─────────────────────────────────────────────
    if prev and len(prev) > 0:
        vol_change = (len(recent) - len(prev)) / len(prev) * 100
        if vol_change >= ALERT_THRESHOLDS["volume_spike_pct"]:
            alerts.append({
                "alert_type": "volume_spike",
                "subject": "Complaint Volume",
                "message": f"Alert: Complaint volume increased by {round(vol_change)}% this week ({len(recent)} vs {len(prev)} previous week).",
                "risk_level": "High" if vol_change >= 80 else "Medium",
            })

    # ── Route spike alerts ─────────────────────────────────────────────
    route_recent: Counter = Counter()
    route_prev: Counter = Counter()
    for c in recent:
        if c.route_number:
            route_recent[c.route_number] += 1
    for c in prev:
        if c.route_number:
            route_prev[c.route_number] += 1

    for route, r_count in route_recent.items():
        p_count = route_prev.get(route, 0)
        if p_count > 0:
            change = (r_count - p_count) / p_count * 100
            if change >= ALERT_THRESHOLDS["route_spike_pct"]:
                alerts.append({
                    "alert_type": "route_spike",
                    "subject": f"Route {route}",
                    "message": f"Alert: Route {route} complaint volume increased by {round(change)}% this week ({r_count} vs {p_count}).",
                    "risk_level": "Critical" if change >= 100 else "High",
                })
        elif r_count >= 3:  # New route appearing with 3+ complaints
            alerts.append({
                "alert_type": "route_spike",
                "subject": f"Route {route}",
                "message": f"Alert: Route {route} received {r_count} new complaints this week with no previous history.",
                "risk_level": "Medium",
            })

    # ── High driver risk alerts ────────────────────────────────────────
    for d in driver_risks:
        if d["risk_score"] >= ALERT_THRESHOLDS["driver_risk_threshold"]:
            alerts.append({
                "alert_type": "driver_risk",
                "subject": f"Bus {d['driver_identifier']}",
                "message": f"Alert: Bus {d['driver_identifier']} operator has risk score {d['risk_score']:.2f} ({d['risk_level']}). "
                            f"Misconduct: {d['misconduct_count']}, Safety: {d['safety_count']} complaints.",
                "risk_level": d["risk_level"],
            })

    # ── Bus maintenance alerts ─────────────────────────────────────────
    for b in bus_risks:
        if b["risk_score"] >= ALERT_THRESHOLDS["bus_risk_threshold"]:
            alerts.append({
                "alert_type": "bus_health",
                "subject": f"Bus {b['bus_number']}",
                "message": f"Alert: Bus {b['bus_number']} shows elevated maintenance risk ({b['maintenance_risk']}). "
                            f"Maintenance complaints: {b['maintenance_count']}.",
                "risk_level": b["maintenance_risk"],
            })

    # ── Safety spike alert ─────────────────────────────────────────────
    safety_recent = sum(1 for c in recent if c.category == "Safety Issue" or
                         "Safety Issue" in _parse_json(c.ai_categories, []))
    safety_prev = sum(1 for c in prev if c.category == "Safety Issue" or
                       "Safety Issue" in _parse_json(c.ai_categories, []))
    if safety_prev > 0:
        safety_change = (safety_recent - safety_prev) / safety_prev * 100
        if safety_change >= ALERT_THRESHOLDS["safety_spike_pct"]:
            alerts.append({
                "alert_type": "safety_spike",
                "subject": "Safety Complaints",
                "message": f"Alert: Safety complaints increased by {round(safety_change)}% this week ({safety_recent} vs {safety_prev}).",
                "risk_level": "Critical",
            })

    # ── Forecast warning ───────────────────────────────────────────────
    if forecast.get("trend") == "increasing" and forecast.get("weekly_forecast", 0) > len(complaints) * 0.3:
        alerts.append({
            "alert_type": "forecast_warning",
            "subject": "Forecast",
            "message": f"Alert: Complaint forecast predicts {int(forecast.get('weekly_forecast', 0))} complaints next week, "
                        f"significantly above historical average.",
            "risk_level": "High",
        })

    return sorted(alerts, key=lambda x: ["Critical", "High", "Medium", "Low"].index(x.get("risk_level", "Low")))


# ══════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR — persist results to DB
# ══════════════════════════════════════════════════════════════════════

def run_all_analytics(db: Session) -> dict:
    """
    Runs all Phase 5 analytics agents and persists results to DB.
    Returns combined dict for immediate API response.
    """
    from app.models import Complaint
    from app.predictive_models import (
        ComplaintTrend, RouteRisk, DriverRisk, BusRisk,
        ComplaintForecast, PreventiveRecommendation, SmartAlert,
    )

    complaints = db.query(Complaint).all()
    now = datetime.now()

    # Compute
    trends = compute_trends(complaints)
    route_risks = compute_route_risks(complaints)
    driver_risks = compute_driver_risks(complaints)
    bus_risks = compute_bus_risks(complaints)
    forecast = compute_forecast(complaints)
    recommendations = generate_recommendations(route_risks, driver_risks, bus_risks, forecast, trends)
    alerts = generate_smart_alerts(complaints, route_risks, driver_risks, bus_risks, forecast)

    # ── Persist trends ─────────────────────────────────────────────────
    db.query(ComplaintTrend).delete()
    for t in trends:
        db.add(ComplaintTrend(
            trend_type=t["trend_type"],
            subject=t["subject"],
            trend_description=t["trend_description"],
            trend_score=t["trend_score"],
            metadata_json=json.dumps(t.get("metadata", {})),
            generated_at=now,
        ))

    # ── Persist route risks ────────────────────────────────────────────
    db.query(RouteRisk).delete()
    for r in route_risks:
        db.add(RouteRisk(
            route_number=r["route"],
            risk_score=r["risk_score"],
            risk_level=r["risk_level"],
            route_risk_score=r["risk_score"],
            route_risk_level=r["risk_level"],
            complaint_count=r["complaint_count"],
            safety_count=r["safety_count"],
            severe_count=r["severe_count"],
            top_categories_json=json.dumps(r.get("top_categories", [])),
            generated_at=now,
        ))

    # ── Persist driver risks ───────────────────────────────────────────
    db.query(DriverRisk).delete()
    for d in driver_risks:
        db.add(DriverRisk(
            driver_identifier=d["driver_identifier"],
            risk_score=d["risk_score"],
            risk_level=d["risk_level"],
            driver_risk_score=d["risk_score"],
            driver_risk_level=d["risk_level"],
            complaint_count=d["complaint_count"],
            misconduct_count=d["misconduct_count"],
            safety_count=d["safety_count"],
            recommendation=d["recommendation"],
            generated_at=now,
        ))

    # ── Persist bus risks ──────────────────────────────────────────────
    db.query(BusRisk).delete()
    for b in bus_risks:
        db.add(BusRisk(
            bus_number=b["bus_number"],
            maintenance_risk=b["maintenance_risk"],
            risk_score=b["risk_score"],
            complaint_count=b["complaint_count"],
            maintenance_count=b["maintenance_count"],
            overcrowding_count=b["overcrowding_count"],
            generated_at=now,
        ))

    # ── Persist forecast (keep latest) ────────────────────────────────
    db.query(ComplaintForecast).delete()
    db.add(ComplaintForecast(
        forecast_type="combined",
        period_label="Next 30 days",
        predicted_count=forecast.get("monthly_forecast", 0),
        confidence=forecast.get("confidence", "Low"),
        trend_direction=forecast.get("trend", "stable"),
        metadata_json=json.dumps(forecast),
        generated_at=now,
    ))

    # ── Persist recommendations ────────────────────────────────────────
    db.query(PreventiveRecommendation).delete()
    for rec in recommendations:
        db.add(PreventiveRecommendation(
            rec_type=rec["rec_type"],
            subject=rec.get("subject", ""),
            recommendation=rec["recommendation"],
            preventive_recommendation=rec["recommendation"],
            priority=rec.get("priority", "Medium"),
            recommendation_priority=rec.get("priority", "Medium"),
            status="Active",
            generated_at=now,
        ))

    # ── Persist alerts ─────────────────────────────────────────────────
    db.query(SmartAlert).delete()
    for a in alerts:
        db.add(SmartAlert(
            alert_type=a["alert_type"],
            subject=a.get("subject", ""),
            message=a["message"],
            risk_level=a.get("risk_level", "Medium"),
            status="unread",
            generated_at=now,
        ))

    db.commit()
    logger.info(f"Phase 5 analytics computed: {len(trends)} trends, {len(route_risks)} route risks, {len(alerts)} alerts")

    return {
        "generated_at": now.isoformat(),
        "trends": trends,
        "route_risks": route_risks,
        "driver_risks": driver_risks,
        "bus_risks": bus_risks,
        "forecast": forecast,
        "recommendations": recommendations,
        "alerts": alerts,
    }
