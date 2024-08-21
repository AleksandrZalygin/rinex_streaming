import subprocess
import sys
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path

import requests

from protocol import Protocol
from logger import setup_logger


class DataSource(ABC):
    """
    Abstract base class for data sources.
    """

    def __init__(
        self,
        server_url : str,
        protocol: Protocol,
        host: str,
        port: int,
        url_template: str,
        storage_path: Path,
    ):
        """
        Initialize the DataSource object.

        Args:
        protocol (Protocol): The protocol to use for data transfer.
        host (str): The host of the data source.
        port (int): The port of the data source.
        url_template (str): The URL template for data retrieval.
        storage_path (Path): The path where downloaded data will be stored.
        """
        self.server_url = server_url
        self.protocol = protocol
        self.session = requests.Session()
        self.host = host
        self.port = port
        self.url_template = url_template
        self.storage_path = storage_path
        self.logger = setup_logger(f"{self.__class__.__name__}")

    @abstractmethod
    def check_online(self) -> bool:
        """
        Check if the data source is online.

        Returns:
        bool: True if the data source is online, False otherwise.
        """

    @abstractmethod
    def check_available(self, date) -> bool:
        """
        Check if data is available for a specific date.

        Args:
        date (str): The date to check for data availability.

        Returns:
        bool: True if data is available for the specified date, False otherwise.
        """

    @abstractmethod
    def download(self, date) -> Path:
        """
        Download data for a specific date.

        Args:
        date (str): The date to download data for.

        Returns:
        Path: The path where the downloaded data is stored.
        """

    @abstractmethod
    def check_download(self, file_path: Path) -> bool:
        """
        Check if the download was successful.

        Args:
        file_path (Path): The path of the downloaded file.

        Returns:
        bool: True if the download was successful, False otherwise.
        """

    @abstractmethod
    def unpack(self, file_path: Path):
        """
        Unpack downloaded data.

        Args:
        file_path (Path): The path of the downloaded file.
        """

    @abstractmethod
    def get_sites_data(self) -> list:
        """
        Get the paths of downloaded data.

        Returns:
        list: A list of paths of downloaded data.
        """


class SimurgSource(DataSource):
    """
    SimurgSource is a concrete implementation of DataSource for accessing data from the Simurg data source.
    It provides methods for checking online status, checking data availability, downloading data, checking download success,
    unpacking downloaded data, and getting paths of downloaded data.
    """

    def check_online(self) -> bool:
        """
        Check if the Simurg data source is online.

        Returns:
        bool: True if the data source is online, False otherwise.
        """
        try:
            # Check the availability of the specific resource
            url = f"{self.protocol.value}://{self.host}:{self.port}/docs"
            response = self.session.head(url)
            self.logger.info(f"Checking online status: {response.status_code == 200}")
            return response.status_code == 200
        except requests.RequestException:
            self.logger.error("Failed to check online status")
            return False

    def check_available(self, date) -> bool:
        """
        Check if data is available for a specific date.

        Args:
        date (str): The date to check for data availability.

        Returns:
        bool: True if data is available for the specified date, False otherwise.
        """
        url = f"https://api.simurg.space/datafiles/map_files?date={date}"
        response = self.session.get(url, timeout=10)
        return response.status_code == 200

    def download(self, date: str):
        """
        Download data for a specific date.

        Args:
        date (str): The date to download data for.

        Returns:
        Path: The path where the downloaded data is stored.
        """
        file_name = f"{date}.zip"
        data_path = self.storage_path / "data"
        if not data_path.exists():
            data_path.mkdir()
        file_path = data_path / file_name
        if file_path.exists():
            self.logger.info(f"{file_path} already exists. Skipping download.")
            return file_path

        with open(file_path, "wb") as f:
            self.logger.info(f"Downloading {file_path}")
            response = requests.get(
                f"{self.protocol.value}://{self.host}:{self.port}/datafiles/map_files?date={date}",
                stream=True,
            )
            total_length = response.headers.get("content-length")
            if total_length is None:  # no content length header
                f.write(response.content)
            else:
                dl = 0
                total_length = int(total_length)  # type: ignore
                for data in response.iter_content(chunk_size=4096):
                    dl += len(data)
                    f.write(data)
                    done = int(50 * dl / total_length)  # type: ignore
                    sys.stdout.write(f"\r[{'=' * done}{' ' * (50 - done)}]")
                    sys.stdout.flush()
        self.logger.info(f"Download completed: {file_path}")
        return file_path

    def check_download(self, file_path: Path) -> bool:
        """
        Check if the download was successful.

        Args:
        file_path (Path): The path of the downloaded file.

        Returns:
        bool: True if the download was successful, False otherwise.
        """
        return file_path.exists() and file_path.stat().st_size > 0

    def unpack(self, file_path: Path):
        """
        Unpack downloaded data.

        Args:
        file_path (Path): The path of the downloaded file.
        """

        extract_path = self._unzip_zip_file(file_path)
        # Iterate through all files in the extracted directory
        for item in extract_path.iterdir():
            if item.suffix == ".gz":
                self._unzip_gz_file(item)
            elif item.suffix == ".Z":
                self._uncompress_z_file(item)

        for item in extract_path.iterdir():
            self.logger.info(f"Processing compact RINEX candidate: {item}")
            if item.suffix == ".crx":
                self._convert_crx_to_rnx(item)

    def _unzip_zip_file(self, file_path: Path):
        # Unpacking the .zip archive
        try:
            # Create a directory for unpacking
            extract_path = file_path.with_suffix("")
            extract_path.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(file_path, "r") as zip_ref:
                zip_ref.extractall(extract_path)
            return extract_path
        except Exception as e:
            self.logger.error(f"Error during zip extraction: {e}")
            return

    def _unzip_gz_file(self, file_path: Path):
        try:
            output_path = file_path.with_suffix("")
            subprocess.run(["gunzip", str(file_path)], check=True)
            self.logger.info(f"Unzipped file: {output_path}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error during .gz file unpacking: {e}")
        except FileNotFoundError:
            self.logger.error(
                "The `gunzip` utility is not available. Please install it using `sudo apt-get install gzip`."
            )

    def _uncompress_z_file(self, file_path: Path):
        try:
            output_path = file_path.with_suffix("")
            subprocess.run(["uncompress", str(file_path)], check=True)
            self.logger.info(f"Uncompressed file: {output_path}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error during .Z file unpacking: {e}")
        except FileNotFoundError:
            self.logger.error("The `uncompress` utility is not available.")

    def _convert_crx_to_rnx(self, file_path: Path):
        try:
            output_path = file_path.with_suffix("")
            subprocess.run(["CRX2RNX", str(file_path)], check=True)
            self.logger.info(f"Converted file: {output_path}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error converting file: {e}")
        except FileNotFoundError:
            self.logger.error("The `CRX2RNX` utility is not available.")

    def get_download_sites_data(self, path: Path):
        requests.post(f"{self.server_url}/upload_stations/",
                      [str(file[:4]) for file in path])
