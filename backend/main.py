from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel

app = FastAPI(title="RailAI Transit Engine")

# Allow requests from your GitHub Pages frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Multi-hop timetable dataset
SCHEDULES = [
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
    # Direct leg: Aurangabad to Mumbai
    {
        "train_number": "12072",
        "train_name": "Janshatabdi Express",
        "from_station": "AWB",
        "to_station": "MMCT",
        "departure_time": "06:00",
        "arrival_time": "12:30",
        "punctuality_score": 95
    }
]

@app.get("/")
def read_root():
    return {"status": "online", "service": "RailAI Engine", "docs_url": "/docs"}

@app.get("/api/v1/routes", response_model=RouteResponse)
def get_routes(
    origin: str = Query(..., description="Origin Station Code"),
    destination: str = Query(..., description="Destination Station Code"),
    max_changes: int = Query(2, ge=0, le=3)
):
    origin = origin.upper().strip()
    destination = destination.upper().strip()

    # 1. Check for a direct route
    direct_legs = [s for s in SCHEDULES if s["from_station"] == origin and s["to_station"] == destination]
    if direct_legs:
        return RouteResponse(
            origin=origin,
            destination=destination,
            total_legs=1,
            reliability_score=direct_legs[0]["punctuality_score"],
            legs=direct_legs
        )

    # 2. Check for a 1-stop transfer (Origin -> Intermediate -> Destination)
    legs_from_origin = [s for s in SCHEDULES if s["from_station"] == origin]
    for leg1 in legs_from_origin:
        intermediate = leg1["to_station"]
        legs_to_dest = [s for s in SCHEDULES if s["from_station"] == intermediate and s["to_station"] == destination]
        
        if legs_to_dest:
            leg2 = legs_to_dest[0]
            avg_punctuality = int((leg1["punctuality_score"] + leg2["punctuality_score"]) / 2)
            return RouteResponse(
                origin=origin,
                destination=destination,
                total_legs=2,
                reliability_score=avg_punctuality,
                legs=[Leg(**leg1), Leg(**leg2)]
            )

    # 3. Fallback when no viable route sequence is found
    return RouteResponse(
        origin=origin,
        destination=destination,
        total_legs=0,
        reliability_score=0,
        legs=[]
    )