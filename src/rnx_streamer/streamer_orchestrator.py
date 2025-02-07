import os
import re
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

import requests
from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
from requests import Response

from launches_modes import LaunchesModes
from logger import setup_logger



load_dotenv()

class StreamerInfo:
    """
    A class to hold information about a streamer.

    Attributes
    ----------
    site_name : str
        The unique identifier for the streamer station.
    cfg_file : Path
        The path to the configuration file for the streamer.

    Methods
    -------
    None
    """

    def __init__(self, site_name: str, cfg_file: Path):
        """
        Initialize a new instance of StreamerInfo.

        Parameters
        ----------
        site_name : str
            The unique identifier for the streamer station.
        cfg_file : Path
            The path to the configuration file for the streamer.

        Returns
        -------
        None
        """
        self.site_name = site_name
        self.cfg_file = cfg_file


class StreamerOrchestrator:
    _instance = None  # Initialization for Singleton

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(StreamerOrchestrator, cls).__new__(
                cls, *args, **kwargs
            )
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):  # Avoid reinitialization
            self.logger = setup_logger("StreamerOrchestrator")
            self.server_url = os.getenv("SERVER_URL")
            self.scheduler = BackgroundScheduler()
            self.scheduler.start()
            self.scheduler.add_job(
                self.check_all_streamer_statuses,
                "interval",
                minutes=1,
                args=[LaunchesModes.subprocess],
            )
            self.storage_path = None
            self.initialized = True
            self.sites = {}
            self.streamer_pids = {}

    def set_storage_path(self, storage_path: Path):
        self.storage_path = storage_path  # type: ignore

    def _get_all_stations(self) -> list:  # type: ignore
        response = requests.get(f"{self.server_url}/all_streamers/")
        if response.status_code == 200:
            return response.json()
        else:
            self.logger.error("Failed to get all streamers:", response.json())

    def add_station(self, site_name: str, file_path: Path):
        if (
            len(site_name) != 4
            or re.search(r"A-Z", site_name)
            or not site_name.isupper()
        ):
            self.logger.error(f"Incorrect station name {site_name}")
        else:
            if site_name in self.sites:
                self.logger.warning(f"Station {site_name} is already added")
            else:
                cfg_file = self._create_cfg_file(site_name, file_path)
                streamer = StreamerInfo(site_name, cfg_file)
                self._register_streamer(site_name, streamer)
                self.sites[site_name] = streamer
                self.logger.info(f"Station {site_name} added successfully. It can be launched know.")

    def _register_streamer(self, site_name: str, streamer: StreamerInfo):
        response = requests.post(f"{self.server_url}/register_streamer/",
                                 json={"streamer_id": site_name, "cfg_file": str(streamer.cfg_file)})
        if response.status_code == 200:
            self.logger.info(f"Station {site_name} registered successfully at {self.server_url}")
        else:
            self.logger.error(f"Failed to register streamer: {response.json()}")

    def _create_cfg_file(self, site_name: str, file_path: Path):
        cfg_dir = self.storage_path / "data/cfg"
        if not cfg_dir.exists():
            cfg_dir.mkdir()
        cfg_file = cfg_dir / f"cfg-{site_name}.txt"
        with open(cfg_file, "w", encoding="utf-8") as f:
            f.write(str(file_path))
        return cfg_file

    def _read_cfg_file(self, site_name: str) -> str:
        with open(self.sites[site_name].cfg_file, "r", encoding="utf-8") as f:
            rinex_path = f.readline()
        return rinex_path

    def update_cfg_file(self, site_name: str, file_path: Path):
        self.logger.info(f"Attempt to change cfg_file for {site_name}")
        with open(self.sites[site_name].cfg_file, "w", encoding="utf-8") as f:
            self.logger.info(f"Writing new rinex path {file_path} for {site_name}")
            f.write(str(file_path))

    def check_streamer_status(self, site_name: str, mode: LaunchesModes):
        self.logger.debug(f"Checking streamer status for {site_name} in mode {mode}")
        if mode == LaunchesModes.subprocess:
            try:
                # Assuming the streamer is launched as `streamer.py {site_name}`
                cmd = f'pgrep -fl "streamer.py {site_name}"'
                self.logger.debug(f"Executing command: {cmd}")
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, check=True
                )
                self.logger.debug(
                    f"Command result: returncode={result.returncode}, stdout={result.stdout}, stderr={result.stderr}"
                )
                if result.returncode == 0:
                    self.logger.debug(
                        f"Streamer for {site_name} keep working. PID: {result.stdout.strip()}"
                    )
                else:
                    self.logger.warning(f"Streamer for {site_name} is not working.")
            except subprocess.CalledProcessError as e:
                self.logger.error(
                    f"Error checking streamer status for {site_name}: {e}"
                )
        elif mode == LaunchesModes.service:
            try:
                service_name = f"streamer_{site_name}.service"
                cmd = f"systemctl is-active {service_name}"
                self.logger.debug(f"Executing command: {cmd}")
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, check=True
                )
                self.logger.debug(
                    f"Command result: returncode={result.returncode}, stdout={result.stdout}, stderr={result.stderr}"
                )
                if result.returncode == 0:
                    self.logger.info(f"Streamer service for {site_name} is active.")
                else:
                    self.logger.info(f"Streamer service for {site_name} is not active.")
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Error checking service status for {site_name}: {e}")
        elif mode == LaunchesModes.docker:
            # Add logic to check docker container status
            self.logger.info(
                f"Checking docker status for {site_name} is not implemented yet."
            )
        else:
            self.logger.error("Invalid mode")

    def check_all_streamer_statuses(self, mode: LaunchesModes):
        if self.sites:
            for site_name in self.sites:
                self.check_streamer_status(site_name, mode)

    def launch_streamer(self, site_name: str, mode: LaunchesModes):
        if mode == LaunchesModes.subprocess:
            try:
                self.logger.info(f"Try to launch streamer for {site_name} in mode {mode}")
                streamer_process = subprocess.Popen(
                    ["python3", "streamer.py", Path(self.sites[site_name].cfg_file)],
                )
                pid = streamer_process.pid
                self.streamer_pids[site_name] = pid
                self.logger.info(f"Streamer launched for {site_name} using subprocess with PID {pid}.")
            except subprocess.CalledProcessError as e:
                self.logger.error(f"{site_name} is of non supported version")
        elif mode == LaunchesModes.service:
            self.logger.info(f"Streamer launched for {site_name} using service mode.")
        elif mode == LaunchesModes.docker:
            self.logger.info(f"Streamer launched for {site_name} using docker mode.")
        else:
            self.logger.error("Invalid mode")

    def launch_all_streamers(self, mode: LaunchesModes):
        """
        Launch all streamers for a given mode.

        Parameters:
        mode (LaunchesModes): The mode in which the streamers should be launched.

        Returns:
        None
        """
        number_of_streamers = 0
        for site_name in self.sites:
            try:
                self.launch_streamer(site_name, mode)
                number_of_streamers += 1
            except Exception as e:
                info.critical(f"Unknown error while streamer activating for {site_name} \n {e}")
        self.logger.info(f"Launched {number_of_streamers} streamers. Done launching")
