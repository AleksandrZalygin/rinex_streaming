from fastapi import FastAPI, HTTPException, Depends
from typing import List, Dict


app = FastAPI()

registered_streamers = {}
active_streamers = {}  # type: ignore
stations = []


@app.post("/register_streamer/")
def register_streamer(streamer_id: int, streamer):
    registered_streamers[streamer_id] = {streamer}
    return {"message": "Streamer registered successfully", "streamer": registered_streamers[streamer_id]}


@app.post("/share_active_streamer/")
def share_active_streamer(streamer_id: int):
    if streamer_id in active_streamers:
        raise HTTPException(status_code=400, detail="Streamer already active")
    active_streamers[streamer_id] = {
        "id": streamer_id,
        "is_active": False,
    }
    return {"message": "Streamer activated successfully", "streamer": active_streamers[streamer_id]}

@app.get("/active_streamers/", response_model=List[Dict])
def get_active_streamers():
    return list(active_streamers.values())

@app.get("/all_streamers/", response_model=List[Dict])
def get_all_streamers():
    return list(registered_streamers.values())

@app.post("/upload_stations/")
def upload_stations(stations_data: List[Dict]):
    global stations
    stations.extend(stations_data)
    return {"message": "Stations uploaded successfully", "stations": stations}
