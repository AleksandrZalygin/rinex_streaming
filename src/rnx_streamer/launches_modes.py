from enum import Enum


class LaunchesModes(Enum):
    """
    An enumeration representing different modes of launching applications.

    Attributes:
    subprocess : str
        Represents launching an application in a subprocess.
    service : str
        Represents launching an application as a service.
    docker : str
        Represents launching an application in a Docker container.
    """
    subprocess = "subprocess"
    service = "service"
    docker = "docker"
