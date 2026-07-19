# pyrefly: ignore [missing-import]
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from datetime import datetime
from src.db.session import Base

# Reference/static tables
class City(Base):
    __tablename__ = "cities"
    city_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    state = Column(String)
    timezone = Column(String)

class Ward(Base):
    __tablename__ = "wards"
    ward_id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, ForeignKey("cities.city_id"))
    name = Column(String)
    geometry = Column(Text) # GeoJSON string for MVP
    population = Column(Integer)
    boundary_geojson = Column(Text)

class Station(Base):
    __tablename__ = "stations"
    station_id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.ward_id"))
    name = Column(String)
    lat = Column(Float)
    lon = Column(Float)
    source = Column(String) # 'CPCB' or 'OpenAQ'

class Inspector(Base):
    __tablename__ = "inspectors"
    inspector_id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, ForeignKey("cities.city_id"))
    name = Column(String)
    base_lat = Column(Float)
    base_lon = Column(Float)
    daily_capacity = Column(Integer)

class EmissionSite(Base):
    __tablename__ = "emission_sites"
    site_id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.ward_id"))
    type = Column(String) # 'industrial' or 'construction'
    lat = Column(Float)
    lon = Column(Float)
    permit_ref = Column(String)
    registered_date = Column(DateTime)

# Raw ingested data
class RawAQIReading(Base):
    __tablename__ = "raw_aqi_readings"
    reading_id = Column(Integer, primary_key=True, index=True)
    station_id = Column(Integer, ForeignKey("stations.station_id"))
    timestamp = Column(DateTime, index=True)
    pm25 = Column(Float)
    pm10 = Column(Float)
    no2 = Column(Float)
    so2 = Column(Float)
    co = Column(Float)
    source = Column(String)

class RawWeather(Base):
    __tablename__ = "raw_weather"
    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, ForeignKey("cities.city_id"))
    timestamp = Column(DateTime, index=True)
    wind_speed = Column(Float)
    wind_dir = Column(Float)
    humidity = Column(Float)
    precipitation = Column(Float)
    temp = Column(Float)

class RawFireHotspot(Base):
    __tablename__ = "raw_fire_hotspots"
    hotspot_id = Column(Integer, primary_key=True, index=True)
    lat = Column(Float)
    lon = Column(Float)
    timestamp = Column(DateTime, index=True)
    frp = Column(Float)
    source = Column(String)

class RawLanduse(Base):
    __tablename__ = "raw_landuse"
    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.ward_id"))
    category = Column(String)
    pct_coverage = Column(Float)
    source = Column(String)

# Agent Output Models
class AttributionResult(Base):
    __tablename__ = "attribution_results"
    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.ward_id"))
    timestamp = Column(DateTime, index=True)
    pct_vehicular = Column(Float)
    pct_construction = Column(Float)
    pct_industrial = Column(Float)
    pct_burning = Column(Float)
    pct_dust = Column(Float)
    confidence_score = Column(Float)
    signals_available_json = Column(Text)

class ForecastGrid(Base):
    __tablename__ = "forecast_grid"
    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, ForeignKey("cities.city_id"))
    grid_cell_id = Column(String)
    forecast_made_at = Column(DateTime, index=True)
    horizon_hours = Column(Integer)
    aqi_predicted = Column(Float)
    uncertainty_band = Column(Float)
    physics_component = Column(Float)
    ml_component = Column(Float)

class ForecastAccuracyLog(Base):
    __tablename__ = "forecast_accuracy_log"
    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, ForeignKey("cities.city_id"))
    horizon_hours = Column(Integer)
    date = Column(DateTime)
    rmse_model = Column(Float)
    rmse_persistence = Column(Float)

class EnforcementWorklist(Base):
    __tablename__ = "enforcement_worklist"
    worklist_id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.ward_id"))
    site_id = Column(Integer, ForeignKey("emission_sites.site_id"))
    date = Column(DateTime, index=True)
    priority_score = Column(Float)
    impact_score = Column(Float)
    feasibility_score = Column(Float)
    assigned_inspector_id = Column(Integer, ForeignKey("inspectors.inspector_id"))
    justification_text = Column(Text)
    evidence_json = Column(Text)
    status = Column(String) # 'pending', 'reviewed', 'actioned'

class Intervention(Base):
    __tablename__ = "interventions"
    intervention_id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, ForeignKey("cities.city_id"))
    ward_id = Column(Integer, ForeignKey("wards.ward_id"))
    policy_name = Column(String)
    start_date = Column(DateTime)
    logged_by = Column(String)

class InterventionEffect(Base):
    __tablename__ = "intervention_effects"
    id = Column(Integer, primary_key=True, index=True)
    intervention_id = Column(Integer, ForeignKey("interventions.intervention_id"))
    effect_size = Column(Float)
    confidence_interval_low = Column(Float)
    confidence_interval_high = Column(Float)
    transferability_note = Column(Text)
    target_city_id = Column(Integer, ForeignKey("cities.city_id"))

class Advisory(Base):
    __tablename__ = "advisories"
    advisory_id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.ward_id"))
    tier = Column(String)
    channel = Column(String) # 'push', 'ivr', 'display'
    language = Column(String)
    text = Column(Text)
    generated_at = Column(DateTime, index=True)

class Anomaly(Base):
    __tablename__ = "anomalies"
    anomaly_id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.ward_id"))
    timestamp = Column(DateTime, index=True)
    z_score = Column(Float)
    investigation_note = Column(Text)
    evidence_json = Column(Text)
    confidence_statement = Column(Text)
    human_reviewed = Column(Boolean, default=False)

class QueryLog(Base):
    __tablename__ = "query_log"
    query_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String)
    question = Column(Text)
    city_id = Column(Integer, ForeignKey("cities.city_id"))
    final_answer = Column(Text)
    tools_called_json = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_log"
    log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String)
    action = Column(String)
    target_table = Column(String)
    target_id = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)
