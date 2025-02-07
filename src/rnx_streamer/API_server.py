from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict


app = FastAPI()

registered_streamers = {}
active_streamers = {}
stations = []

class StreamerInfo(BaseModel):
    streamer_id: str
    cfg_file: str

class StreamerID(BaseModel):
    streamer_id: str


# StreamerOrchestrator._register_streamer()
@app.post("/register_streamer/")
def register_streamer(streamer: StreamerInfo):
    registered_streamers[streamer.streamer_id] = {streamer.cfg_file}
    return {"message": "Streamer registered successfully", "streamer": registered_streamers[streamer.streamer_id]}


# Streamer._share_activate_streamer()
@app.post("/share_active_streamer/")
def share_active_streamer(streamer: StreamerID):
    if streamer.streamer_id in active_streamers:
        raise HTTPException(status_code=400, detail="Streamer already active")
    active_streamers[streamer.streamer_id] = {
        "id": streamer.streamer_id,
        "is_active": False,
    }
    return {"message": "Streamer activated successfully", "streamer": active_streamers[streamer.streamer_id]}

# client
@app.get("/active_streamers/", response_model=List[str])
def get_active_streamers():
    return list(active_streamers.keys())

# StreamerOrchestrator._get_all_stations()
@app.get("/all_streamers/", response_model=List[str])
def get_all_streamers():
    return list(registered_streamers.keys())

# loader
@app.post("/upload_station/")
def upload_station(upload_file: StreamerID):
    stations.append(upload_file)
    return {"message": "Station uploaded successfully", "station": upload_file}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.rnx_streamer.API_server:app", host="0.0.0.0", port=8000, reload=True)
