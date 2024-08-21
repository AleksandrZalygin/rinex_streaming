import sys
import warnings
import requests
from pathlib import Path
from datetime import datetime, timezone
import paho.mqtt.client as mqtt_client
from gnss_tec import rnx  # type: ignore
from apscheduler.schedulers.blocking import BlockingScheduler  # type: ignore
from logger import setup_logger  # type: ignore


class Streamer:
    def __init__(self, config_file: Path, server_url: str, broker: str):
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
        self.server_url = server_url
        self.broker = broker
        self.client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION1, 'isu1001230000')
        print(self.client.connect(self.broker))
        self.client.loop_start()

        self._open_file()
        self.iterator = None

        self.scheduler = BlockingScheduler()
        self.scheduler.add_job(self._parsing, "cron", second="0,30")

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
        self.reader = rnx(self.file)
        self.logger = setup_logger(f"Streamer_{self.file_name[:4]}")
        self.topic = f"streamer/data/{self.file_name[:4]}"
        # self._share_activate_streamer()

    def _share_activate_streamer(self):
        response = requests.post(f"{self.server_url}/share_active_streamer/",
                                 json={"streamer_id": self.file_name[:4]})
        if response.status_code == 200:
            self.logger.info("Streamer registered successfully")
        else:
            self.logger.error("Failed to register streamer:", response.json())

    def _parsing(self):
        """
        Process TEC data from the current RINEX file every 30 seconds.

        Parameters:
        None

        Returns:
        None
        """
        self.current_time = datetime.now(timezone.utc).strftime("%H:%M:%S")
        if self.iterator is None:
            self.iterator = iter(self.reader)

        self.logger.info(f"Time now: {self.current_time}")
        try:
            while True:
                tec = next(self.iterator)
                tec_time = tec.timestamp.strftime("%H:%M:%S")
                if tec_time == self.current_time:
                    message = f"{tec.satellite}: {tec.phase_tec} {tec.p_range_tec}"
                    self.logger.info(message)
                    # self.client.publish(self.topic, message)
                    self.client.publish("streamer/data", message)
                elif tec_time > self.current_time:
                    break

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
            self.logger.info(f"Starting scheduler... {self.file_path}")
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.file.close()
            raise
        finally:
            self.file.close()
            self.client.disconnect()
            self.client.loop_stop()


if __name__ == "__main__":
    streamer_logger = setup_logger("Streamer")
    if len(sys.argv) != 4:
        streamer_logger.error("Usage: python3 streamer.py <config_file> <broker> <topic>")
        sys.exit(1)

    config_file_path = Path(sys.argv[1])
    server_url = sys.argv[2]
    broker = sys.argv[3]

    if not config_file_path.is_file():
        streamer_logger.error(f"Config file {config_file_path} does not exist.")
        sys.exit(1)

    streamer = Streamer(config_file_path, server_url, broker)
    streamer.get_30seconds_data()
