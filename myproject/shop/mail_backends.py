import socket
from django.core.mail.backends.smtp import EmailBackend

class IPv4EmailBackend(EmailBackend):
    """
    A custom email backend that forces IPv4 resolution for SMTP.
    This fixes issues on cloud platforms like Render where IPv6 connections
    to smtp.gmail.com are dropped due to strict reverse DNS policies.
    """
    def open(self):
        if self.connection:
            return False

        old_getaddrinfo = socket.getaddrinfo

        def ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
            # Force IPv4 (socket.AF_INET)
            return old_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

        socket.getaddrinfo = ipv4_getaddrinfo
        try:
            return super().open()
        finally:
            socket.getaddrinfo = old_getaddrinfo
