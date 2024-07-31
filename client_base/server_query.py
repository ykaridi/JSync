import os
import re


def query_server(query_function, configuration_file):
    # type: (callable, str) -> tuple[str, int, str]
    default_connection = "user@localhost:9501"
    if os.path.exists(configuration_file):
        with open(configuration_file, "r") as f:
            default_connection = f.read()

    while True:
        connection_description = query_function(default_connection)
        if connection_description == "":
            return
        m = re.match(r"(?P<name>.*)@(?P<host>.*)(:(?P<port>[0-9]*))", connection_description)
        if m is not None:
            break

    with open(configuration_file, "w") as f:
        f.write(connection_description)

    name = m.group("name").encode("utf-8")
    host = m.group("host").encode("utf-8")
    port = int(m.group("port"))

    return host, port, name
