"""
Module to stream and parse GNSS TEC data from RINEX files.
"""

import sys
import warnings
import logging
from pathlib import Path
from datetime import datetime, timezone
from gnss_tec import rnx  # type: ignore
from apscheduler.schedulers.blocking import BlockingScheduler  # type: ignore


# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class Streamer:
    def __init__(self, config_file: Path):
        """
        Инициализирует экземпляр класса Streamer.

        Открывает конфигурационный файл, считывает имя файла RINEX,
        инициализирует атрибуты для хранения текущего времени, имени файла,
        открытого файла, экземпляра чтения RINEX и итератора.

        Parameters:
        config_file (Path): Путь к конфигурационному файлу.

        Returns:
        None
        """
        self.cfg_file = config_file
        self._open_file()
        self.iterator = None  # Атрибут для хранения итератора

        self.scheduler = BlockingScheduler()
        self.scheduler.add_job(self._parsing, "cron", second="0,30")

    def _open_file(self):
        """
        Открывает конфигурационный файл, считывает имя файла RINEX,
        инициализирует экземпляр чтения RINEX.

        Parameters:
        None

        Returns:
        None
        """
        with open(self.cfg_file) as f:
            self.file_name = f.readline().strip()
        self.file = open(self.file_name)
        self.reader = rnx(self.file)

    def _parsing(self):
        """
        Обрабатывает данные TEC из текущего файла RINEX каждые 30 секунд.

        Считывает текущее время, инициализирует итератор, если он еще не был инициализирован.
        Обрабатывает данные TEC, соответствующие текущему времени, и переключается на новый файл,
        если текущее время превышает время в текущем файле.

        Parameters:
        None

        Returns:
        None
        """
        self.current_time = datetime.now(timezone.utc).strftime("%H:%M:%S")
        if self.iterator is None:
            self.iterator = iter(self.reader)

        logging.info(f"Время: {self.current_time}")
        try:
            while True:
                tec = next(self.iterator)
                tec_time = tec.timestamp.strftime("%H:%M:%S")
                if tec_time == self.current_time:
                    logging.info(f"{tec.satellite}: {tec.phase_tec} {tec.p_range_tec}")
                elif tec_time > self.current_time:
                    break
                else:
                    continue

        except StopIteration:
            logging.info("Switch to new file...")
            self._switch_to_new_file()
            self.iterator = None

    def _switch_to_new_file(self):
        """
        Переключается на новый файл RINEX, если он доступен.

        Открывает конфигурационный файл, считывает имя нового файла RINEX,
        закрывает текущий файл, инициализирует экземпляр чтения RINEX для нового файла.

        Parameters:
        None

        Returns:
        None
        """
        with open(self.cfg_file, 'r', encoding="utf-8") as f:
            new_file_name = f.readline().strip()

        if new_file_name != self.file_name:
            logging.info(f"Переключение на новый файл: {new_file_name}")
            self.file.close()
            self.file_name = new_file_name
            self._open_file()
        else:
            logging.info("Нет доступных новых файлов для переключения.")

    def get_30seconds_data(self):
        """
        Запускает планировщик для получения и обработки данных каждые 30 секунд.

        Игнорирует предупреждения для отладки, открывает указанный в конфигурационном
        файле RINEX-файл, инициализирует и запускает планировщик. В случае прерывания
        работы (например, с помощью Ctrl+C), закрывает текущий RINEX-файл и
        передает управление. В конце работы закрывает текущий RINEX-файл.

        Parameters:
        None

        Returns:
        None
        """
        # Игнорируем предупреждения для отладки
        warnings.filterwarnings("ignore", category=UserWarning)

        try:
            logging.info(f"Запуск планировщика... {self.file_name}")
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.file.close()
            raise
        finally:
            self.file.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        logging.error("Usage: python3 streamer.py <config_file>")
        sys.exit(1)

    config_file_path = Path(sys.argv[1])
    if not config_file_path.is_file():
        logging.error(f"Config file {config_file_path} does not exist.")
        sys.exit(1)

    streamer = Streamer(config_file_path)
    streamer.get_30seconds_data()
