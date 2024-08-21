#
# import time
# import paho.mqtt.client as mqtt_client
#
# from logger import setup_logger  # type: ignore
#
# import requests
#
# broker="broker.emqx.io"
# server_url = ""
# logger = setup_logger("MQTT_Client")
#
# # all_active_streamers = requests.post(f"{server_url}/active_streamers/")
#
# def on_message(client, userdata, message):
#     time.sleep(1)
#     data = str(message.payload.decode("utf-8"))
#     logger.info("received message =", data)
#
# client = mqtt_client.Client(
#    mqtt_client.CallbackAPIVersion.VERSION1,
#    'isu10012300'
# )
# client.on_message=on_message
#
# # topics = [f"streamer/data/{all_active_streamers[0]}", f"streamer/data/{all_active_streamers[1]}", ]
#
# logger.info("Connecting to broker",broker)
# client.connect(broker)
# client.loop_start()
# logger.info("Subcribing")
# # for topic in topics:
# #     client.subscribe(topic)
# client.subscribe("streamer/data")
# time.sleep(1800)
# client.disconnect()
# client.loop_stop()

import time
import paho.mqtt.client as mqtt_client
import random

broker="broker.emqx.io"

def on_message(client, userdata, message):
    time.sleep(1)
    data = str(message.payload.decode("utf-8"))
    print(data)


client = mqtt_client.Client(
   mqtt_client.CallbackAPIVersion.VERSION1,
   'isu100123'
)
client.on_message=on_message

print("Connecting to broker",broker)
client.connect(broker)
client.loop_start()
print("Subcribing")
client.subscribe("streamer/data")
time.sleep(1800)
client.disconnect()
client.loop_stop()

