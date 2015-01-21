__author__ = 'michele'
import socket

def get_local_address(destination, port=37852):
    """Guess the local address where the client can reach the server"""
    s = socket.socket(type=socket.SOCK_DGRAM)
    try:
        """by using datagram socket I can connect without any exception if the
        address is reacheble"""
        s.connect((destination, port))
        return s.getsockname()[0]
    except socket.error:
        return ""
