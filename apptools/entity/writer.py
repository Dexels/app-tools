import pathlib
import urllib.parse
import xml.etree.ElementTree as ElementTree

from typing import Callable, List, Any, NamedTuple, Dict, Optional, Set, MutableMapping, Mapping
from xml.etree.ElementTree import Element

from apptools.entity.navajo import Entity, Message, Property
from apptools.entity.request import Network

Options = Dict[str, Any]
Writer = Callable[[List[Entity], Options], int]


def write(writer: Writer, options: Options) -> int:
    input: pathlib.Path = options["input"]
    username: str = options["username"]
    password: str = options["password"]
    includes: List[str] = options.get("entities", None)
    skips: List[str] = options.get("skip", None)

    paths = _entity_mappings_paths(input, includes, skips)
    mappings = _fetch(paths, username, password)
    entities = _entities(input, mappings)

    return writer(entities, options)


def _entity_mappings_paths(path: pathlib.Path,
                           includes: Optional[List[str]],
                           skips: Optional[List[str]]) -> Set[pathlib.Path]:
    paths: Set[pathlib.Path] = set()
    for file in path.rglob("*entitymapping.xml"):
        print(f"Parsing entity mapping: {file}")

        parsed = ElementTree.parse(str(file))
        for property in parsed.findall(".//property[@name='entity']"):
            value = property.get("value")
            if value is not None:
                path = pathlib.Path("entity", value)
                if (includes is None or str(path) in includes) and (skips is None or str(path) not in skips):
                    paths.add(path)

    return paths


def _included(path: pathlib.Path, includes: Optional[List[str]]) -> bool:
    if includes is None:
        return True

    return str(path) in includes


def _fetch(paths: Set[pathlib.Path], username: str,
           password: str) -> Mapping[pathlib.Path, Element]:
    network = Network(username, password)

    mapping: MutableMapping[pathlib.Path, Element] = {}

    def fetch(paths: Set[pathlib.Path]):
        for path in paths:
            # Avoid calling the same paths because they're reused somewhere
            # else.
            if path in mapping:
                continue

            print(f"Fetch {path}")

            # Requesting the entity requires a unix path.
            element = network.request(str(path.as_posix()))
            mapping[path] = element

            # Find all extension in the entities. We need to load them as well.
            extensions: Set[pathlib.Path] = set()
            for message in element.findall(".//message[@extends]"):
                extends = message.get("extends")
                if extends is None:
                    continue

                extension = pathlib.Path("entity",
                                         *_extends(extends).path.parts)
                extensions.add(extension)

            fetch(extensions)

    fetch(paths)

    return mapping


def _entities(input: pathlib.Path, mappings: Mapping[pathlib.Path,
                                                     Element]) -> List[Entity]:
    return [
        _entity(input, path, element, mappings)
        for path, element in mappings.items()
    ]


def _entity(input: pathlib.Path, path: pathlib.Path, element: Element,
            mappings: Mapping[pathlib.Path, Element]) -> Entity:
    print(f"Parsing {path}")

    name = path.stem
    version = _version(name, element)
    root = _root(name, version, element)
    methods = _methods(element)
    message = _message(input, root, mappings)
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
        operation.get("method") or "GET"
        for operation in element.findall("operations/operation")
    ]


def _package(input: pathlib.Path, path: pathlib.Path,
             name: str) -> pathlib.Path:
    folder = pathlib.Path(*input.parts[input.parts.index("entity"):])

    package = path.parts
    for part in folder.parts:
        if part == package[0]:
            package = package[1:]
        else:
            break

    return pathlib.Path(*package).parent


def _message(input: pathlib.Path, element: Element,
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
        properties_raw = element.findall("./property")
        messages_raw = element.findall("./message")
        extends_raw = element.get("extends")

    properties = [_property(property) for property in properties_raw]
    messages = [_message(input, message, mappings) for message in messages_raw]

    parent: Optional[Entity] = None
    if extends_raw is not None:
        extends = _extends(extends_raw)

        extension = pathlib.Path("entity", *extends.path.parts)
        parent = _entity(input, extension, mappings[extension], mappings)

    return Message(name, is_array, nullable, properties, messages, parent)


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
    path = pathlib.Path(components.netloc) / pathlib.Path(components.path[1:])
    name = _name(path.stem)
    path = path.with_name(name.base)

    return Extends(name, path)


def _name(raw: str) -> Name:
    if "." not in raw:
        return Name(raw, -1)

    components = raw.split(".")
    return Name(components[0], int(components[1]))
