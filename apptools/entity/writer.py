import pathlib
import urllib.parse
import xml.etree.ElementTree as ElementTree

from typing import Callable, List, Any, NamedTuple, Dict, Optional, Set, MutableMapping, Mapping
from xml.etree.ElementTree import Element, XML

from apptools.entity.navajo import Entity, Message, Property

Options = Dict[str, Any]
Writer = Callable[[List[Entity], Options], int]


def write(writer: Writer, options: Options) -> int:
    input: pathlib.Path = options["input"]

    paths = _api(input)
    mappings = _parse(input, paths)
    entities = _entities(input, mappings)

    return writer(entities, options)


def _api(path: pathlib.Path) -> set[pathlib.Path]:
    paths: set[pathlib.Path] = set()
    for path in path.rglob("*.xml"):
        # In the future this statement can possibly be removed since we might
        # want everything to be exposed that is defined.
        if path.stem == "entitymapping":
            continue
        paths.add(path)
    return paths


def _parse(input: pathlib.Path, paths: Set[pathlib.Path]) -> Mapping[pathlib.Path, Element]:
    mapping: MutableMapping[pathlib.Path, Element] = {}

    for path in paths:
        print(f"Fetch path {path}")
        mapping[path] = ElementTree.parse(path).getroot()

    return mapping


def _entities(input: pathlib.Path, mappings: Mapping[pathlib.Path,
                                                     Element]) -> List[Entity]:
    return [
        _entity(input, path, element, mappings)
        for path, element in mappings.items()
    ]


def _entity(input: pathlib.Path, path: pathlib.Path, element: Element,
            mappings: Mapping[pathlib.Path, Element]) -> Entity:
    name = path.stem
    version = _version(name, element)
    root = _root(name, version, element)
    methods = _methods(element)
    message = _message(input, path, root, mappings)
    package = _package(input, path, name)

    return Entity(name, path, package, version, methods, message)


def _version(name: str, element: Element) -> int:
    version = -1
    for sub_element in list(element):
        if (sub_element.tag != "message"
                or not sub_element.attrib["name"].startswith(name)):
            continue

        if "." in sub_element.attrib["name"]:
            version = max(version,
                          int(sub_element.attrib["name"].split(".")[1]))

    return version


def _root(name: str, version: int, element: Element) -> Element:
    if version == -1:
        root = element.find(f"message[@name='{name}']")
    else:
        root = element.find(f"message[@name='{name}.{version}']")

    assert root is not None, f"Root message not found for input {name}"

    return root


def _methods(element: Element) -> List[str]:
    return [
        operation.get("method")
        for operation in element.findall("operations/operation")
    ]


def _package(input: pathlib.Path, path: pathlib.Path,
             name: str) -> pathlib.Path:
    return pathlib.Path(str(path).removeprefix(str(input) + "/")).parent


def _message(input: pathlib.Path, path: pathlib.Path, element: Element,
             mappings: Mapping[pathlib.Path, Element]) -> Message:
    name = element.get("name").split(".")[0]
    is_array = element.get("type") == "array"
    nullable = _is_message_nullable(element.get("subtype"))

    properties_raw: List[Element] = []
    extends_raw: Optional[str] = None
    if is_array:
        definition = element.find("message[@type='definition']")
        properties_raw = element.findall(
            "message[@type='definition']/property")
        messages_raw = element.findall("message[@type='definition']/message")
        extends_raw = definition.get("extends")
    else:
        definition = element
        properties_raw = element.findall("./property")
        messages_raw = element.findall("./message")
        extends_raw = element.get("extends")

    properties = [_property(property) for property in properties_raw]
    messages = [_message(input, path, message, mappings) for message in messages_raw]

    parents: List[Entity] = []
    if extends_raw is not None:
        for extends_item in extends_raw.split("^"):
            extends = _extends(extends_item)
            extension = pathlib.Path(*extends.path.parts)
            dir = pathlib.Path(*input.parts[:input.parts.index("entities")])
            parent = _entity(input, extension, mappings[dir / "entities" / (str(extension) + ".xml")], mappings)
            parents.append(parent)

            assert extends.name.version == parent.version, f"Version error: Entity at {path} includes an extension of {parent.name} with version {extends.name.version}, but should be {parent.version}"

    return Message(name, is_array, nullable, properties, messages, parents)


def _property(element: Element) -> Property:
    name = element.get("name")
    type = element.get("type")

    assert name is not None and type is not None, "All property require a name and a type"

    subtype = element.get("subtype")
    key = element.get("key")

    return Property(name, type, element.get("method"),
                    _is_property_nullable(subtype), _enum(subtype),
                    _is_key(key), _is_optional_key(key), _get_key_ids(key))


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
    return key is not None


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


Name = NamedTuple("Name", [("base", str), ("version", int)])
Extends = NamedTuple("Extends", [("name", Name), ("path", pathlib.Path)])


def _extends(raw: str) -> Extends:
    components = urllib.parse.urlparse(raw)
    path = pathlib.Path(components.netloc) / pathlib.Path(components.path)
    name = _name(path.name)
    path = path.with_name(name.base)
    
    return Extends(name, path)


def _name(raw: str) -> Name:
    if "." not in raw:
        return Name(raw, -1)

    components = raw.split(".")
    return Name(components[0], int(components[1]))
