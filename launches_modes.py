from enum import Enum


class LaunchesModes(Enum):
    subprocess = "subprocess"
    service = "service"
    docker = "docker"
