import re
import subprocess
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
from launches_modes import LaunchesModes

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class StreamerInfo:
    def __init__(self, site_name: str, cfg_file: str):
        self.site_name = site_name
        self.cfg_file = cfg_file


class StreamerOrchestrator:
    _instance = None  # Инициализация для Singleton

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(StreamerOrchestrator, cls).__new__(
                cls, *args, **kwargs
            )
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):  # Avoid reinitialization
            self.sites = {}
            self.scheduler = BackgroundScheduler()
            self.scheduler.start()
            self.scheduler.add_job(
                self.check_all_streamer_statuses,
                "interval",
                minutes=1,
                args=[LaunchesModes.subprocess],
            )

            self.initialized = True

    def add_station(self, site_name: str, file_path: str):
        if (
            len(site_name) != 4
            or re.search(r"A-Z", site_name)
            or not site_name.isupper()
        ):
            logging.error("Некорректное имя станции")
        else:
            if site_name in self.sites:
                logging.warning("Станция уже добавлена")
            else:
                cfg_file = self._create_cfg_file(site_name, file_path)
                streamer = StreamerInfo(site_name, cfg_file)
                self.sites.update({site_name: streamer})
                logging.info(f"Станция {site_name} успешно добавлена")

    @staticmethod
    def _create_cfg_file(site_name: str, file_path: str):
        cfg_file = f"data/cfg/cfg-{site_name}.txt"
        with open(cfg_file, "w", encoding="utf-8") as f:
            f.write(file_path)
        return cfg_file

    def _read_cfg_file(self, site_name: str) -> str:
        with open(self.sites[site_name].cfg_file, "r", encoding="utf-8") as f:
            rinex_path = f.readline()
        return rinex_path

    def update_cfg_file(self, site_name: str, file_path: str):
        with open(self.sites[site_name].cfg_file, "w", encoding="utf-8") as f:
            f.write(file_path)

    @staticmethod
    def check_streamer_status(site_name: str, mode: LaunchesModes):
        logging.debug(f"Проверка статуса стримера для {site_name} в режиме {mode}")
        if mode == LaunchesModes.subprocess:
            try:
                # Предполагаем, что стример запускается как `streamer.py {site_name}`
                cmd = f'pgrep -fl "streamer.py {site_name}"'
                logging.debug(f"Выполнение команды: {cmd}")
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                logging.debug(
                    f"Результат команды: returncode={result.returncode}, stdout={result.stdout}, stderr={result.stderr}"
                )
                if result.returncode == 0:
                    logging.info(
                        f"Стример для {site_name} запущен. PID: {result.stdout.strip()}"
                    )
                else:
                    logging.info(f"Стример для {site_name} не запущен.")
            except subprocess.CalledProcessError as e:
                logging.error(
                    f"Ошибка при проверке статуса стримера для {site_name}: {e}"
                )
        elif mode == LaunchesModes.service:
            try:
                service_name = f"streamer_{site_name}.service"
                cmd = f"systemctl is-active {service_name}"
                logging.debug(f"Выполнение команды: {cmd}")
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                logging.debug(
                    f"Результат команды: returncode={result.returncode}, stdout={result.stdout}, stderr={result.stderr}"
                )
                if result.returncode == 0:
                    logging.info(f"Сервис стримера для {site_name} активен.")
                else:
                    logging.info(f"Сервис стримера для {site_name} не активен.")
            except subprocess.CalledProcessError as e:
                logging.error(
                    f"Ошибка при проверке статуса сервиса для {site_name}: {e}"
                )
        elif mode == LaunchesModes.docker:
            # Добавьте логику для проверки статуса docker контейнера
            logging.info(
                f"Проверка статуса docker для {site_name} пока не реализована."
            )
        else:
            logging.error("Некорректный режим")

    def check_all_streamer_statuses(self, mode: LaunchesModes):
        if self.sites:
            for site_name in self.sites:
                self.check_streamer_status(site_name, mode)

    def launch_streamer(self, site_name: str, mode: LaunchesModes):
        if mode == LaunchesModes.subprocess:
            try:
                subprocess.run(
                    ["python3", "streamer.py", Path(self.sites[site_name].cfg_file)],
                    check=True,
                )
                logging.info(
                    f"Стример запущен для {site_name} с использованием subprocess."
                )
            except subprocess.CalledProcessError as e:
                logging.error(f"Ошибка при запуске стримера для {site_name}: {e}")
        elif mode == LaunchesModes.service:
            # Добавьте логику для запуска стримера как сервис
            logging.info(
                f"Стример запущен для {site_name} с использованием режима service."
            )
        elif mode == LaunchesModes.docker:
            # Добавьте логику для запуска стримера как docker контейнер
            logging.info(
                f"Стример запущен для {site_name} с использованием режима docker."
            )
        else:
            logging.error("Некорректный режим")

    def launch_all_streamers(self, mode: LaunchesModes):
        with ThreadPoolExecutor(max_workers=len(self.sites)) as executor:
            futures = {
                executor.submit(self.launch_streamer, site_name, mode): site_name
                for site_name in self.sites
            }
            for future in as_completed(futures):
                site_name = futures[future]
                try:
                    future.result()
                    logging.info(f"Стример успешно запущен для {site_name}")
                except Exception as e:
                    logging.error(f"Ошибка при запуске стримера для {site_name}: {e}")
