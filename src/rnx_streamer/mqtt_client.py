import time
import paho.mqtt.client as mqtt_client
import random

import requests

broker="simurg.space"
port = 8778
server_url = "http://127.0.0.1:8000"

def on_message(client, userdata, message):
    data = str(message.payload.decode("utf-8"))
    print(data)

def get_all_stations() -> list:  # type: ignore
    response = requests.get(f"{server_url}/active_streamers/")
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to get all streamers:", response.json())
all_stations = get_all_stations()
count_stations = int(input("count stations: "))
print(all_stations)
client = mqtt_client.Client(
    mqtt_client.CallbackAPIVersion.VERSION2,
    'isu100123'
)
client.username_pw_set("mosquitto", "3SimurgMosquitto")
client.on_message=on_message

print("Connecting to broker",broker)
client.connect(broker, port, 60)
client.loop_start()
print("Subcribing")
i = 0
while i < count_stations:
    client.subscribe(f"streamer/data/{all_stations[i]}")
    i += 1

time.sleep(1800)
client.disconnect()
client.loop_stop()
