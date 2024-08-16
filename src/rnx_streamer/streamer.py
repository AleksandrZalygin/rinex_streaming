"""
Module to stream and parse GNSS TEC data from RINEX files.
"""

import sys
import warnings
from pathlib import Path
from datetime import datetime, timezone
from gnss_tec import rnx  # type: ignore
from apscheduler.schedulers.blocking import BlockingScheduler  # type: ignore
from logger import setup_logger


class Streamer:
    def __init__(self, config_file: Path):
        """
        Initialize the Streamer class instance.

        Open the configuration file, read the RINEX file name,
        initialize attributes for storing the current time, file name,
        opened file, RINEX reader instance, and iterator.

        Parameters:
        config_file (Path): Path to the configuration file.

        Returns:
        None
        """
        self.cfg_file = config_file
        self._open_file()
        self.iterator = None  # Attribute for storing the iterator

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

    def _parsing(self):
        """
        Process TEC data from the current RINEX file every 30 seconds.

        Read the current time, initialize the iterator if it hasn't been initialized yet.
        Process TEC data corresponding to the current time, and switch to a new file
        if the current time exceeds the time in the current file.

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
                    self.logger.info(
                        f"{tec.satellite}: {tec.phase_tec} {tec.p_range_tec}"
                    )
                elif tec_time > self.current_time:
                    break
                else:
                    continue

        except StopIteration:
            self.logger.info("Switch to new file...")
            self._switch_to_new_file()
            self.iterator = None

    def _switch_to_new_file(self):
        """
        Switch to a new RINEX file if available.

        Open the configuration file, read the name of the new RINEX file,
        close the current file, and initialize the RINEX reader instance for the new file.

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

        Ignore debug warnings, open the specified RINEX file in the configuration file,
        initialize and start the scheduler. In case of interruption (e.g., using Ctrl+C),
        close the current RINEX file and pass control. At the end of the work, close the current RINEX file.

        Parameters:
        None

        Returns:
        None
        """
        # Ignore debug warnings
        warnings.filterwarnings("ignore", category=UserWarning)

        try:
            self.logger.info(f"Starting scheduler... {self.file_path}")
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.file.close()
            raise
        finally:
            self.file.close()


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
