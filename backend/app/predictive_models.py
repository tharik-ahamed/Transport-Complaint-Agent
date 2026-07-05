"""
Phase 5 Predictive Models
=========================
New SQLAlchemy table definitions for predictive analytics.
These are SEPARATE tables from the Phase 1-4 complaints table.
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from sqlalchemy.sql import func
from app.database import Base


class ComplaintTrend(Base):
    """Persisted trend analysis results."""
    __tablename__ = "complaint_trends"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trend_type = Column(String(50), nullable=False)          # route | bus | time | location | category | driver
    subject = Column(String(200), nullable=True)             # Route 47A, Bus TN47AB, Weekend, etc.
    trend_description = Column(Text, nullable=False)
    trend_score = Column(Float, default=0.0, nullable=False)  # 0–1 normalised score
    metadata_json = Column(Text, nullable=True)              # additional data as JSON string
    generated_at = Column(DateTime, server_default=func.now(), nullable=False)


class RouteRisk(Base):
    """Computed route risk profile."""
    __tablename__ = "route_risks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    route_number = Column(String(20), nullable=False, index=True)
    risk_score = Column(Float, default=0.0, nullable=False)    # 0–1
    risk_level = Column(String(20), nullable=True)             # Low | Medium | High | Critical
    complaint_count = Column(Integer, default=0)
    safety_count = Column(Integer, default=0)
    severe_count = Column(Integer, default=0)
    top_categories_json = Column(Text, nullable=True)          # JSON list
    route_risk_score = Column(Float, default=0.0)              # alias for schema compat
    route_risk_level = Column(String(20), nullable=True)       # alias
    metadata_json = Column(Text, nullable=True)
    generated_at = Column(DateTime, server_default=func.now(), nullable=False)


class DriverRisk(Base):
    """Driver / operator risk profile (keyed by bus or extracted driver ID)."""
    __tablename__ = "driver_risks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    driver_identifier = Column(String(100), nullable=False, index=True)  # bus_number used as proxy
    risk_score = Column(Float, default=0.0, nullable=False)
    risk_level = Column(String(20), nullable=True)             # Low | Medium | High | Critical
    driver_risk_score = Column(Float, default=0.0)             # alias for schema compat
    driver_risk_level = Column(String(20), nullable=True)      # alias
    complaint_count = Column(Integer, default=0)
    misconduct_count = Column(Integer, default=0)
    safety_count = Column(Integer, default=0)
    recommendation = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    generated_at = Column(DateTime, server_default=func.now(), nullable=False)


class BusRisk(Base):
    """Bus health / maintenance risk profile."""
    __tablename__ = "bus_risks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bus_number = Column(String(20), nullable=False, index=True)
    maintenance_risk = Column(String(20), nullable=True)       # Low | Medium | High | Critical
    risk_score = Column(Float, default=0.0, nullable=False)
    complaint_count = Column(Integer, default=0)
    maintenance_count = Column(Integer, default=0)
    overcrowding_count = Column(Integer, default=0)
    metadata_json = Column(Text, nullable=True)
    generated_at = Column(DateTime, server_default=func.now(), nullable=False)


class ComplaintForecast(Base):
    """Forecast record."""
    __tablename__ = "complaint_forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    forecast_type = Column(String(30), nullable=False)    # daily | weekly | monthly
    period_label = Column(String(50), nullable=True)
    predicted_count = Column(Float, default=0.0)
    confidence = Column(String(20), nullable=True)        # Low | Medium | High
    trend_direction = Column(String(20), nullable=True)   # increasing | stable | decreasing
    metadata_json = Column(Text, nullable=True)           # includes history data
    generated_at = Column(DateTime, server_default=func.now(), nullable=False)


class PreventiveRecommendation(Base):
    """Preventive action recommendation."""
    __tablename__ = "preventive_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rec_type = Column(String(30), nullable=False)          # route | driver | bus | system
    subject = Column(String(200), nullable=True)
    recommendation = Column(Text, nullable=False)
    preventive_recommendation = Column(Text, nullable=True) # alias for schema compat
    priority = Column(String(20), nullable=True)           # Critical | High | Medium | Low
    recommendation_priority = Column(String(20), nullable=True)  # alias
    status = Column(String(20), default="Active")
    metadata_json = Column(Text, nullable=True)
    generated_at = Column(DateTime, server_default=func.now(), nullable=False)


class SmartAlert(Base):
    """Smart threshold-based alert."""
    __tablename__ = "smart_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_type = Column(String(50), nullable=False)        # route_spike | driver_risk | safety | volume
    subject = Column(String(200), nullable=True)
    message = Column(Text, nullable=False)
    risk_level = Column(String(20), nullable=True)
    status = Column(String(20), default="unread")
    metadata_json = Column(Text, nullable=True)
    generated_at = Column(DateTime, server_default=func.now(), nullable=False)
