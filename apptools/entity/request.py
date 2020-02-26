import pathlib
import urllib.request

from xml.etree.ElementTree import Element, XML


class Network(object):
    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self.url = "http://localhost:9090/navajo/Generic"

    def request(self, path: str) -> Element:
        request = urllib.request.Request(self.url, self.data(path).encode())
        opener = urllib.request.urlopen(request)
        response = opener.read().decode()

        return XML(response)

    def data(self, path) -> str:
        return f'''
            <tml documentImplementation="SAXP">
                <header>
                    <transaction 
                        rpc_usr="{self.username}"
                        rpc_pwd="{self.password}"
                        rpc_name="{path}" />
                </header>
            </tml>'''
