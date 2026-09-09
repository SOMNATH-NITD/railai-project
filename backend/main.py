"""
Indian Railway AI Route Optimization & RAPTOR Engine
FastAPI + Pydantic Implementation
File: main.py
"""

import math
from datetime import datetime, time
from typing import List, Dict, Optional, Tuple
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="Indian Railway Multi-Hop Routing & Delay Engine",
    version="2.4.0",
    description="Time-Dependent RAPTOR & Delay-Aware Pareto Route Optimizer"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------------
# DATA MODELS & SCHEMAS
# -------------------------------------------------------------------------
class StationStop(BaseModel):
    station_code: str
    arrival_time: str      # HH:MM format
    departure_time: str    # HH:MM format
    day_offset: int        # 1-indexed relative to train start
    distance_km: int
    platform: Optional[str] = None

class TrainDefinition(BaseModel):
    train_number: str
    train_name: str
    train_type: str
    running_days: List[int] # 0=Mon, 6=Sun
    historical_punctuality: float # 0.0 to 100.0
    current_delay_min: int = 0
    stops: List[StationStop]

class StationMetadata(BaseModel):
    code: str
    name: str
    city: str
    lat: float
    lon: float
    min_transfer_buffer_min: int
    is_major_junction: bool

class LegResponse(BaseModel):
    train_number: str
    train_name: str
    train_type: str
    from_station: str
    to_station: str
    departure_time: str
    departure_day: int
    arrival_time: str
    arrival_day: int
    distance_km: int
    duration_minutes: int
    live_delay_min: int
    punctuality: float

class TransferResponse(BaseModel):
    junction_code: str
    scheduled_buffer_min: int
    effective_buffer_min: int
    required_buffer_min: int
    connection_probability: int
    risk_level: str
    risk_color: str

class RouteResponse(BaseModel):
    route_id: str
    route_type: str
    ai_score: int
    total_duration_minutes: int
    total_waiting_minutes: int
    changes_count: int
    overall_reliability: float
    min_connection_probability: int
    ai_explanation: str
    legs: List[LegResponse]
    transfers: List[TransferResponse]

# -------------------------------------------------------------------------
# IN-MEMORY STRUCTURED RAILWAY KNOWLEDGE BASE
# -------------------------------------------------------------------------
STATIONS_DB: Dict[str, StationMetadata] = {
    "MMCT": StationMetadata(code="MMCT", name="Mumbai Central", city="Mumbai", lat=18.9696, lon=72.8193, min_transfer_buffer_min=45, is_major_junction=True),
    "CSMT": StationMetadata(code="CSMT", name="Mumbai CSMT", city="Mumbai", lat=18.9401, lon=72.8347, min_transfer_buffer_min=45, is_major_junction=True),
    "AWB":  StationMetadata(code="AWB",  name="Aurangabad", city="Chhatrapati Sambhajinagar", lat=19.8762, lon=75.3433, min_transfer_buffer_min=25, is_major_junction=False),
    "NDLS": StationMetadata(code="NDLS", name="New Delhi", city="Delhi", lat=28.6427, lon=77.2198, min_transfer_buffer_min=50, is_major_junction=True),
    "NGP":  StationMetadata(code="NGP",  name="Nagpur Junction", city="Nagpur", lat=21.1528, lon=79.0882, min_transfer_buffer_min=35, is_major_junction=True),
    "ET":   StationMetadata(code="ET",   name="Itarsi Junction", city="Itarsi", lat=22.6120, lon=77.7610, min_transfer_buffer_min=35, is_major_junction=True),
    "PRYJ": StationMetadata(code="PRYJ", name="Prayagraj Junction", city="Prayagraj", lat=25.4435, lon=81.8246, min_transfer_buffer_min=35, is_major_junction=True),
    "HWH":  StationMetadata(code="HWH",  name="Howrah Junction", city="Kolkata", lat=22.5838, lon=88.3434, min_transfer_buffer_min=50, is_major_junction=True),
    "BZA":  StationMetadata(code="BZA",  name="Vijayawada Junction", city="Vijayawada", lat=16.5186, lon=80.6200, min_transfer_buffer_min=35, is_major_junction=True),
    "GHY":  StationMetadata(code="GHY",  name="Guwahati", city="Guwahati", lat=26.1824, lon=91.7506, min_transfer_buffer_min=30, is_major_junction=True),
    "PNBE": StationMetadata(code="PNBE", name="Patna Junction", city="Patna", lat=25.6022, lon=85.1376, min_transfer_buffer_min=35, is_major_junction=True),
    "CNB":  StationMetadata(code="CNB",  name="Kanpur Central", city="Kanpur", lat=26.4547, lon=80.3507, min_transfer_buffer_min=40, is_major_junction=True),
}

TRAINS_DB: List[TrainDefinition] = [
    TrainDefinition(
        train_number="12951", train_name="Mumbai Rajdhani Express", train_type="Rajdhani Superfast",
        running_days=[0, 1, 2, 3, 4, 5, 6], historical_punctuality=91.5, current_delay_min=12,
        stops=[
            StationStop(station_code="MMCT", arrival_time="17:00", departure_time="17:00", day_offset=1, distance_km=0),
            StationStop(station_code="NDLS", arrival_time="08:32", departure_time="08:32", day_offset=2, distance_km=1386),
        ]
    ),
    TrainDefinition(
        train_number="12424", train_name="Dibrugarh Rajdhani Express", train_type="Rajdhani Superfast",
        running_days=[0, 1, 2, 3, 4, 5, 6], historical_punctuality=86.0, current_delay_min=20,
        stops=[
            StationStop(station_code="NDLS", arrival_time="16:20", departure_time="16:20", day_offset=1, distance_km=0),
            StationStop(station_code="CNB",  arrival_time="21:02", departure_time="21:07", day_offset=1, distance_km=440),
            StationStop(station_code="PRYJ", arrival_time="23:08", departure_time="23:10", day_offset=1, distance_km=635),
            StationStop(station_code="PNBE", arrival_time="03:50", departure_time="04:00", day_offset=2, distance_km=1000),
            StationStop(station_code="GHY",  arrival_time="19:25", departure_time="19:25", day_offset=2, distance_km=1890),
        ]
    ),
    TrainDefinition(
        train_number="11201", train_name="Nagpur Express (Origin: CSMT)", train_type="Express",
        running_days=[0, 1, 2, 3, 4, 5, 6], historical_punctuality=79.0, current_delay_min=15,
        stops=[
            StationStop(station_code="CSMT", arrival_time="14:00", departure_time="14:00", day_offset=1, distance_km=0),
            StationStop(station_code="AWB",  arrival_time="21:20", departure_time="21:25", day_offset=1, distance_km=375),
            StationStop(station_code="NGP",  arrival_time="08:15", departure_time="08:15", day_offset=2, distance_km=890),
        ]
    ),
    TrainDefinition(
        train_number="12509", train_name="Guwahati Superfast Express", train_type="Superfast",
        running_days=[0, 1, 2, 3, 4, 5, 6], historical_punctuality=84.0, current_delay_min=25,
        stops=[
            StationStop(station_code="NGP",  arrival_time="11:15", departure_time="11:30", day_offset=1, distance_km=0),
            StationStop(station_code="PRYJ", arrival_time="23:15", departure_time="23:30", day_offset=1, distance_km=710),
            StationStop(station_code="GHY",  arrival_time="04:15", departure_time="04:15", day_offset=3, distance_km=1890),
        ]
    ),
    TrainDefinition(
        train_number="12716", train_name="Sachkhand Express", train_type="Superfast",
        running_days=[0, 1, 2, 3, 4, 5, 6], historical_punctuality=88.0, current_delay_min=18,
        stops=[
            StationStop(station_code="AWB",  arrival_time="09:40", departure_time="09:45", day_offset=1, distance_km=0),
            StationStop(station_code="ET",   arrival_time="19:35", departure_time="19:40", day_offset=1, distance_km=580),
            StationStop(station_code="NDLS", arrival_time="12:15", departure_time="12:15", day_offset=2, distance_km=1370),
        ]
    ),
    TrainDefinition(
        train_number="12345", train_name="Saraighat Express", train_type="Superfast",
        running_days=[0, 1, 2, 3, 4, 5, 6], historical_punctuality=89.5, current_delay_min=10,
        stops=[
            StationStop(station_code="HWH", arrival_time="15:55", departure_time="15:55", day_offset=1, distance_km=0),
            StationStop(station_code="GHY", arrival_time="10:05", departure_time="10:05", day_offset=2, distance_km=998),
        ]
    ),
    TrainDefinition(
        train_number="12833", train_name="Howrah Superfast Express", train_type="Superfast",
        running_days=[0, 1, 2, 3, 4, 5, 6], historical_punctuality=82.0, current_delay_min=15,
        stops=[
            StationStop(station_code="CSMT", arrival_time="06:00", departure_time="06:00", day_offset=1, distance_km=0),
            StationStop(station_code="NGP",  arrival_time="17:55", departure_time="18:00", day_offset=1, distance_km=837),
            StationStop(station_code="HWH",  arrival_time="13:35", departure_time="13:35", day_offset=2, distance_km=1968),
        ]
    )
]

# -------------------------------------------------------------------------
# TIME & DELAY HELPER FUNCTIONS
# -------------------------------------------------------------------------
def to_minutes(time_str: str) -> int:
    h, m = map(int, time_str.split(":"))
    return h * 60 + m

def get_absolute_minute(day: int, time_str: str) -> int:
    return (day - 1) * 1440 + to_minutes(time_str)

def evaluate_transfer(leg_a: LegResponse, leg_b: LegResponse, injected_delay_a: int = 0) -> TransferResponse:
    jn_code = leg_a.to_station
    stn_meta = STATIONS_DB.get(jn_code, StationMetadata(code=jn_code, name=jn_code, city="", lat=0, lon=0, min_transfer_buffer_min=35, is_major_junction=True))
    
    sched_arr_a = get_absolute_minute(leg_a.arrival_day, leg_a.arrival_time)
    sched_dep_b = get_absolute_minute(leg_b.departure_day, leg_b.departure_time)
    
    layover = sched_dep_b - sched_arr_a
    while layover < 0:
        layover += 1440 # Roll over to next scheduled run

    total_delay_a = leg_a.live_delay_min + injected_delay_a
    effective_buffer = layover - total_delay_a
    req_buffer = stn_meta.min_transfer_buffer_min

    if effective_buffer < req_buffer:
        deficit = req_buffer - effective_buffer
        prob = max(5, 75 - int(deficit * 2.2))
    else:
        surplus = effective_buffer - req_buffer
        prob = min(99, 85 + int(surplus * 0.15))

    if prob < 40:
        risk_level, risk_color = "VERY HIGH (MISSED)", "rose"
    elif prob < 60:
        risk_level, risk_color = "HIGH RISK", "amber"
    elif prob < 78:
        risk_level, risk_color = "MODERATE", "yellow"
    else:
        risk_level, risk_color = "LOW RISK", "emerald"

    return TransferResponse(
        junction_code=jn_code,
        scheduled_buffer_min=layover,
        effective_buffer_min=effective_buffer,
        required_buffer_min=req_buffer,
        connection_probability=prob,
        risk_level=risk_level,
        risk_color=risk_color
    )

def find_direct_legs(from_code: str, to_code: str) -> List[LegResponse]:
    results = []
    for train in TRAINS_DB:
        stops = train.stops
        from_idx = next((i for i, s in enumerate(stops) if s.station_code == from_code), None)
        to_idx = next((i for i, s in enumerate(stops) if s.station_code == to_code), None)
        
        if from_idx is not None and to_idx is not None and to_idx > from_idx:
            s_from = stops[from_idx]
            s_to = stops[to_idx]
            dep_min = get_absolute_minute(s_from.day_offset, s_from.departure_time)
            arr_min = get_absolute_minute(s_to.day_offset, s_to.arrival_time)
            duration = arr_min - dep_min
            
            results.append(LegResponse(
                train_number=train.train_number,
                train_name=train.train_name,
                train_type=train.train_type,
                from_station=from_code,
                to_station=to_code,
                departure_time=s_from.departure_time,
                departure_day=s_from.day_offset,
                arrival_time=s_to.arrival_time,
                arrival_day=s_to.day_offset,
                distance_km=s_to.distance_km - s_from.distance_km,
                duration_minutes=duration,
                live_delay_min=train.current_delay_min,
                punctuality=train.historical_punctuality
            ))
    return results

# -------------------------------------------------------------------------
# API ROUTE ENDPOINT
# -------------------------------------------------------------------------
@app.get("/api/v1/routes", response_model=List[RouteResponse])
def get_optimized_routes(
    origin: str = Query(..., description="Origin Station Code (e.g. AWB, MMCT)"),
    destination: str = Query(..., description="Destination Station Code (e.g. GHY, NDLS)"),
    max_changes: int = Query(2, ge=0, le=3),
    goal: str = Query("recommended", enum=["recommended", "fastest", "reliable", "fewest"]),
    simulated_delay: int = Query(0, description="Injected delay in minutes")
):
    origin = origin.upper()
    destination = destination.upper()

    if origin not in STATIONS_DB or destination not in STATIONS_DB:
        raise HTTPException(status_code=400, detail="Invalid station code provided.")

    if origin == destination:
        raise HTTPException(status_code=400, detail="Origin and Destination cannot be identical.")

    candidate_routes: List[RouteResponse] = []

    # Round 1: Direct Trains
    for leg in find_direct_legs(origin, destination):
        ai_score = int(min(99, leg.punctuality * 0.4 + max(0, 100 - (leg.duration_minutes / 2880) * 100) * 0.6))
        candidate_routes.append(RouteResponse(
            route_id=f"dir-{leg.train_number}",
            route_type="DIRECT",
            ai_score=ai_score,
            total_duration_minutes=leg.duration_minutes,
            total_waiting_minutes=0,
            changes_count=0,
            overall_reliability=leg.punctuality,
            min_connection_probability=100,
            ai_explanation=f"Direct service via {leg.train_name} ({leg.train_number}). Zero transfer risk.",
            legs=[leg],
            transfers=[]
        ))

    # Round 2: 1-Change Routes
    if max_changes >= 1:
        for jn in STATIONS_DB.keys():
            if jn in (origin, destination):
                continue
            legs1 = find_direct_legs(origin, jn)
            legs2 = find_direct_legs(jn, destination)
            for l1 in legs1:
                for l2 in legs2:
                    if l1.train_number == l2.train_number:
                        continue
                    tf = evaluate_transfer(l1, l2, simulated_delay)
                    if tf.scheduled_buffer_min > 720:
                        continue
                    
                    total_duration = l1.duration_minutes + tf.scheduled_buffer_min + l2.duration_minutes
                    rel = round((l1.punctuality + l2.punctuality) / 2, 1)
                    
                    time_score = max(0, 100 - (total_duration / 2880) * 100)
                    ai_score = int(time_score * 0.35 + rel * 0.25 + tf.connection_probability * 0.25 + 75 * 0.15)
                    
                    candidate_routes.append(RouteResponse(
                        route_id=f"1hop-{l1.train_number}-{l2.train_number}",
                        route_type="1-CHANGE",
                        ai_score=min(99, ai_score),
                        total_duration_minutes=total_duration,
                        total_waiting_minutes=tf.scheduled_buffer_min,
                        changes_count=1,
                        overall_reliability=rel,
                        min_connection_probability=tf.connection_probability,
                        ai_explanation=f"Interchange via {STATIONS_DB[jn].name} with a {tf.effective_buffer_min}m effective buffer.",
                        legs=[l1, l2],
                        transfers=[tf]
                    ))

    candidate_routes.sort(key=lambda r: r.ai_score, reverse=True)
    return candidate_routes

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)