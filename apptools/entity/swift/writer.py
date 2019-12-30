import pathlib

from typing import List, Dict, Any, Tuple

from apptools.entity.navajo import Entity, Message, Property
from apptools.entity.io import IndentedWriter
from apptools.entity.text import camelcase, capitalize

# TODO Tasks:
#   * Remove Alamofire prefix
#   * Service struct should be an enum, meaning we cannot instantiate it and
#     we can remove the private initializer.
#   * Use Swiftlints marker to disable all linting on generated files.

reserved_words = [
    "guard", "Protocol", "Self", "Type", "__COLUMN__", "__FILE__",
    "__FUNCTION__", "__LINE__", "as", "break", "case", "class", "continue",
    "default", "deinit", "do", "dynamicType", "else", "enum", "extension",
    "fallthrough", "false", "final", "for", "func ", "if", "import", "in",
    "init", "internal", "is", "let", "nil", "operator", "private", "protocol",
    "public", "required", "return", "right", "self", "set", "static", "struct",
    "subscript", "super", "switch", "true", "typealias", "unowned", "var",
    "weak", "where", "while"
]


def write(entities: List[Entity], options: Dict[str, Any]) -> None:
    output = options["output"]

    for entity in entities:
        _write_entity(entity, output)


def _write_entity(entity: Entity, output: pathlib.Path) -> None:
    datamodel = output / _capitalize_path(entity.package / "datamodel")
    datamodel.mkdir(parents=True, exist_ok=True)
    datamodel_class = datamodel / f"{entity.name}Entity.swift"
    with IndentedWriter(path=datamodel_class) as writer:
        _write_datamodel(writer, entity)
    return

    logic = output / _capitalize_path(entity.package / "logic")
    logic.mkdir(parents=True, exist_ok=True)
    logic_class = logic / f"{entity.name}.swift"
    if not logic_class.exists():
        with IndentedWriter(path=logic_class) as writer:
            _write_logic(writer, entity)

    if entity.methods:
        service = output / _capitalize_path(entity.package / "service")
        service.mkdir(parents=True, exist_ok=True)
        service_class = service / f"{entity.name}Service.swift"
        with IndentedWriter(path=service_class) as writer:
            _write_service(writer, entity)


def _write_datamodel(writer: IndentedWriter, entity: Entity) -> None:
    writer.writeln(
        "// swiftlint:disable type_body_length file_length line_length identifier_name superfluous_disable_command"
    )
    writer.newline()
    writer.writeln("import Foundation")
    writer.newline()
    _write_datamodel_class(writer, entity.root)


def _write_datamodel_class(writer: IndentedWriter,
                           message: Message,
                           prefix: str = '') -> None:
    prefix += f"{message.name}."

    writer.write(f"class {message.name}Entity")
    if message.extends is not None:
        writer.append(f": {message.extends.name}")
    else:
        writer.append(f": Codable")
    writer.append(" {")
    writer.newline()

    constructor_parameters: List[Tuple[str, str]] = []

    for property in message.properties:
        if property.method == "request":
            continue

        indented_writer = writer.indented()

        name = _variable_name(property.name)
        if property.enum is not None:
            type = property.name

            _write_enum(indented_writer, property, property.enum)
        else:
            type = _swift_type(property.type)

        indented_writer.write(f"var {name}: {type}")
        if property.nullable:
            indented_writer.append("?")
        else:
            constructor_parameters.append((name, type))
        indented_writer.newline()

    for sub_message in message.messages:
        indented_writer = writer.indented()

        if sub_message.is_array:
            if sub_message.extends is None or sub_message.properties or sub_message.name != sub_message.extends.name:
                _write_datamodel_class(indented_writer, sub_message, prefix)
                type = f"[{prefix}{sub_message.name}]"
            else:
                type = f"[{sub_message.extends.name}]"
            name = f"{camelcase(sub_message.name)}List"
        else:
            if sub_message.extends is None or sub_message.properties or sub_message.name != sub_message.extends.name:
                _write_datamodel_class(indented_writer, sub_message, prefix)
                type = prefix + sub_message.name
            else:
                type = sub_message.extends.name
            name = camelcase(sub_message.name)

        indented_writer.write(f"var {name}: {type}")
        if sub_message.nullable:
            indented_writer.append("?")
        else:
            constructor_parameters.append((name, type))
        indented_writer.newline()

    super_constructor_parameters = []
    constructor_parameters_string = []

    if message.extends is not None:
        super_constructor_parameters = _get_constructor_parameters(
            message.extends)

        for construct_parameter in super_constructor_parameters:
            constructor_parameters_string.append(
                f"{construct_parameter[0]}: {construct_parameter[1]}")

    for construct_parameter in constructor_parameters:
        constructor_parameters_string.append(
            f"{construct_parameter[0]}: {construct_parameter[1]}")

    super_arguments_string: List[str] = []
    for construct_parameter in super_constructor_parameters:
        super_arguments_string.append(
            f"{construct_parameter[0]}: {construct_parameter[0]}")

    if constructor_parameters_string:
        indented_writer = writer.indented()

        indented_writer.newline()
        override = ""
        if not constructor_parameters:
            override = "override "
        indented_writer.writeln(
            f"{override}init({', '.join(constructor_parameters_string)}) {{")

        for constructor_parameter in constructor_parameters:
            name = constructor_parameter[0]
            indented_writer.indented().writeln(f"self.{name} = {name}")

        if message.extends is not None:
            indented_writer.newline()
            indented_writer.indented().writeln(
                f"super.init({', '.join(super_arguments_string)})")

        indented_writer.writeln("}")
    elif message.extends is None:
        writer.newline()
        writer.indented().writeln("init() { }")

    _write_coding(writer.indented(), message, prefix)
    writer.writeln("}")


def _write_coding(writer: IndentedWriter,
                  message: Message,
                  prefix: str = '') -> None:
    if message.messages or message.properties:
        writer.newline()
        writer.writeln("private enum CodingKeys: String, CodingKey {")

        for property in message.properties:
            if property.method == "request":
                continue

            writer.indented().writeln(
                f'case {_to_case(property.name)} = "{property.name}"')

        for sub_message in message.messages:
            indented_writer = writer.indented()

            name = sub_message.name
            if sub_message.is_array:
                name = f"{sub_message.name}List"

            writer.indented().writeln(
                f'case {_to_case(name)} = "{sub_message.name}"')

        writer.writeln("}")

    writer.newline()
    _write_decoding(writer, message, prefix)
    writer.newline()
    _write_encoding(writer, message, prefix)


def _write_decoding(writer: IndentedWriter,
                    message: Message,
                    prefix: str = '') -> None:
    writer.writeln("required init(from decoder: Decoder) throws {")

    indented_writer = writer.indented()

    if message.messages or message.properties:
        indented_writer.writeln(
            "let container = try decoder.container(keyedBy: CodingKeys.self)")

    for property in message.properties:
        if property.method == "request":
            continue

        variable_name = _to_case(property.name)
        variable_type = _swift_type(property.type)
        if property.enum:
            variable_type = property.name

        indented_writer.write(variable_name)
        indented_writer.append(" = try container.")
        if property.nullable:
            indented_writer.append("decodeIfPresent")
        else:
            indented_writer.append("decode")
        indented_writer.appendln(
            f"({variable_type}.self, forKey: .{variable_name})")

    for sub_message in message.messages:
        variable_name = _to_case(sub_message.name)
        variable_type = sub_message.name

        if sub_message.is_array:
            if sub_message.extends is None or sub_message.properties or sub_message.name != sub_message.extends.name:
                variable_type = f"[{prefix}{sub_message.name}]"
            else:
                variable_type = f"[{sub_message.extends.name}]"
            variable_name += "List"
        else:
            if sub_message.extends is None or sub_message.properties or sub_message.name != sub_message.extends.name:
                variable_type = prefix + sub_message.name
            else:
                variable_type = sub_message.extends.name

        indented_writer.write(variable_name)
        indented_writer.append(" = try container.")
        if sub_message.nullable:
            indented_writer.append("decodeIfPresent")
        else:
            indented_writer.append("decode")

        indented_writer.appendln(
            f"({variable_type}.self, forKey: .{variable_name})")

    if message.extends is not None:
        indented_writer.newline()
        indented_writer.writeln("try super.init(from: decoder)")

    writer.writeln("}")


def _write_encoding(writer: IndentedWriter,
                    message: Message,
                    prefix: str = '') -> None:
    override = ""
    if message.extends is not None:
        override = "override "

    writer.writeln(f"{override}func encode(to encoder: Encoder) throws {{")

    indented_writer = writer.indented()

    if message.extends is not None:
        indented_writer.writeln("try super.encode(to: encoder)")

    if message.properties or message.messages:
        indented_writer.writeln(
            f"var container = encoder.container(keyedBy: CodingKeys.self)")

    for property in message.properties:
        if property.method == "request":
            continue

        name = _variable_name(property.name)

        indented_writer.writeln(
            f"try container.encode({name}, forKey: .{name})")

    for sub_message in message.messages:
        name = _variable_name(sub_message.name)
        if sub_message.is_array:
            name += "List"

        indented_writer.writeln(
            f"try container.encode({name}, forKey: .{name})")

    writer.writeln("}")


def _get_constructor_parameters(entity: Entity) -> List[Tuple[str, str]]:
    constructor_parameters: List[Tuple[str, str]] = []

    if entity.root.extends is not None:
        constructor_parameters += _get_constructor_parameters(
            entity.root.extends)

    for property in entity.root.properties:
        name = camelcase(property.name)
        if property.enum is not None and property.enum:
            type = property.name
        else:
            type = _swift_type(property.type)

        if not property.nullable and property.method != "request":
            constructor_parameters.append((name, type))

    for message in entity.root.messages:
        name = message.name
        if message.is_array:
            if message.extends is None or len(
                    message.properties) > 0 or name != message.extends.name:
                type = f"[{name}]"
            else:
                type = f"[{message.extends.name}]"
            name = camelcase(name) + "List"
        else:
            if message.extends is None or len(
                    message.properties) > 0 or name != message.extends.name:
                type = name
            else:
                type = message.extends.name
            name = camelcase(name)

        if not message.nullable:
            constructor_parameters.append((name, type))

    return constructor_parameters


def _write_enum(writer: IndentedWriter, property: Property,
                cases: List[str]) -> None:
    writer.writeln(
        f"enum {property.name}: String, Codable, CaseIterable, Comparable {{")
    for case in cases:
        name = _to_case(case)
        value = case

        if name != value:
            writer.indented().writeln(f'case {_to_case(case)} = "{case}"')
        else:
            writer.indented().writeln(f'case {_to_case(case)}')

    writer.newline()
    _write_enum_comparable(writer.indented(), property)
    writer.writeln("}")


def _write_enum_comparable(writer: IndentedWriter, property: Property) -> None:
    writer.writeln(
        f"static func < (lhs: {property.name}, rhs: {property.name}) -> Bool {{"
    )
    indented_writer = writer.indented()
    indented_writer.writeln("let index = allCases.firstIndex(of: lhs)")
    indented_writer.writeln("let other = allCases.firstIndex(of: rhs)")
    indented_writer.newline()
    indented_writer.writeln("return index! < other!")
    writer.writeln("}")


def _write_logic(writer: IndentedWriter, entity: Entity) -> None:
    writer.writeln("import Foundation")
    writer.newline()
    _write_logic_class(writer, entity.root)


def _write_logic_class(writer: IndentedWriter, message: Message) -> None:
    writer.writeln(f"class {message.name}: {message.name}Entity {{")
    for message in message.messages:
        if message.extends is None or message.properties or message.name != message.extends.name:
            _write_logic_class(writer.indented(), message)

    if not message.messages:
        writer.newline()

    writer.writeln("}")


def _write_service(writer: IndentedWriter, entity: Entity) -> None:
    writer.writeln(
        f"// swiftlint:disable function_parameter_count superfluous_disable_command"
    )
    writer.newline()
    writer.writeln(f"import Alamofire")
    writer.newline()
    writer.writeln(f"struct {entity.name}Service {{")

    indented_writer = writer.indented()

    indented_writer.writeln(f'static let path = "/{entity.path}"')

    indented_writer.writeln("static let headers = [")
    indented_writer.indented().writeln(
        f'"X-Navajo-Version": "{max(entity.version, 0)}"')
    indented_writer.writeln("]")

    indented_writer.newline()
    indented_writer.writeln("private init() { }")

    writer.newline()

    for i, method in enumerate(entity.methods):
        for key_id in entity.key_ids:
            properties = entity.key_properties(key_id)
            required_properties = [
                property for property in properties if not property.nullable
            ]
            optional_properties = [
                property for property in properties if property.nullable
            ]

            parameters: List[str] = []
            for property in properties:
                name = camelcase(property.name)
                type = _swift_type(property.type)
                optional = "?" if property.nullable else ""

                parameters.append(f"{name}: {type}{optional}")

            if method == "GET":
                _write_service_get(indented_writer, entity, parameters,
                                   properties, required_properties,
                                   optional_properties)
            if method == "PUT":
                _write_service_put(indented_writer, entity, parameters,
                                   properties, required_properties,
                                   optional_properties)
            if method == "POST":
                _write_service_post(indented_writer, entity, parameters,
                                    properties, required_properties,
                                    optional_properties)
            if method == "DELETE":
                _write_service_delete(indented_writer, entity, parameters,
                                      properties, required_properties,
                                      optional_properties)

        if not entity.key_ids:
            if method == "GET":
                _write_service_get(indented_writer, entity)
            if method == "PUT":
                _write_service_put(indented_writer, entity)
            if method == "POST":
                _write_service_post(indented_writer, entity)
            if method == "DELETE":
                _write_service_delete(indented_writer, entity)

        if i != len(entity.methods) - 1:
            writer.newline()

    writer.writeln("}")


def _write_service_get(writer: IndentedWriter,
                       entity: Entity,
                       parameters: List[str] = [],
                       properties: List[Property] = [],
                       required_properties: List[Property] = [],
                       optional_properties: List[Property] = []) -> None:
    writer.writeln(
        f"static func {camelcase(entity.name)}({', '.join(parameters)}) -> JSONDecodableOperation<{entity.name}> {{"
    )

    operation_parameters: Dict[str, str] = {
        "path": "path",
        "headers": "headers"
    }

    indented_writer = writer.indented()

    if properties:
        if required_properties:
            if optional_properties:
                indented_writer.write("var")
            else:
                indented_writer.write("let")

            indented_writer.appendln(" parameters: [String: Any] = [")
            for i, property in enumerate(required_properties):
                indented_writer.indented().write(
                    f'"{property.name}": {_variable_name(property.name)}')
                if i != len(required_properties) - 1:
                    indented_writer.indented().append(",")
                indented_writer.indented().newline()
            indented_writer.writeln("]")
        elif optional_properties:
            indented_writer.writeln("var parameters: [String: Any] = []")

        for property in optional_properties:
            indented_writer.writeln(
                f'parameters["{property.name}"] = {_variable_name(property.name)}'
            )

        indented_writer.newline()
        indented_writer.writeln(
            "let encoding = Alamofire.URLEncoding(destination: .queryString, boolEncoding: .literal)"
        )
        indented_writer.writeln(
            "let input = ParameterInputEncoding(encoding: encoding, parameters: parameters)"
        )
        operation_parameters["input"] = "input"
        indented_writer.newline()

    operation_parameters["output"] = f"{entity.name}.self"
    indented_writer.writeln(
        f'return JSONDecodableOperation({", ".join([f"{name}: {value}" for (name, value) in operation_parameters.items()])})'
    )

    writer.writeln("}")


def _write_service_put(writer: IndentedWriter,
                       entity: Entity,
                       parameters: List[str] = [],
                       properties: List[Property] = [],
                       required_properties: List[Property] = [],
                       optional_properties: List[Property] = []) -> None:
    if parameters:
        writer.writeln(
            f"static func update({', '.join(parameters)}, {_variable_name(entity.name)}: {entity.name}) -> JSONDecodableOperation<{entity.name}> {{"
        )
    else:
        writer.writeln(
            f"static func update(_ {_variable_name(entity.name)}: {entity.name}) -> JSONDecodableOperation<{entity.name}> {{"
        )

    encoding_parameters: List[str] = [_variable_name(entity.name)]

    indented_writer = writer.indented()

    if properties:
        if required_properties:
            if optional_properties:
                indented_writer.write("var")
            else:
                indented_writer.write("let")

            indented_writer.appendln(" parameters: [String: Any] = [")
            for i, property in enumerate(required_properties):
                indented_writer.indented().write(
                    f'"{property.name}": {_variable_name(property.name)}')
                if i != len(required_properties) - 1:
                    indented_writer.indented().append(",")
                indented_writer.indented().newline()
            indented_writer.writeln("]")
        elif optional_properties:
            indented_writer.writeln("var parameters: [String: Any] = []")

        for property in optional_properties:
            indented_writer.writeln(
                f'parameters["{property.name}"] = {_variable_name(property.name)}'
            )

        indented_writer.newline()
        indented_writer.writeln(
            "let encoding = Alamofire.URLEncoding(destination: .queryString, boolEncoding: .literal)"
        )
        indented_writer.writeln(
            "let parameterInputEncoding = ParameterInputEncoding(encoding: encoding, parameters: parameters)"
        )
        encoding_parameters.append(
            "parameterInputEncoding: parameterInputEncoding")

    indented_writer.writeln(
        f'let input = EncodableEncoding({",".join(encoding_parameters)})')
    indented_writer.newline()
    indented_writer.writeln(
        f'return JSONDecodableOperation(path: path, method: .put, headers: headers, input: input, output: {entity.name}.self)'
    )

    writer.writeln("}")


def _write_service_post(writer: IndentedWriter,
                        entity: Entity,
                        parameters: List[str] = [],
                        properties: List[Property] = [],
                        required_properties: List[Property] = [],
                        optional_properties: List[Property] = []) -> None:
    if parameters:
        writer.writeln(
            f"static func insert({', '.join(parameters)}, {_variable_name(entity.name)}: {entity.name}) -> Operation {{"
        )
    else:
        writer.writeln(
            f"static func insert(_ {_variable_name(entity.name)}: {entity.name}) -> Operation {{"
        )

    operation_parameters: Dict[str, str] = {
        "path": "path",
        "headers": "headers"
    }

    indented_writer = writer.indented()

    if properties:
        if required_properties:
            if optional_properties:
                indented_writer.write("var")
            else:
                indented_writer.write("let")

            indented_writer.appendln(" parameters: [String: Any] = [")
            for i, property in enumerate(required_properties):
                indented_writer.indented().write(
                    f'"{property.name}": {_variable_name(property.name)}')
                if i != len(required_properties) - 1:
                    indented_writer.indented().append(",")
                indented_writer.indented().newline()
            indented_writer.writeln("]")
        elif optional_properties:
            indented_writer.writeln("var parameters: [String: Any] = []")

        for property in optional_properties:
            indented_writer.writeln(
                f'parameters["{property.name}"] = {_variable_name(property.name)}'
            )

        indented_writer.newline()
        indented_writer.writeln(
            "let encoding = Alamofire.URLEncoding(destination: .queryString, boolEncoding: .literal)"
        )
        indented_writer.writeln(
            "let input = ParameterInputEncoding(encoding: encoding, parameters: parameters)"
        )
        operation_parameters["input"] = "input"

    operation_parameters["output"] = f"{entity.name}.self"
    indented_writer.writeln(
        f'return PlainOperation({", ".join([f"{name}: {value}" for (name, value) in operation_parameters.items()])})'
    )

    writer.writeln("}")


def _write_service_delete(writer: IndentedWriter,
                          entity: Entity,
                          parameters: List[str] = [],
                          properties: List[Property] = [],
                          required_properties: List[Property] = [],
                          optional_properties: List[Property] = []) -> None:
    writer.writeln(
        f"static func remove({', '.join(parameters)}) -> Operation {{")

    encoding_parameters: List[str] = [_variable_name(entity.name)]

    indented_writer = writer.indented()

    if properties:
        if required_properties:
            if optional_properties:
                indented_writer.write("var")
            else:
                indented_writer.write("let")

            indented_writer.appendln(" parameters: [String: Any] = [")
            for i, property in enumerate(required_properties):
                indented_writer.indented().write(
                    f'"{property.name}": {_variable_name(property.name)}')
                if i != len(required_properties) - 1:
                    indented_writer.indented().append(",")
                indented_writer.indented().newline()
            indented_writer.writeln("]")
        elif optional_properties:
            indented_writer.writeln("var parameters: [String: Any] = []")

        for property in optional_properties:
            indented_writer.writeln(
                f'parameters["{property.name}"] = {_variable_name(property.name)}'
            )

        indented_writer.newline()
        indented_writer.writeln(
            "let encoding = Alamofire.URLEncoding(destination: .queryString, boolEncoding: .literal)"
        )
        indented_writer.writeln(
            "let parameterInputEncoding = ParameterInputEncoding(encoding: encoding, parameters: parameters)"
        )
        encoding_parameters.append(
            "parameterInputEncoding: parameterInputEncoding")

    indented_writer.writeln(
        f'let input = EncodableEncoding({",".join(encoding_parameters)})')
    indented_writer.newline()
    indented_writer.writeln(
        f'return PlainOperation(path: path, method: .put, headers: headers, input: input)'
    )

    writer.writeln("}")


def _to_case(s: str) -> str:
    if s.isupper():
        s = s.lower()

    s = _variable_name(s)
    output = []
    uppercase = False
    for character in s:
        if character == "_":
            uppercase = True
        else:
            if uppercase:
                output.append(character.upper())
                uppercase = False
            else:
                output.append(character)
    s = ''.join(output)

    if s in reserved_words:
        return f"`{s}`"
    return s


def _variable_name(name: str):
    name = camelcase(name)
    if name.startswith("_"):
        return name[1:]
    return name


def _capitalize_path(path: pathlib.Path) -> pathlib.Path:
    return pathlib.Path(*map(capitalize, path.parts))


def _swift_type(type: str) -> str:
    if type == 'integer':
        return 'Int'
    elif type == 'string':
        return 'String'
    elif type == 'boolean':
        return 'Bool'
    elif type == 'date':
        return 'String'
    elif type == 'clocktime':
        return 'String'
    elif type == 'float':
        return 'Double'
    elif type == 'binary':
        return 'Data'
    else:
        return 'String'
