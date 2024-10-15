import re
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
from requests import Response

from launches_modes import LaunchesModes
from logger import setup_logger


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
            # self.server_url = "http://10.0.6.78:22580"
            self.server_url = "http://127.0.0.1:8000"
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

    def set_storage_path(self, storage_path: Path):
        """
        Set the storage path for the streamer orchestrator.

        Parameters:
        storage_path (Path): The path where the configuration files will be stored.

        Returns:
        None
        """
        self.storage_path = storage_path  # type: ignore

    def _get_all_stations(self) -> list:  # type: ignore
        """
        Fetch all streamer stations from the server.

        This method sends a GET request to the server to retrieve a list of all streamer stations.
        If the request is successful (status code 200), it returns the response data as a list.
        If the request fails (status code other than 200), it logs an error message and returns an empty list.

        Parameters:
        None

        Returns:
        list: A list of streamer station names. If the request fails, returns an empty list.
        """
        response = requests.get(f"{self.server_url}/all_streamers/")
        if response.status_code == 200:
            return response.json()
        else:
            self.logger.error("Failed to get all streamers:", response.json())

    def add_station(self, site_name: str, file_path: Path):
        """
        Add a new station to the orchestrator.

        Parameters:
        site_name (str): The unique identifier for the streamer station.
        file_path (str): The path to the RINEX file for the streamer.

        Returns:
        None
        """
        if (
            len(site_name) != 4
            or re.search(r"A-Z", site_name)
            or not site_name.isupper()
        ):
            self.logger.error("Incorrect station name")
        else:
            if site_name in self.sites:
                self.logger.warning("Station already added")
            else:
                cfg_file = self._create_cfg_file(site_name, file_path)
                streamer = StreamerInfo(site_name, cfg_file)
                self._register_streamer(site_name, streamer)
                self.sites[site_name] = streamer
                self.logger.info("Station %s added successfully", site_name)

    def _register_streamer(self, site_name: str, streamer: StreamerInfo):
        """
        Register a streamer with the server using the provided site name and streamer information.

        Parameters:
        site_name (str): The unique identifier for the streamer station.
        streamer (StreamerInfo): An instance of StreamerInfo containing the configuration file path.

        Returns:
        None

        This method sends a POST request to the server's registration endpoint with the site name and
        configuration file path. If the registration is successful (status code 200), it logs an info message.
        If the registration fails (status code other than 200), it logs an error message along with the server's response.
        """
        response = requests.post(f"{self.server_url}/register_streamer/",
                                 json={"streamer_id": site_name, "cfg_file": str(streamer.cfg_file)})
        if response.status_code == 200:
            self.logger.info("Streamer registered successfully")
        else:
            self.logger.error("Failed to register streamer:", response.json())

    def _create_cfg_file(self, site_name: str, file_path: Path):
        """
        Create a configuration file for a streamer station.

        Parameters:
        site_name (str): The unique identifier for the streamer station.
        file_path (str): The path to the RINEX file for the streamer.

        Returns:
        str: The path to the created configuration file.
        """
        cfg_dir = self.storage_path / "data/cfg"
        if not cfg_dir.exists():
            cfg_dir.mkdir()
        cfg_file = cfg_dir / f"cfg-{site_name}.txt"
        with open(cfg_file, "w", encoding="utf-8") as f:
            f.write(str(file_path))
        return cfg_file

    def _read_cfg_file(self, site_name: str) -> str:
        """
        Read the configuration file for a streamer station.

        Parameters:
        site_name (str): The unique identifier for the streamer station.

        Returns:
        str: The content of the configuration file.
        """
        with open(self.sites[site_name].cfg_file, "r", encoding="utf-8") as f:
            rinex_path = f.readline()
        return rinex_path

    def update_cfg_file(self, site_name: str, file_path: Path):
        """
        Update the configuration file for a streamer station.

        Parameters:
        site_name (str): The unique identifier for the streamer station.
        file_path (str): The new path to the RINEX file for the streamer.

        Returns:
        None
        """
        with open(self.sites[site_name].cfg_file, "w", encoding="utf-8") as f:
            f.write(str(file_path))

    def check_streamer_status(self, site_name: str, mode: LaunchesModes):
        """
        Check the status of a streamer for a given site and mode.

        Parameters:
        site_name (str): The unique identifier for the streamer station.
        mode (LaunchesModes): The mode in which the streamer should be launched.

        Returns:
        None
        """
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
        """
        Check the status of all streamers for a given mode.

        Parameters:
        mode (LaunchesModes): The mode in which the streamers should be launched.

        Returns:
        None
        """
        if self.sites:
            for site_name in self.sites:
                self.check_streamer_status(site_name, mode)

    def launch_streamer(self, site_name: str, mode: LaunchesModes):
        """
        Launch a streamer for a given site and mode.

        Parameters:
        site_name (str): The unique identifier for the streamer station.
        mode (LaunchesModes): The mode in which the streamer should be launched.

        Returns:
        None
        """
        if mode == LaunchesModes.subprocess:
            try:
                subprocess.run(
                    ["python3", "streamer.py", Path(self.sites[site_name].cfg_file), self.server_url, "simurg.space"],
                    check=True,
                )
                self.logger.info(f"Streamer launched for {site_name} using subprocess.")
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
        with ThreadPoolExecutor(max_workers=len(self.sites)) as executor:
            futures = {
                executor.submit(self.launch_streamer, site_name, mode): site_name
                for site_name in self.sites
            }
            for future in as_completed(futures):
                site_name = futures[future]
                try:
                    future.result()
                    self.logger.info(f"Streamer successfully launched for {site_name}")
                except Exception as exc:
                    self.logger.error(
                        f"Error launching streamer for {site_name}: {exc}"
                    )
