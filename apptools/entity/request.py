import pathlib
import urllib.request

from xml.etree.ElementTree import Element, XML


class Rpc(object):
    def __init__(self, username: str, password: str, path: pathlib.Path,
                 name: str) -> None:
        self.username = username
        self.password = password
        self.path = path
        self.name = name

    @staticmethod
    def make(username: str, password: str, file: pathlib.Path) -> "Rpc":
        return Rpc(username, password, Rpc.named(file), file.stem)

    @staticmethod
    def named(file: pathlib.Path) -> pathlib.Path:
        parts = file.parts[file.parts.index("entity"):]

        return pathlib.Path(*parts).with_suffix("")


class Call(object):
    def __init__(self, rpc: Rpc) -> None:
        self.rpc = rpc
        self.url = "http://localhost:9090/navajo/Generic"

    def execute(self) -> Element:
        print(f"Requesting \"{self.rpc.path}\"")

        request = urllib.request.Request(self.url, self.data.encode())
        opener = urllib.request.urlopen(request)
        response = opener.read().decode()

        return XML(response)

    @property
    def data(self) -> str:
        return f'''
            <tml documentImplementation="SAXP">
                <header>
                    <transaction 
                        rpc_usr="{self.rpc.username}"
                        rpc_pwd="{self.rpc.password}"
                        rpc_name="{"/".join(self.rpc.path.parts)}" />
                </header>
            </tml>'''
