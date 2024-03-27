import socket
import re

def resolve_host(host: str) -> str:
    # Attempts to resolve the IP address of a host and returns the first IP it found
    # Raises NameError if the host was not found
    try:
        data = socket.gethostbyname_ex(host)
        return data[2][0];
    except:
        raise NameError(f"Name not found: '{host}'")

def resolve_server_addr(server: str) -> str:
    # Attempts to resolve the IP address from a server address e.g. https://example.com
    # which then calls resolve_host('example.com')
    # Raises SyntaxError if the server name does not start with http:// or https://
    # Raises NameError if the host was not found
    p = re.compile("^(https?://)(.*)", re.IGNORECASE)
    m = p.match(server);

    if None == m:
        raise SyntaxError(f"Invalid server address: '{server}'")
    else:
        return resolve_host(m.group(2));

