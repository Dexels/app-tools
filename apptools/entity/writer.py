import pathlib
import urllib.parse

from typing import Callable, List, Any, NamedTuple, Dict, Optional
from xml.etree.ElementTree import Element

from apptools.entity.navajo import Entity, Message, Property
from apptools.entity.request import Call, Rpc

Options = Dict[str, Any]
Writer = Callable[[List[Entity], Options], int]

EntityValue = NamedTuple("EntityValue", [("path", pathlib.Path),
                                         ("entity", Element)])
EntitiesMap = Dict[str, EntityValue]


def write(writer: Writer, options: Options) -> int:
    username: str = options["username"]
    password: str = options["password"]
    input: pathlib.Path = options["input"]

    entities: EntitiesMap = {}
    for file in input.rglob("*.xml"):
        if file.stem == "entitymapping":
            continue

        rpc = Rpc.make(username, password, file)
        entity = Call(rpc).execute()

        entities[rpc.name] = EntityValue(rpc.path, entity)

    print(f"Requested {len(entities)} entities")

    loaded_entities = [
        _load(input, name, value, entities)
        for name, value in entities.items()
    ]

    return writer(loaded_entities, options)


def _load(input: pathlib.Path, name: str, value: EntityValue,
          entities: EntitiesMap) -> Entity:
    version = _max_version(name, value.entity)
    if version == -1:
        root_message = value.entity.find(f"message[@name='{name}']")
    else:
        root_message = value.entity.find(f"message[@name='{name}.{version}']")

    if root_message is None:
        raise NameError(f"Root message not found for input {input}")

    methods = [
        element.get("method") or "GET"
        for element in value.entity.findall("operations/operation")
    ]
    message = _load_message(input, root_message, entities)
    package = _package(input, value.path, name)

    return Entity(name, value.path, package, version, methods, message)


def _max_version(name: str, entity: Element) -> int:
    version = -1
    for element in list(entity):
        if (element.tag != "message"
                or not element.attrib["name"].startswith(name)):
            continue

        if "." in element.attrib["name"]:
            version = max(version, int(element.attrib["name"].split(".")[1]))

    return version


def _package(input: pathlib.Path, path: pathlib.Path,
             name: str) -> pathlib.Path:
    parts = []
    target = path.parts[0]
    is_matched = False
    for part in input.parts:
        if target == part:
            is_matched = True

        if is_matched:
            parts.append(part)

    return path.relative_to(pathlib.Path(*parts)).parent


def _load_message(input: pathlib.Path, message: Element,
                  entities: EntitiesMap) -> Message:
    name = message.get("name").split(".")[0]
    is_array = message.get("type") == "array"
    nullable = _is_message_nullable(message.get("subtype"))

    properties_raw: List[Element] = []
    extends_raw: Optional[str] = None
    if is_array:
        definition = message.find("message[@type='definition']")
        properties_raw = message.findall(
            "message[@type='definition']/property")
        messages_raw = message.findall("message[@type='definition']/message")
        extends_raw = definition.get("extends")
    else:
        properties_raw = message.findall("./property")
        messages_raw = message.findall("./message")
        extends_raw = message.get("extends")

    properties = [_load_property(property) for property in properties_raw]
    messages = [
        _load_message(input, message, entities) for message in messages_raw
    ]

    extends = None
    if extends_raw is not None:
        extends_name = _load_extends(extends_raw).name_components.name
        extends = _load(input, extends_name, entities[extends_name], entities)

    return Message(name, is_array, nullable, properties, messages, extends)


def _load_property(element) -> Property:
    subtype = element.get("subtype")
    key = element.get("key")

    return Property(element.get("name"), element.get("type"),
                    element.get("method"), _is_property_nullable(subtype),
                    _enum(subtype), _is_key(key), _is_optional_key(key),
                    _get_key_ids(key))


def _is_message_nullable(subtype: Optional[str]) -> bool:
    return _is_nullable(subtype, False)


def _is_property_nullable(subtype: Optional[str]) -> bool:
    return _is_nullable(subtype, True)


def _is_nullable(subtype: Optional[str], fallback: bool) -> bool:
    if subtype is not None:
        for subtype_info in subtype.split(","):
            subtype_info_key = subtype_info.split("=")[0]
            subtype_info_value = subtype_info.split("=")[1]
            if subtype_info_key == "nullable":
                return subtype_info_value == "true"
    return fallback


def _enum(subtype: Optional[str]) -> Optional[List[str]]:
    if subtype is not None:
        for subtype_info in subtype.split(","):
            subtype_info_key = subtype_info.split("=")[0]
            subtype_info_value = subtype_info.split("=")[1]
            if subtype_info_key == "enum":
                return subtype_info_value.split(";")

    return None


def _is_key(key: Optional[str]) -> bool:
    if key is not None:
        return True

    return False


def _is_optional_key(key: Optional[str]) -> bool:
    if key is not None:
        return "optional" in key

    return False


def _get_key_ids(key: Optional[str]) -> List[str]:
    # Our key syntax is not the best. We split each component on the
    # comma but our id is a multi value separated by comma again. So it
    # has to be on the end.
    if key is not None:
        if "id=" in key:
            return key.split("id=")[-1].split(",")
        else:
            return ["default"]

    return []


NameComponents = NamedTuple("NameComponents", [("name", str),
                                               ("version", int)])
Extends = NamedTuple("Extends", [("scheme", str), ("path", pathlib.Path),
                                 ("name_components", NameComponents)])


def _load_extends(extends: str) -> Extends:
    components = urllib.parse.urlparse(extends)
    path = pathlib.Path(components.netloc) / pathlib.Path(components.path[1:])
    name_components = _load_name_components(path.stem)
    path = path.with_name(name_components.name)

    return Extends(components.scheme, path, name_components)


def _load_name_components(name: str) -> NameComponents:
    if "." not in name:
        return NameComponents(name, -1)

    components = name.split(".")
    return NameComponents(components[0], int(components[1]))
