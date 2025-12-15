import os
import sys
import warnings

import pika
import requests
from pathlib import Path
from datetime import datetime, timezone
import paho.mqtt.client as mqtt_client
from gnss_tec import rnx  # type: ignore
from apscheduler.schedulers.blocking import BlockingScheduler  # type: ignore
from logger import setup_logger  # type: ignore
from dotenv import load_dotenv


load_dotenv()


class Streamer:
    def __init__(self, config_file: Path):
        """
        Initialize the Streamer class instance.

        Open the configuration file, read the RINEX file name,
        initialize attributes for storing the current time, file name,
        opened file, RINEX reader instance, and iterator.

        Parameters:
        config_file (Path): Path to the configuration file.
        broker (str): Address of the MQTT broker.
        topic (str): MQTT topic to publish logs.

        Returns:


        None
        """
        self.cfg_file = config_file
        self.server_url = os.getenv("SERVER_URL")
        self.broker = os.getenv("MQTT_BROKER")
        self.port = os.getenv("MQTT_PORT")

        # # self.client = mqtt_client.Client(
        # #     mqtt_client.CallbackAPIVersion.VERSION2,
        # #     f'isu100123000{str(self.cfg_file)[:-1]}'
        # # )
        # self.client = mqtt_client.Client(
        #    mqtt_client.CallbackAPIVersion.VERSION1,
        #    'isu10012300'
        # )
        # self.client.username_pw_set(os.getenv("MQTT_USERNAME"), os.getenv("MQTT_PASSWORD"))
        # # self.client.connect(self.broker, self.port, 60)
        # self.client.connect(self.broker)
        # self.client.loop_start()

        # RabbitMQ
        # Initial
        self.rabbitmq_host = os.getenv("RABBITMQ_HOST", "localhost")
        self.rabbitmq_port = int(os.getenv("RABBITMQ_PORT", 5672))
        self.rabbitmq_user = os.getenv("RABBITMQ_USER", "guest")
        self.rabbitmq_password = os.getenv("RABBITMQ_PASSWORD", "guest")

        # Connecttiion
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.rabbitmq_host,
                port=self.rabbitmq_port,
                credentials=pika.PlainCredentials(self.rabbitmq_user, self.rabbitmq_password)
            )
        )
        self.channel = connection.channel()

        self.iterator = None
        self.reader = None
        self.scheduler = BlockingScheduler()
        self._open_file()

   
    def _open_file(self):
        """
        Open the configuration file, read the RINEX file name,
        initialize the RINEX reader instance.

        Parameters:
        None

        Returns:
        None
        """
        with open(self.cfg_file, "r", encoding="utf-8") as f:
            self.file_path = Path(f.readline().strip())
        self.file_name = self.file_path.name
        self.file = open(self.file_path, "r", encoding="utf-8")
        self.logger = setup_logger(f"Streamer_{self.file_name[:4]}")

        # Create a queue with station name and TTL of 24 hours (in milliseconds)
        self.queue_name = self.file_name[:4]  # Use station name as queue name
        self.channel.queue_declare(
            queue=self.queue_name,
            arguments={"x-message-ttl": 86400000}  # 24 часа в миллисекундах
        )
        self.logger.info(f"Created/connected to queue: {self.queue_name}")

        # try:
        #     self.reader = rnx(self.file)
        # except Exception as e:
        #     self.logger.error(f"{self.file_name[:4]} is of non supported version")
        try:
            self.reader = rnx(self.file)
            if self.reader:
                self.topic = f"streamer/data/{self.file_name[:4]}"
                self._share_activate_streamer()
            self.scheduler.add_job(self._parsing, "cron", second="0,30")
        except ValueError as e:
            if e.args and "Unknown file type" in e.args[0]:
                self.logger.error(f"Unsupported file type for {self.file_name}. Check file content and extension")
            else:
                self.logger.critical(f"Unknown error when attempt to parse {self.file_name} \n {e}")
                raise e
        except Exception as e:
            if e.args and "Unknown RINEX version" in e.args[0]:
                self.logger.error(f"Could not parse file {self.file_name} due to {e.args[0]}. ")
            else:
                self.logger.critical(f"Unknown error when attempt to parse {self.file_name} \n {e}")
                raise e
        #except ValueError as e:
        #    if e.args and "Unknown file type" in e.args[0]:
        #        self.logger.error(f"Unsupported file type for {self.file_name}. Check file content and extension")
        #    else:
        #        self.logger.critical(f"Unknown error when attempt to parse {self.file_name} \n {e}")
        #        raise e

    def _share_activate_streamer(self):
        """
        Send a POST request to the server to activate the streamer.

        This function sends a POST request to the server's 'share_active_streamer/' endpoint
        with the streamer's ID (the first four characters of the RINEX file name) in the request body.
        It then logs the server's response.

        Parameters:
        self (Streamer): The instance of the Streamer class.

        Returns:
        None
        """
        response = requests.post(f"{self.server_url}/share_active_streamer/",
                                 json={"streamer_id": self.file_name[:4]})
        if response.status_code == 200:
            self.logger.info(f"Streamer {self.file_name[:4]} successfully reported it is activate")
        else:
            self.logger.error(f"Streamer failed to report it is activate. See details:{response.json()}")

    def _parsing(self):
        """
        Process TEC data from the current RINEX file every 30 seconds.

        Parameters:
        None

        Returns:
        None
        """

        site_name = self.file_name[:4]

        self.current_time = datetime.now(timezone.utc).strftime("%H:%M:%S")
        if self.iterator is None:
            self.iterator = iter(self.reader)

        message = f"Start send {site_name}. {self.current_time}"
        self.logger.info(message)
        # self.client.publish(self.topic, f"Start send {site_name}. {self.current_time}", qos=2)
        self.channel.basic_publish(
            exchange="",
            routing_key=self.queue_name,
            body=message
        )
        try:
            while True:
                tec = next(self.iterator)
                tec_time = tec.timestamp.strftime("%H:%M:%S")
                if tec_time == self.current_time:
                    message = f"{tec.satellite}: {tec.phase_tec} {tec.p_range_tec}"
                    self.logger.info(message)
                    # self.client.publish(self.topic, site_name + ' ' + message, qos=2)
                    self.channel.basic_publish(
                        exchange="",
                        routing_key=self.queue_name,
                        body=message
                    )

                elif tec_time > self.current_time:
                    break
            message = f"End send {site_name}. {self.current_time}"
            self.logger.info(message)
            # self.client.publish(self.topic, f"End send {site_name}. {self.current_time}", qos=2)
            self.channel.basic_publish(
                exchange="",
                routing_key=self.queue_name,
                body=message
            )

        except StopIteration:
            self.logger.info("Switch to new file...")
            self._switch_to_new_file()
            self.iterator = None

    def _switch_to_new_file(self):
        """
        Switch to a new RINEX file if available.

        Parameters:
        None

        Returns:
        None
        """
        with open(self.cfg_file, "r", encoding="utf-8") as f:
            new_file_path = f.readline().strip()

        if new_file_path != self.file_path:
            self.logger.info(f"Switching to new file: {new_file_path}")
            self.file.close()
            self.file_path = new_file_path
            self._open_file()
        else:
            self.logger.info("No available new files to switch to.")

    def get_30seconds_data(self):
        """
        Start the scheduler to get and process data every 30 seconds.

        Parameters:
        None

        Returns:
        None
        """
        warnings.filterwarnings("ignore", category=UserWarning)

        try:
            self.logger.info(f"Starting streaming {self.file_path}")
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.file.close()
            raise
        finally:
            self.file.close()
            #self.client.disconnect()
            #self.client.loop_stop()


if __name__ == "__main__":
    streamer_logger = setup_logger("Streamer")
    if len(sys.argv) != 2:
        streamer_logger.error("Usage: python3 streamer.py <config_file>")
        sys.exit(1)

    config_file_path = Path(sys.argv[1])

    if not config_file_path.is_file():
        streamer_logger.error(f"Config file {config_file_path} does not exist.")
        sys.exit(1)

    streamer = Streamer(config_file_path)
    streamer.get_30seconds_data()
