from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel

app = FastAPI(title="RailAI Transit Engine")

# Enable Cross-Origin Resource Sharing (CORS) for GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# DATA MODELS & SCHEMAS
# -------------------------------------------------------------
class Leg(BaseModel):
    train_number: str
    train_name: str
    from_station: str
    to_station: str
    departure_time: str
    arrival_time: str
    punctuality_score: int

class RouteResponse(BaseModel):
    origin: str
    destination: str
    total_legs: int
    reliability_score: int
    legs: List[Leg]

# -------------------------------------------------------------
# COMMON TYPO & ALIAS RESOLVER
# -------------------------------------------------------------
STATION_ALIASES = {
    "MMTC": "MMCT",      # Common typo for Mumbai Central
    "MUMBAI": "MMCT",
    "BOMBAY": "MMCT",
    "AURANGABAD": "AWB",
    "NAGPUR": "NGP",
    "GUWAHATI": "GHY",
    "DELHI": "NDLS",
    "NEW DELHI": "NDLS",
    "ITARSI": "ET",
}

# -------------------------------------------------------------
# IN-MEMORY SCHEDULE DATABASE
# -------------------------------------------------------------
SCHEDULES = [
    # Direct Leg: Aurangabad to Mumbai Central
    {
        "train_number": "12072",
        "train_name": "Janshatabdi Express",
        "from_station": "AWB",
        "to_station": "MMCT",
        "departure_time": "06:00",
        "arrival_time": "12:30",
        "punctuality_score": 95
    },
    # Leg 1: Aurangabad to Nagpur
    {
        "train_number": "11401",
        "train_name": "Nandigram Express",
        "from_station": "AWB",
        "to_station": "NGP",
        "departure_time": "21:30",
        "arrival_time": "06:15",
        "punctuality_score": 88
    },
    # Leg 2: Nagpur to Guwahati
    {
        "train_number": "12522",
        "train_name": "Rapti Sagar Express",
        "from_station": "NGP",
        "to_station": "GHY",
        "departure_time": "09:45",
        "arrival_time": "23:30",
        "punctuality_score": 84
    },
    # Leg 1 Alternative: Aurangabad to Itarsi
    {
        "train_number": "12715",
        "train_name": "Sachkhand Express",
        "from_station": "AWB",
        "to_station": "ET",
        "departure_time": "13:30",
        "arrival_time": "21:10",
        "punctuality_score": 90
    },
    # Leg 2 Alternative: Itarsi to New Delhi
    {
        "train_number": "12625",
        "train_name": "Kerala Express",
        "from_station": "ET",
        "to_station": "NDLS",
        "departure_time": "23:00",
        "arrival_time": "13:40",
        "punctuality_score": 87
    }
]

# -------------------------------------------------------------
# API ROUTE HANDLERS
# -------------------------------------------------------------
@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "RailAI RAPTOR Optimization Engine",
        "documentation": "/docs"
    }

@app.get("/api/v1/routes", response_model=RouteResponse)
def get_routes(
    origin: str = Query(..., description="Origin Station Code, e.g. AWB"),
    destination: str = Query(..., description="Destination Station Code, e.g. MMCT or GHY"),
    max_changes: int = Query(2, ge=0, le=3)
):
    # Normalize inputs
    origin = origin.upper().strip()
    destination = destination.upper().strip()

    # Resolve typos or common station name variants
    origin = STATION_ALIASES.get(origin, origin)
    destination = STATION_ALIASES.get(destination, destination)

    # 1. Direct Route Check
    direct_matches = [
        s for s in SCHEDULES 
        if s["from_station"] == origin and s["to_station"] == destination
    ]
    if direct_matches:
        leg_data = direct_matches[0]
        return RouteResponse(
            origin=origin,
            destination=destination,
            total_legs=1,
            reliability_score=leg_data["punctuality_score"],
            legs=[Leg(**leg_data)]
        )

    # If user selected max 0 changes and no direct train, return empty
    if max_changes == 0:
        return RouteResponse(
            origin=origin,
            destination=destination,
            total_legs=0,
            reliability_score=0,
            legs=[]
        )

    # 2. Single-Hop Transfer Check (Origin -> Intermediate Junction -> Destination)
    departing_legs = [s for s in SCHEDULES if s["from_station"] == origin]
    
    for leg1 in departing_legs:
        transfer_junction = leg1["to_station"]
        connecting_legs = [
            s for s in SCHEDULES 
            if s["from_station"] == transfer_junction and s["to_station"] == destination
        ]
        
        if connecting_legs:
            leg2 = connecting_legs[0]
            avg_score = int((leg1["punctuality_score"] + leg2["punctuality_score"]) / 2)
            return RouteResponse(
                origin=origin,
                destination=destination,
                total_legs=2,
                reliability_score=avg_score,
                legs=[Leg(**leg1), Leg(**leg2)]
            )

    # 3. Fallback when no viable route path is found
    return RouteResponse(
        origin=origin,
        destination=destination,
        total_legs=0,
        reliability_score=0,
        legs=[]
    )