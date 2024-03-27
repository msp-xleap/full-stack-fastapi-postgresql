import socket
import re

def resolve_host(host: str) -> str:
    """
    Attempts to resolve the IP address of a host and returns the first IP it
    found.

    Args:
        host (str): The hostname to resolve.

    Returns:
        str: The IP address of the resolved host.

    Raises:
        NameError: If the host was not found.
    """
    try:
        data = socket.gethostbyname_ex(host)
        return data[2][0]
    except:
        raise NameError(f"Name not found: '{host}'")

def resolve_server_addr(server: str) -> str:
    """
    Attempts to resolve the IP address from a server address.

    Args:
        server (str): The server address, e.g., https://example.com.

    Returns:
        str: The IP address of the resolved server.

    Raises:
        SyntaxError: If the server name does not start with http:// or https://
        NameError: If the host was not found.
    """
    p = re.compile("^(https?://)(.*)", re.IGNORECASE)
    m = p.match(server)

    if m is None:
        raise SyntaxError(f"Invalid server address: '{server}'")
    else:
        return resolve_host(m.group(2))

