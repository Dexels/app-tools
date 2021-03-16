import pathlib

from typing import List, Optional


class Property(object):
    def __init__(self, name: str, type: str, method: Optional[str],
                 nullable: bool, enum: Optional[List[str]], is_key: bool,
                 is_optional_key: bool, key_ids: List[str]):
        super().__init__()

        self.name = name
        self.type = type
        self.method = method
        self.nullable = nullable
        self.enum = enum
        self.is_key = is_key
        self.is_optional_key = is_optional_key
        self.key_ids = key_ids


class Message(object):
    def __init__(self, name: str, is_array: bool, nullable: bool,
                 properties: List[Property], messages: List["Message"],
                 extends: Optional["Entity"]):
        super().__init__()

        self.name = name
        self.is_array = is_array
        self.nullable = nullable
        self.properties = properties
        self.messages = messages
        self.extends = extends


class Entity(object):
    def __init__(self, name: str, path: pathlib.Path, package: pathlib.Path,
                 version: int, methods: List[str], root: Message) -> None:
        super().__init__()

        self.name = name
        self.path = path
        self.package = package
        self.version = version
        self.methods = methods
        self.root = root

    def key_properties(self, key_id) -> List[Property]:
        result = []

        for property in self.root.properties:
            if property.is_key and key_id in property.key_ids:
                result.append(property)
        if self.root.extends is not None:
            result += self.root.extends.key_properties(key_id)
        return result

    @property
    def key_ids(self) -> List[str]:
        result: List[str] = []

        if self.root.extends is not None:
            result += self.root.extends.key_ids
        for property in self.root.properties:
            if property.is_key:
                for key in property.key_ids:
                    if not key in result:
                        result.append(key)
        return result
