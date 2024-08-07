import subprocess
import sys
import zipfile
from pathlib import Path
from abc import ABC, abstractmethod
import requests

from protocol import Protocol


class DataSource(ABC):
    def __init__(
        self,
        protocol: Protocol,
        host: str,
        port: int,
        url_template: str,
        storage_path: Path,
    ):
        self.protocol = protocol
        self.session = requests.Session()
        self.host = host
        self.port = port
        self.url_template = url_template
        self.storage_path = storage_path

    @abstractmethod
    def check_online(self) -> bool:
        """
        Проверка, работает ли сервер.
        """

    @abstractmethod
    def check_available(self, date) -> bool:
        """
        Проверка, существуют ли данные о конкретном дне.
        """

    @abstractmethod
    def download(self, date) -> Path:
        """
        Скачивание данных по дате.
        """

    @abstractmethod
    def check_download(self, file_path: Path) -> bool:
        """
        Проверка на успешность скачивания.
        """

    @abstractmethod
    def unpack(self, file_path: Path):
        """
        Метод распаковки скачанных данных.
        """

    @abstractmethod
    def get_sites_data(self) -> list:
        """
        Вернет список полученных путей.
        """


class SimurgSource(DataSource):
    def check_online(self) -> bool:
        try:
            # Проверяем доступность конкретного ресурса
            url = f"{self.protocol.value}://{self.host}:{self.port}/docs"
            response = self.session.head(url)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def check_available(self, date) -> bool:
        url = f"https://api.simurg.space/datafiles/map_files?date={date}"
        response = self.session.get(url, timeout=10)
        return response.status_code == 200

    def download(self, date: str):
        file_name = f"{date}.zip"
        with open("data/" + file_name, "wb") as f:
            print("Downloading %s" % file_name)
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
                    sys.stdout.write("\r[%s%s]" % ("=" * done, " " * (50 - done)))
                    sys.stdout.flush()
        return self.storage_path / file_name

    def check_download(self, file_path: Path) -> bool:
        return file_path.exists() and file_path.stat().st_size > 0

    def unpack(self, file_path: Path):
        extract_path = self._unzip_zip_file(file_path)
        # Итерируем по всем файлам в распакованной директории
        for item in extract_path.iterdir():
            if item.suffix == ".gz":
                self._unzip_gz_file(item)
            elif item.suffix == ".Z":
                self._uncompress_z_file(item)

        for item in extract_path.iterdir():
            if item.suffix == ".crx":
                self._convert_crx_to_rnx(item)

    @staticmethod
    def _unzip_zip_file(file_path: Path):
        # Распаковка архива .zip
        try:
            # Создаем директорию для распаковки
            extract_path = file_path.with_suffix("")
            extract_path.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(file_path, "r") as zip_ref:
                zip_ref.extractall(extract_path)
            return extract_path
        except Exception as e:
            print(f"Error during zip extraction: {e}")
            return

    @staticmethod
    def _unzip_gz_file(file_path: Path):
        try:
            output_path = file_path.with_suffix("")
            subprocess.run(["gunzip", str(file_path)], check=True)
            print(f"Unzipped file: {output_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error during .gz file unpacking: {e}")
        except FileNotFoundError:
            print(
                "The `gunzip` utility is not available. Please install it using `sudo apt-get install gzip`."
            )

    @staticmethod
    def _uncompress_z_file(file_path: Path):
        try:
            output_path = file_path.with_suffix("")
            subprocess.run(["uncompress", str(file_path)], check=True)
            print(f"Uncompressed file: {output_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error during .gz file unpacking: {e}")
        except FileNotFoundError:
            print(
                "The `gunzip` utility is not available. Please install it using `sudo apt-get install gzip`."
            )

    @staticmethod
    def _convert_crx_to_rnx(file_path: Path):
        try:
            output_path = file_path.with_suffix("")
            subprocess.run(["CRX2RNX", str(file_path)], check=True)
            print(f"Convert file: {output_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error during .gz file unpacking: {e}")
        except FileNotFoundError:
            print(
                "The `gunzip` utility is not available. Please install it using `sudo apt-get install gzip`."
            )

    def get_sites_data(self) -> list:
        return [str(file) for file in self.storage_path.glob("*.zip")]
