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
        # We are sending a request to an entity file which basically returns
        # all the content of that file backs to us. This will not execute the
        # entity but instead run the file as a navascript call.
        return f'''
            <tml documentImplementation="SAXP">
                <header application="TARONGA">
                    <transaction
                        rpc_usr="{self.username}"
                        rpc_pwd="{self.password}"
                        rpc_name="{path}" />
                </header>
            </tml>'''
