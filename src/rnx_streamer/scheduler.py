import os
import sys

from datetime import datetime, timedelta
from pathlib import Path

import psutil  # type: ignore
from apscheduler.schedulers.blocking import BlockingScheduler  # type: ignore
from loader import SimurgSource  # type: ignore
from protocol import Protocol  # type: ignore
from launches_modes import LaunchesModes  # type: ignore
from streamer_orchestrator import StreamerOrchestrator  # type: ignore
from logger import setup_logger  # type: ignore

# Set up logger
logger = setup_logger("Scheduler")


def get_date(days: int) -> str:
    """
    Get the date in the format 'YYYY-MM-DD' for a specified number of days ago.

    Args:
    days (int): The number of days ago.

    Returns:
    str: The date in the format 'YYYY-MM-DD'.
    """
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")


def download_files(date: str) -> None:
    """
    Download files from a specified date using the SimurgSource class.

    Args:
    date (str): The date in the format 'YYYY-MM-DD'.
    """
    # Set up parameters for creating an instance of SimurgSource
    #server_url = "http://10.0.6.78:22580"
    server_url = "http://127.0.0.1:8000"
    protocol = Protocol.HTTPS
    host = "api.simurg.space"
    port = 443
    url_template = f"/datafiles/map_files?date={date}"

    # Create an instance of SimurgSource
    data_source = SimurgSource(server_url, protocol, host, port, url_template, storage_path)
    file_path = data_source.download(date)

    # Check the download success
    if data_source.check_download(file_path):
        logger.info(f"File downloaded successfully: {file_path}. Try to unpack...")
        # Unpack the downloaded file
        data_source.unpack(file_path)
    else:
        logger.error("Download failed.")


def orchestrate_first_launch(
    orchestrator: StreamerOrchestrator, directory_path: Path, available_RAM: float
) -> None:
    """
    Orchestrate the first launch of streamers by adding stations from a specified directory.
    The function iterates through files in the given directory, checks if the file is an RINEX file,
    and adds the corresponding station to the StreamerOrchestrator instance if the memory usage is below 75%.
    If the memory usage exceeds 75%, the function logs a message and stops the process.

    Args:
    orchestrator (StreamerOrchestrator): The StreamerOrchestrator instance to add stations to.
    directory_path (Path): The path to the directory containing the files.

    Returns:
    None: The function does not return any value.
    """
    logger.info(f"Check files in {directory_path}")
    for file in os.listdir(directory_path):
        logger.info(f"Candidate for streaming {file}")
        if file.endswith(".rnx"):
            if psutil.virtual_memory().used < psutil.virtual_memory().total * (available_RAM / 100):
                orchestrator.add_station(
                    file[0:4], os.path.abspath(f"{directory_path}/{file}")
                )
            else:
                logger.critical(
                    f"Not adding station {file[0:4]} as it exceeds the memory limit."
                )
                logger.info("Memory usage is low. Stopping the process.")
                return None


def update_cfg_files(orchestrator: StreamerOrchestrator, directory_path: Path) -> None:
    """
    Update configuration files for the streamers by adding stations from a specified directory.

    Args:
    orchestrator (StreamerOrchestrator): The StreamerOrchestrator instance.
    directory_path (Path): The path to the directory containing the files.
    """
    if not orchestrator.sites:
       logger.error(f"Orchestrator is not awear of any streamers. Register stations first.")
       return
    logger.info(f"Known streamers are: {orchestrator.sites}")
    for site_name in orchestrator.sites:
        logger.info(f"Changing config to {site_name}")
        for file in os.listdir(directory_path):
            if file.endswith(".rnx") and file[0:4] == site_name:
                fpath = directory_path / file
                logger.info(f"Changing config to streamer {site_name}, with {fpath}")
                orchestrator.update_cfg_file(
                    site_name, os.path.abspath(str(fpath))
                )


def scheduled_everyday_task(
    days_to_subtract: int, 
    orchestrator: StreamerOrchestrator, 
    storage_path: Path,
    available_RAM: float
) -> None:
    """
    Perform a scheduled task every day, which includes downloading files and updating configuration files.

    Args:
    days_to_subtract (int): Time shift in past where data are taken.
    orchestrator (StreamerOrchestrator): The StreamerOrchestrator instance.
    directory_path (Path): The path to the directory containing the files.
    """
    ping_file = Path(storage_path / ("task_started_" + str(datetime.now())))
    ping_file.touch()
    logger.info("Started new task...")
    date = get_date(days_to_subtract - 1) # -1 to get data for next day compared to day job run at
    directory_path = storage_path / "data" / date
    logger.info(f"For date {date} use {directory_path}. Start downloading...")
    download_files(date)
    logger.info(f"Updating config files for streamers.")
    update_cfg_files(orchestrator, directory_path)
    logger.info("Ended task")


def ping_task():
    logger.info("Sheduler is working")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        logger.error("Usage: python scheduler.py <storage_path> <days_to_subtract> <available_RAM>")
        sys.exit(1)

    storage_path = Path(sys.argv[1])
    days_to_subtract = int(sys.argv[2])
    available_RAM = float(sys.argv[3])

    current_date = get_date(days_to_subtract)

    download_files(current_date)
    directory_path = storage_path / "data" / current_date
    os.makedirs(directory_path, exist_ok=True)
    logger.info("Create orchestrator")
    orchestrator = StreamerOrchestrator()
    orchestrator.set_storage_path(storage_path)
    logger.info("Register stations")
    orchestrate_first_launch(orchestrator, directory_path, available_RAM)
    logger.info("Try to launch streamers")
    orchestrator.launch_all_streamers(LaunchesModes.subprocess)

    # Create an instance of the scheduler
    scheduler = BlockingScheduler()

    # Schedule the execution of the download_files function every day at a specific time
    logger.info("Adding every day task")
    scheduler.add_job(
        scheduled_everyday_task,
        "cron",
        hour=23,
        minute=0,
        args=[days_to_subtract, orchestrator, storage_path, available_RAM],
    )

    scheduler.add_job(
        ping_task,
        "cron",
        hour="*",
        minute="*"
    )

    try:
        # Start the scheduler
        logger.info("Starting the scheduler...")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
