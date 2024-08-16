from enum import Enum


class Protocol(Enum):
    """
    An enumeration representing different internet protocols.

    Attributes:
    FTP : str
        Represents the File Transfer Protocol.
    HTTP : str
        Represents the Hypertext Transfer Protocol.
    HTTPS : str
        Represents the Secure Hypertext Transfer Protocol.
    """
    FTP = "ftp"
    HTTP = "http"
    HTTPS = "https"
