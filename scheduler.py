import os
import sys

from datetime import datetime, timedelta
from pathlib import Path
from apscheduler.schedulers.blocking import BlockingScheduler  # type: ignore

from loader import SimurgSource
from protocol import Protocol
from launches_modes import LaunchesModes
from streamer_orchestrator import StreamerOrchestrator


def download_files(date: str):
    # Задаем параметры для создания экземпляра ExampleDataSource
    protocol = Protocol.HTTPS
    host = "api.simurg.space"
    port = 443
    url_template = f"/datafiles/map_files?date={date}"

    # Создаем экземпляр ExampleDataSource
    data_source = SimurgSource(protocol, host, port, url_template, storage_path)
    file_path = data_source.download(date)

    # Проверяем успешность скачивания
    if data_source.check_download(file_path):
        print(f"File downloaded successfully: {file_path}")
        # Распаковываем скачанный файл
        data_source.unpack(file_path)
    else:
        print("Download failed.")

    print("Загружаем файлы...")


def orchestrate_first_launch(orchestrator, directory_path="data/2024-01-01"):
    for file in os.listdir(directory_path):
        if file.endswith(".rnx"):
            orchestrator.add_station(file[0:4], os.path.abspath(f"{directory_path}/{file}"))


def update_cfg_files(orchestrator, directory_path):
    for site_name in orchestrator.sites:
        for file in os.listdir(directory_path):
            if file.endswith(".rnx") and file[0:4] == site_name:
                orchestrator.update_cfg_file(site_name, os.path.abspath(f"{directory_path}/{file}"))


def scheduled_everyday_task(orchestrator):
    current_date = "2024-01-01"
    download_files(current_date)
    update_cfg_files(orchestrator, current_date)
    # Обновляем дату на следующий день
    current_date += timedelta(days=1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scheduler.py <storage_path>")
        sys.exit(1)

    storage_path = Path(sys.argv[1])

    current_date = "2024-01-01"
    download_files(current_date)

    orchestrator = StreamerOrchestrator()
    orchestrate_first_launch(orchestrator, "data/" + current_date)
    orchestrator.launch_all_streamers(LaunchesModes.subprocess)

    # Создаем экземпляр планировщика
    scheduler = BlockingScheduler()

    # Планируем выполнение функции download_files каждый день в определенное время
    scheduler.add_job(scheduled_everyday_task, "cron", hour=23, minute=0, args=[orchestrator, storage_path])
    # scheduler.add_job(scheduled_everyday_task, 'interval', minutes=8)

    try:
        # Запускаем планировщик
        print("Запуск планировщика...")
        scheduler.start()

    except (KeyboardInterrupt, SystemExit):
        pass
