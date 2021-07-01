import pathlib
import os

from typing import List, Dict, Any, Tuple, Set

from apptools.entity.navajo import Entity, Message, Property
from apptools.entity.io import IndentedWriter
from apptools.entity.text import camelcase, capitalize

# TODO: Use Swiftlints marker to disable all linting on generated files.

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

debug = False
protocol_as_innerclass = False

class SharedInterface(object):
    def __init__(self, name: str, variables: List[str], parents: List[Entity] = []):
        super().__init__()

        self.name = name
        self.variables = variables
        self.parents = parents
        self.is_inner = True
        for parent in parents:
            if parent.name == self.name:
                self.is_inner = False

def write(entities: List[Entity], options: Dict[str, Any]) -> None:
    global debug
    output = options["output"]
    force = options.get("force", False)
    debug = options.get("debug", False)

    paths: Set[pathlib.Path] = set()
    for entity in entities:
        paths |= _write_entity(entity, output, force)

    if paths:
        xcode = pathlib.Path(__file__).parent / "xcode.rb"
        xcodeproj = options["xcodeproj"]

        # Xcode tool works with relative paths from the xcodeproj file
        rel_paths = [path.relative_to(xcodeproj.parent) for path in paths]
        os.system(
            f"ruby {xcode} {xcodeproj} {' '.join([str(path) for path in rel_paths])}"
        )


def _write_entity(entity: Entity, output: pathlib.Path, force: bool) -> Set[pathlib.Path]:
    paths: Set[pathlib.Path] = set()

    datamodel = output / _capitalize_path(entity.package / "datamodel")
    datamodel.mkdir(parents=True, exist_ok=True)
    datamodel_class = datamodel / f"{entity.name}Entity.swift"

    if not datamodel_class.exists():
        paths.add(datamodel_class)

    with IndentedWriter(path=datamodel_class) as writer:
        print(f"Write {str(datamodel_class)}")

        _write_datamodel(writer, entity)

    logic = output / _capitalize_path(entity.package / "logic")
    logic.mkdir(parents=True, exist_ok=True)
    logic_class = logic / f"{entity.name}.swift"

    if force or not logic_class.exists():
        paths.add(logic_class)

        with IndentedWriter(path=logic_class) as writer:
            print(f"Write {str(logic_class)}")

            _write_logic(writer, entity)

    if entity.methods:
        service = output / _capitalize_path(entity.package / "service")
        service.mkdir(parents=True, exist_ok=True)
        service_class = service / f"{entity.name}Service.swift"

        if not service_class.exists():
            paths.add(service_class)

        with IndentedWriter(path=service_class) as writer:
            print(f"Write {str(service_class)}")

            _write_service(writer, entity)

    return paths


def _write_datamodel(writer: IndentedWriter, entity: Entity) -> None:
    writer.writeln(
        "// swiftlint:disable type_body_length file_length line_length identifier_name superfluous_disable_command"
    )
    writer.newline()
    writer.writeln("import Foundation")
    writer.newline()
    _write_datamodel_inner(writer, entity.root)

def _write_datamodel_inner(writer: IndentedWriter,
                           message: Message,
                           prefix: str = ''):
    if message.is_interface:
        shared_interface = _get_shared_interface(message)
        if debug:
            writer.writeln(f"// interface")
        writer.writeln(f"protocol {message.name}Entity")
        if shared_interface.parents:
            writer.append(": ")
        for parent in shared_interface.parents:
            writer.append(f"{parent.name}, " )
        writer.appendln("{")
        indented_writer = writer.indented()
        for variable in shared_interface.variables:
            indented_writer.writeln(f"var {variable[1]}: {variable[2]} {{ get set }}" )
        
        writer.writeln("}")
        writer.newline()
    elif len(message.extends) > 1:
        shared_interface = _get_shared_interface(message)
        for extends in message.extends:
            _write_datamodel_class(writer, extends.root, prefix, shared_interface)
    else:
        _write_datamodel_class(writer, message, prefix)

def _write_datamodel_class(writer: IndentedWriter,
                           message: Message,
                           prefix: str,
                           shared_interface: SharedInterface = None) -> None:
    if shared_interface is None:
        writer.write(f"class {message.name}Entity")
    else:
        writer.write(f"class {shared_interface.name}{message.name}Entity")

    if not shared_interface:
        prefix += message.name + "."

    variables = _get_variables(message, prefix)
    nonnull_variables = variables[0]
    nullable_variables = variables[1]
    enums = variables[2]
    inner_classes = variables[3]
    super_variables = []
    super_interface_nonnull_variables = []
    super_interface_nullable_variables = []
    shared_interface_super_nonnull_variables = []
    shared_interface_super_nullable_variables = []
    
    if len(message.extends) == 1:
        super_variables = _get_variables(message.extends[0].root, prefix, True)[0]
    for super_interface in message.interfaces:
        super_interface_variables = _get_variables(super_interface.root, prefix)

        super_interface_nonnull_variables += super_interface_variables[0]
        super_interface_nullable_variables += super_interface_variables[1]
    if shared_interface:
        for parent in shared_interface.parents:
            shared_interface_super_nonnull_variables += _get_variables(parent.root, prefix)[0]
            shared_interface_super_nullable_variables += _get_variables(parent.root, prefix)[1]

    if shared_interface:
        if shared_interface.is_inner:
            if protocol_as_innerclass:
                writer.append(f": {message.name}, {prefix}{shared_interface.name}")
            else:
                writer.append(f': {message.name}, {prefix.replace(".", "")}{shared_interface.name}')
        else:
            writer.append(f": {message.name}, {shared_interface.name}")
    elif not message.extends:
        writer.append(f": Codable")
    else:
        writer.append(f": {message.extends[0].name}")
    if not shared_interface:
        for message_interface in message.interfaces:
            writer.append(f", {message_interface.name}")
    writer.append(" {")
    writer.newline()
    indented_writer = writer.indented()
    
    for inner_class in inner_classes:
        _write_datamodel_inner(indented_writer, inner_class[0], inner_class[1])

    for enum in enums:
        _write_enum(indented_writer, enum[0], enum[1])

    if shared_interface:
        for variable in shared_interface_super_nonnull_variables:
            if variable not in nonnull_variables:
                indented_writer.writeln(f"var {variable[1]}: {variable[2]}")

        for variable in shared_interface_super_nullable_variables:
            if variable not in nullable_variables:
                indented_writer.writeln(f"var {variable[1]}: {variable[2]}")
                
    else:
        for variable in nonnull_variables:
            indented_writer.writeln(f"var {variable[1]}: {variable[2]}")

        for variable in nullable_variables:
            indented_writer.writeln(f"var {variable[1]}: {variable[2]}")

        for variable in super_interface_nonnull_variables:
            if variable not in nonnull_variables:
                indented_writer.writeln(f"var {variable[1]}: {variable[2]}")
        
        for variable in super_interface_nullable_variables:
            if variable not in nullable_variables:
                indented_writer.writeln(f"var {variable[1]}: {variable[2]}")


    writer.newline()
    
    own_nonnull_variables = False
    for variable in nonnull_variables:
        if not variable in super_variables and not variable in shared_interface_super_nonnull_variables:
            own_nonnull_variables = True

    own_nullable_variables = False
    for variable in nullable_variables:
        if not variable in shared_interface_super_nullable_variables:
            own_nullable_variables = True

    # init
    if own_nonnull_variables or own_nullable_variables:
        if super_variables or nonnull_variables or super_interface_nonnull_variables or shared_interface or shared_interface_super_nonnull_variables or shared_interface_super_nullable_variables:
            # if we have a super and no additional vars then we should use override
            if (super_variables or shared_interface_super_nonnull_variables) and not (own_nonnull_variables):
                indented_writer.write(f"override init(")
            else:
                indented_writer.write(f"init(")
            init_elements = []
            for variable in super_variables:
                init_elements.append(f'{variable[1]}: {variable[2]}')
            for variable in super_interface_nonnull_variables:
                if variable in shared_interface_super_nonnull_variables:
                    continue
                if shared_interface:
                    init_elements.append(f'{variable[1]}: {variable[2]}')
                else:
                    init_elements.append(f'{variable[1]}: {variable[2]}')
            for variable in nonnull_variables:
                if shared_interface:
                    init_elements.append(f'{variable[1]}: {variable[2]}')
                else:
                    init_elements.append(f'{variable[1]}: {variable[2]}')
            if shared_interface:                
                for variable in shared_interface.variables:
                    init_elements.append(f'var {variable[1]}: {variable[2]}')
            for variable in shared_interface_super_nonnull_variables:
                if variable in nonnull_variables:
                    continue
                init_elements.append(f'{variable[1]}: {variable[2]}')

            indented_writer.append(", ".join(init_elements))

            indented_writer.appendln(") {")

            init_writer = indented_writer.indented()
            
            if (super_interface_nonnull_variables):
                for variable in super_interface_nonnull_variables:
                    if variable in shared_interface_super_nonnull_variables:
                        continue
                    if shared_interface:
                        if debug:
                            init_writer.writeln('/* super interface non null shared variable */ ')
                        init_writer.writeln(f'self.{variable[1]} = {variable[1]}')
                    else:
                        if debug:
                            init_writer.writeln('/* super interface non null variable */ ')
                        init_writer.writeln(f'self.{variable[1]} = {variable[1]}')

            if (shared_interface):
                for variable in shared_interface.variables:
                    if debug:
                        init_writer.writeln('/* shared interface variable */ ')
                    init_writer.writeln(f'self.{variable[1]} = {variable[1]}')

            if (shared_interface_super_nonnull_variables):
                for variable in shared_interface_super_nonnull_variables:
                    if variable in nonnull_variables:
                        continue
                    if debug:
                        init_writer.writeln('/* shared interface super nonnull variable */ ')
                    init_writer.writeln(f'self.{variable[1]} = {variable[1]}')

            if (nonnull_variables):
                if shared_interface:
                    init_elements = []
                    init_writer.write('super.init(')
                    for variable in nonnull_variables:
                        if debug:
                            init_elements.append(f'/* non null shared variable */ {variable[1]}: {variable[1]}')
                        else:
                            init_elements.append(f'{variable[1]}: {variable[1]}')
                    init_writer.append(", ".join(init_elements))
                    init_writer.appendln(')')
                else:
                    for variable in nonnull_variables:
                        if debug:
                            init_writer.writeln('/* non null variable */ ')
                        init_writer.writeln(f'self.{variable[1]} = {variable[1]}')
            
            if (super_variables):
                init_elements = []
                init_writer.write('super.init(')
                for variable in super_variables:
                    if debug:
                        init_elements.append(f'/* super variable */ {variable[1]}: {variable[1]}')
                    else:
                        init_elements.append(f'{variable[1]}: {variable[1]}')
                init_writer.append(", ".join(init_elements))
                init_writer.appendln(')')

            indented_writer.writeln("}")
        elif not message.extends:
            writer.newline()
            writer.indented().writeln("init() { }")

    if own_nonnull_variables or own_nullable_variables:
        _write_coding(writer.indented(), message, prefix, shared_interface)
    writer.writeln("}")
    writer.newline()


def _write_coding(writer: IndentedWriter,
                  message: Message,
                  prefix: str,
                  shared_interface: SharedInterface) -> None:
    variables = _get_variables(message, prefix)
    nonnull_variables = variables[0]
    nullable_variables = variables[1]
    enums = variables[2]
    inner_classes = variables[3]
    super_variables = []
    super_interface_nonnull_variables = []
    super_interface_nullable_variables = []
    shared_interface_super_nonnull_variables = []
    shared_interface_super_nullable_variables = []
    
    if len(message.extends) == 1:
        super_variables = _get_variables(message.extends[0].root, prefix, True)[0]
    for super_interface in message.interfaces:
        super_interface_variables = _get_variables(super_interface.root, prefix)

        super_interface_nonnull_variables += super_interface_variables[0]
        super_interface_nullable_variables += super_interface_variables[1]
    if shared_interface:
        for parent in shared_interface.parents:
            shared_interface_super_nonnull_variables += _get_variables(parent.root, prefix)[0]
            shared_interface_super_nullable_variables += _get_variables(parent.root, prefix)[1]

    
    if nonnull_variables or nullable_variables or shared_interface_super_nonnull_variables or shared_interface_super_nullable_variables or super_interface_nonnull_variables or super_interface_nullable_variables:
        writer.newline()
        writer.writeln("private enum CodingKeys: String, CodingKey {")

        if not shared_interface:
            for variable in nonnull_variables:
                writer.indented().writeln(
                    f'case {variable[1]} = "{variable[0]}"')

            for variable in nullable_variables:
                writer.indented().writeln(
                    f'case {variable[1]} = "{variable[0]}"')

        for variable in shared_interface_super_nonnull_variables:
            if variable not in nonnull_variables:
                writer.indented().writeln(
                    f'case {variable[1]} = "{variable[0]}"')

        for variable in shared_interface_super_nullable_variables:
            if variable not in nullable_variables:
                writer.indented().writeln(
                    f'case {variable[1]} = "{variable[0]}"')

        for variable in super_interface_nonnull_variables:
            if variable not in nonnull_variables:
                writer.indented().writeln(
                    f'case {variable[1]} = "{variable[0]}"')

        for variable in super_interface_nullable_variables:
            if variable not in nullable_variables:
                writer.indented().writeln(
                    f'case {variable[1]} = "{variable[0]}"')
        
        writer.indented().writeln(
                f'case __type__ = "__type__"')

        writer.writeln("}")

    writer.newline()

    # DECODING
    writer.writeln("required init(from decoder: Decoder) throws {")
    

    indented_writer = writer.indented()
    indented_indented_writer = indented_writer.indented()
    indented_indented_indented_writer = indented_indented_writer.indented()

    if nonnull_variables or nullable_variables or shared_interface_super_nonnull_variables or shared_interface_super_nullable_variables or super_interface_nonnull_variables or super_interface_nullable_variables:
        indented_writer.writeln("let container = try decoder.container(keyedBy: CodingKeys.self)")
        
        if not shared_interface:
            for variable in nonnull_variables:
                if variable[3] and len(variable[3].extends) > 1:
                    if len(variable[3].interfaces) == 1:
                        codingPrefix = prefix + variable[3].name
                    else:
                        codingPrefix = prefix
                    # TODO this piece is not only for nonnull_variables
                    # TODO check if we're list or not!
                    indented_writer.writeln(f"var {variable[1]}NestedUnkeyedContainer = try container.nestedUnkeyedContainer(forKey: .{variable[1]})")
                    indented_writer.writeln(f"var {variable[1]}TmpNestedUnkeyedContainer = {variable[1]}NestedUnkeyedContainer")
                    indented_writer.writeln(f"var {variable[1]} = {variable[2]}()")
                    indented_writer.writeln(f"while !{variable[1]}NestedUnkeyedContainer.isAtEnd {{")
                    indented_indented_writer.writeln(f"let typeContainer = try {variable[1]}NestedUnkeyedContainer.nestedContainer(keyedBy: CodingKeys.self)")
                    indented_indented_writer.writeln("let type = try typeContainer.decode(String.self, forKey: .__type__)")
                    indented_indented_writer.writeln("switch type {")
                    for extends in variable[3].extends:
                        indented_indented_writer.writeln(f'case "{pathlib.Path(*extends.path.parts[1:])}":')
                        indented_indented_indented_writer.writeln(f"{variable[1]}.append(try {variable[1]}TmpNestedUnkeyedContainer.decode({codingPrefix}{extends.name}.self))")
                    indented_indented_writer.writeln(f"default:")
                    indented_indented_indented_writer.writeln(f"break")
                    indented_indented_writer.writeln("}")
                    indented_writer.writeln("}")
                    indented_writer.writeln(f"self.{variable[1]} = {variable[1]}")
                else:
                    writer.indented().writeln(f'{variable[1]} = try container.decode({variable[2]}.self, forKey: .{variable[1]})')

            for variable in nullable_variables:
                writer.indented().writeln(f'{variable[1]} = try container.decodeIfPresent({variable[2][:-1]}.self, forKey: .{variable[1]})')

        for variable in shared_interface_super_nonnull_variables:
            if variable not in nonnull_variables:
                writer.indented().writeln(f'{variable[1]} = try container.decode({variable[2]}.self, forKey: .{variable[1]})')

        for variable in shared_interface_super_nullable_variables:
            if variable not in nullable_variables:
                writer.indented().writeln(f'{variable[1]} = try container.decodeIfPresent({variable[2][:-1]}.self, forKey: .{variable[1]})')

        for variable in super_interface_nonnull_variables:
            if variable not in nonnull_variables:
                writer.indented().writeln(f'{variable[1]} = try container.decode({variable[2]}.self, forKey: .{variable[1]})')

        for variable in super_interface_nullable_variables:
            if variable not in nullable_variables:
                writer.indented().writeln(f'{variable[1]} = try container.decodeIfPresent({variable[2][:-1]}.self, forKey: .{variable[1]})')


    if len(message.extends) == 1 or shared_interface:
        indented_writer.newline()
        indented_writer.writeln("try super.init(from: decoder)")

    writer.writeln("}")

    writer.newline()
    
    #ENCODING
    
    if len(message.extends) == 1 or shared_interface:
        writer.writeln("override func encode(to encoder: Encoder) throws {")
        indented_writer.writeln("try super.encode(to: encoder)")
    else:
        writer.writeln("func encode(to encoder: Encoder) throws {")
    

    if nonnull_variables or nullable_variables or shared_interface_super_nonnull_variables or shared_interface_super_nullable_variables or super_interface_nonnull_variables or super_interface_nullable_variables:
        indented_writer.writeln(f"var container = encoder.container(keyedBy: CodingKeys.self)")
        
        if not shared_interface:
            
            for variable in nonnull_variables:
                if variable[3] and len(variable[3].extends) > 1:
                    if len(variable[3].interfaces) == 1:
                        codingPrefix = prefix + variable[3].name
                    else:
                        codingPrefix = prefix
                    # TODO this piece is not only for nonnull_variables
                    # TODO check if we're list or not!
                    indented_writer.writeln(f"var {variable[1]}Container = container.nestedUnkeyedContainer(forKey: .{variable[1]})")
                    indented_writer.writeln(f"for element in {variable[1]} {{")
                    # TODO what does the switch help?
                    # TODO shouldn't we also encode the type here?
                    # TODO should refer to correct type (UserProgram.ProgramItemMatch instead of Match)
                    indented_indented_writer.writeln(f"var typeContainer = {variable[1]}Container.nestedContainer(keyedBy: CodingKeys.self)")
                    indented_indented_writer.writeln("switch element {")
                    for extends in variable[3].extends:
                        indented_indented_writer.writeln(f"case let {camelcase(extends.name)} as {codingPrefix}{extends.name}:")
                        indented_indented_indented_writer.writeln(f'try typeContainer.encode("{pathlib.Path(*extends.path.parts[1:])}", forKey: .__type__)')
                        indented_indented_indented_writer.writeln(f"try {variable[1]}Container.encode({camelcase(extends.name)})")
                    indented_indented_writer.writeln(f"default:")
                    indented_indented_indented_writer.writeln(f"break")
                    indented_indented_writer.writeln("}")
                    indented_writer.writeln("}")
                else:
                    writer.indented().writeln(f'try container.encode({variable[1]}, forKey: .{variable[1]})')

            for variable in nullable_variables:
                writer.indented().writeln(f'try container.encode({variable[1]}, forKey: .{variable[1]})')

        for variable in shared_interface_super_nonnull_variables:
            if variable not in nonnull_variables:
                writer.indented().writeln(f'try container.encode({variable[1]}, forKey: .{variable[1]})')

        for variable in shared_interface_super_nullable_variables:
            if variable not in nullable_variables:
                writer.indented().writeln(f'try container.encode({variable[1]}, forKey: .{variable[1]})')

        for variable in super_interface_nonnull_variables:
            if variable not in nonnull_variables:
                writer.indented().writeln(f'try container.encode({variable[1]}, forKey: .{variable[1]})')

        for variable in super_interface_nullable_variables:
            if variable not in nullable_variables:
                writer.indented().writeln(f'try container.encode({variable[1]}, forKey: .{variable[1]})')

    writer.writeln("}")

    writer.newline()


def _write_enum(writer: IndentedWriter, name: str,
                cases: List[str]) -> None:
    writer.writeln(
        f"enum {name}: String, Codable, CaseIterable, Comparable {{")
    for case in cases:
        case_name = _to_case(case)
        value = case

        if case_name != value:
            writer.indented().writeln(f'case {_to_case(case)} = "{case}"')
        else:
            writer.indented().writeln(f'case {_to_case(case)}')

    writer.newline()
    _write_enum_comparable(writer.indented(), name)
    writer.writeln("}")


def _write_enum_comparable(writer: IndentedWriter, name: str) -> None:
    writer.writeln(
        f"static func < (lhs: {name}, rhs: {name}) -> Bool {{"
    )
    indented_writer = writer.indented()
    indented_writer.writeln("let index = allCases.firstIndex(of: lhs)")
    indented_writer.writeln("let other = allCases.firstIndex(of: rhs)")
    indented_writer.newline()
    indented_writer.writeln("return index! < other!")
    writer.writeln("}")


def _write_logic(writer: IndentedWriter, entity: Entity) -> None:
    global protocol_as_innerclass
    writer.writeln("import Foundation")
    writer.newline()
    if protocol_as_innerclass:
        _write_logic_inner(writer, entity.root, "")
    else:
        postfix = _write_logic_inner(writer, entity.root, "")
        
        writer.newline()
        writer.writeln("// see: https://developer.apple.com/forums/thread/15195")
        writer.writeln(postfix)

def _write_logic_inner(writer: IndentedWriter, message: Message, prefix: str) -> str:
    global protocol_as_innerclass
    postfix = ""
    if message.is_interface:
        writer.writeln(f"protocol {message.name}: {message.name}Entity {{")
        if message.messages:
            indented_writer = writer.indented()
            for submessage in message.messages:
                name = submessage.name
                if submessage.is_array:
                    if len(submessage.extends) != 1 or submessage.properties or submessage.messages:
                        _write_logic_inner(indented_writer, submessage, message.name)
                else:
                    if len(submessage.extends) != 1 or submessage.properties or submessage.messages:
                        _write_logic_inner(indented_writer, submessage, message.name)
        writer.writeln("}")
        writer.newline()
        
    elif len(message.extends) > 1:
        shared_interface = _get_shared_interface(message)
        if message.interfaces and len(message.interfaces) > 1:
            assert False, f"This is not yet supported, multiple inheritance + multiple interfaces, not sure what code to generate"
    
        if message.interfaces and len(message.interfaces) == 1 and message.interfaces[0].root.name == message.name:
            # add import
            pass
        else:
            if message.interfaces:
                if protocol_as_innerclass:
                    writer.writeln(f"protocol {message.name}: {message.interfaces[0].root.name} {{")
                else:
                    postfix += f"protocol {prefix}{message.name}: {message.interfaces[0].root.name} {{"
            else:
                if protocol_as_innerclass:
                    writer.writeln(f"protocol {message.name} {{")
                else:
                    postfix += f"protocol {message.name} {{"
            indented_writer = writer.indented()
            for variable in shared_interface.variables:
                if protocol_as_innerclass:
                    indented_writer.writeln(f"var {variable[1]}: {variable[2]}" )
                else:
                    postfix += f"var {variable[1]}: {variable[2]}"
            if protocol_as_innerclass:
                writer.writeln("}")
                writer.newline()
            else:
                postfix += "}\n"
                postfix += "\n"
        for extends in message.extends:
            if protocol_as_innerclass:
                _write_logic_class(writer, extends.root, shared_interface, prefix)
                writer.newline()
            else:
                postfix += _write_logic_class(writer, extends.root, shared_interface, prefix)
                postfix += "\n"
    else:
        if protocol_as_innerclass:
            _write_logic_class(writer, message, None, prefix)
        else:
            postfix += _write_logic_class(writer, message, None, prefix)
    return postfix


def _write_logic_class(writer: IndentedWriter, message: Message, shared_interface: SharedInterface, prefix: str) -> str:
    global protocol_as_innerclass
    postfix = ""
    if shared_interface:
        writer.writeln(f"class {shared_interface.name}{message.name}: {shared_interface.name}{message.name}Entity {{")
    else:
        writer.writeln(f"class {message.name}: {message.name}Entity {{")
    writer.newline()

    indented_writer = writer.indented()
    
    for submessage in message.messages:
        name = submessage.name

        if submessage.is_array:
            if len(submessage.extends) != 1 or submessage.properties or submessage.messages:
                postfix += _write_logic_inner(indented_writer, submessage, message.name)
        else:
            if len(submessage.extends) != 1 or submessage.properties or submessage.messages:
                postfix += _write_logic_inner(indented_writer, submessage, message.name)

    if not message.messages:
        writer.newline()

    super_nonnull_variables = _get_variables(message, "", True)[0]
    super_nullable_variables = _get_variables(message, "", True)[1]
    shared_interface_super_nonnull_variables = []
    shared_interface_super_nullable_variables = []
    if shared_interface:
        for parent in shared_interface.parents:
            shared_interface_super_nonnull_variables += _get_variables(parent.root, "")[0]
            shared_interface_super_nullable_variables += _get_variables(parent.root, "")[1]
    
    if (shared_interface and (super_nonnull_variables or shared_interface_super_nonnull_variables or shared_interface_super_nullable_variables)):
        constructor_elements = []
        constructor_writer = indented_writer.indented()
        constructor_elements.append(f"{camelcase(message.name)}: {message.name}")
        for constructor_parameter in shared_interface_super_nonnull_variables:
            if constructor_parameter not in super_nonnull_variables:
                constructor_elements.append(f'{constructor_parameter[1]}: {constructor_parameter[2]}')
        for variable in shared_interface.variables:
            if constructor_parameter not in super_nonnull_variables:
                constructor_elements.append(f"{variable[1]}: {variable[2]}")
        indented_writer.writeln(f'convenience init({", ".join(constructor_elements)}) {{')
        super_elements = []
        
        for constructor_parameter in super_nonnull_variables:
            name = constructor_parameter[1]
            super_elements.append(f'{name}: {camelcase(message.name)}.{name}')
        for constructor_parameter in shared_interface_super_nonnull_variables:
            if constructor_parameter not in super_nonnull_variables:
                name = constructor_parameter[1]
                super_elements.append(f'{name}: {name}')
        if shared_interface:
            for variable in shared_interface.variables:
                if variable not in super_nonnull_variables:
                    super_elements.append(f'{variable[1]}: {variable[1]}')
        constructor_writer.writeln(f'self.init({", ".join(super_elements)})')
        indented_writer.writeln("}")
        

    writer.writeln("}")
    return postfix


def _write_service(writer: IndentedWriter, entity: Entity) -> None:
    writer.writeln(
        f"// swiftlint:disable function_parameter_count superfluous_disable_command"
    )
    writer.newline()
    writer.writeln(f"import Alamofire")
    writer.newline()
    writer.writeln(f"enum {entity.name}Service {{")

    indented_writer = writer.indented()

    indented_writer.writeln(f'static let path = "/{entity.path}"')

    indented_writer.writeln("static let headers = [")
    indented_writer.indented().writeln(
        f'"X-Navajo-Version": "{max(entity.version, 0)}"')
    indented_writer.writeln("]")

    writer.newline()

    for i, method in enumerate(entity.methods):
        for j, key_id in enumerate(entity.key_ids):
            properties = entity.key_properties(key_id)
            required_properties = [
                property for property in properties if not property.nullable
            ]
            optional_properties = [
                property for property in properties if property.nullable
            ]

            parameters: List[str] = []
            for property in properties:
                name = _variable_name(property.name)
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

            if j != len(entity.key_ids) - 1:
                writer.newline()

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

    indented_writer = writer.indented()

    indented_writer.writeln("var parameters: [String: Any] = [:]")
    indented_writer.writeln(f'parameters["v"] = {max(entity.version, 0)}')
    for property in required_properties + optional_properties:
        indented_writer.writeln(
            f'parameters["{property.name}"] = {_variable_name(property.name)}')

    indented_writer.newline()

    indented_writer.writeln(
        "let encoding = URLEncoding(destination: .queryString, boolEncoding: .literal)"
    )
    indented_writer.writeln(
        "let input = ParameterInputEncoding(encoding: encoding, parameters: parameters)"
    )

    indented_writer.newline()

    indented_writer.writeln(
        f"return JSONDecodableOperation(path: path, headers: headers, input: input, output: {entity.name}.self)"
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

    indented_writer = writer.indented()

    indented_writer.writeln("var parameters: [String: Any] = [:]")
    indented_writer.writeln(f'parameters["v"] = {max(entity.version, 0)}')
    for property in required_properties + optional_properties:
        indented_writer.writeln(
            f'parameters["{property.name}"] = {_variable_name(property.name)}')

    indented_writer.newline()

    indented_writer.writeln(
        "let encoding = URLEncoding(destination: .queryString, boolEncoding: .literal)"
    )
    indented_writer.writeln(
        "let parameterInputEncoding = ParameterInputEncoding(encoding: encoding, parameters: parameters)"
    )
    indented_writer.writeln(
        f'let input = EncodableEncoding({_variable_name(entity.name)}, parameterInputEncoding: parameterInputEncoding)'
    )

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
            f"static func insert({', '.join(parameters)}, {_variable_name(entity.name)}: {entity.name}) -> JSONDecodableOperation<{entity.name}> {{"
        )
    else:
        writer.writeln(
            f"static func insert(_ {_variable_name(entity.name)}: {entity.name}) -> JSONDecodableOperation<{entity.name}> {{"
        )

    indented_writer = writer.indented()

    indented_writer.writeln("var parameters: [String: Any] = [:]")
    indented_writer.writeln(f'parameters["v"] = {max(entity.version, 0)}')
    for property in required_properties + optional_properties:
        indented_writer.writeln(
            f'parameters["{property.name}"] = {_variable_name(property.name)}')

    indented_writer.newline()

    indented_writer.writeln(
        "let encoding = URLEncoding(destination: .queryString, boolEncoding: .literal)"
    )
    indented_writer.writeln(
        "let parameterInputEncoding = ParameterInputEncoding(encoding: encoding, parameters: parameters)"
    )
    indented_writer.writeln(
        f'let input = EncodableEncoding({_variable_name(entity.name)}, parameterInputEncoding: parameterInputEncoding)'
    )

    indented_writer.newline()

    indented_writer.writeln(
        f'return JSONDecodableOperation(path: path, method: .post, headers: headers, input: input, output: {entity.name}.self)'
    )

    writer.writeln("}")


def _write_service_delete(writer: IndentedWriter,
                          entity: Entity,
                          parameters: List[str] = [],
                          properties: List[Property] = [],
                          required_properties: List[Property] = [],
                          optional_properties: List[Property] = []) -> None:
    writer.writeln(
        f"static func remove({', '.join(parameters)}) -> JSONDecodableOperation<{entity.name}> {{")

    indented_writer = writer.indented()

    indented_writer.writeln("var parameters: [String: Any] = [:]")
    indented_writer.writeln(f'parameters["v"] = {max(entity.version, 0)}')
    for property in required_properties + optional_properties:
        indented_writer.writeln(
            f'parameters["{property.name}"] = {_variable_name(property.name)}')

    indented_writer.newline()

    indented_writer.writeln(
        "let encoding = URLEncoding(destination: .queryString, boolEncoding: .literal)"
    )
    indented_writer.writeln(
        "let input = ParameterInputEncoding(encoding: encoding, parameters: parameters)"
    )

    indented_writer.newline()

    indented_writer.writeln(
        f"return JSONDecodableOperation(path: path, method: .delete, headers: headers, input: input, output: {entity.name}.self)"
    )

    writer.writeln("}")

def _get_shared_interface(message: Message) -> SharedInterface:
    variables = []

    for property in message.properties:
        if property.method == "request":
            continue

        type = property.type
        name = property.name
        variable_name = camelcase(name)
        variable_type = _swift_type(type)
        nullable = property.nullable

        if property.enum:
            variable_type = name
            assert False, "This is not supported, because of Swift :-("
        if nullable:
            variable_type += "?"
        variables.append((name, variable_name, variable_type, None))

    for submessage in message.messages:
        name = submessage.name
        nullable = submessage.nullable

        if submessage.is_array:
            if not submessage.extends or (len(submessage.extends) == 1 and (submessage.properties or submessage.messages)):
                # assert False, "This is not supported, because of Swift :-("
                variable_type = "[" + submessage.name + "]"
            elif len(submessage.extends) == 1:
                variable_type = "[" + submessage.extends[0].name + "]"
            else:
                variable_type = "[" + submessage.name + "]"
                # assert False, "This is not supported, because of Swift :-("
            variable_name = camelcase(name) + "List"
        else:
            if not submessage.extends or (len(submessage.extends) == 1 and (submessage.properties or submessage.messages)):
                variable_type = submessage.name
                # assert False, f"This is not supported, because of Swift :-("
            elif len(submessage.extends) == 1:
                variable_type = submessage.extends[0].name
            else:
                variable_type = submessage.name
                # assert False, "This is not supported, because of Swift :-("
            variable_name = camelcase(name)

        if nullable:
            variable_type += "?"
        variables.append((name, variable_name, variable_type, submessage))
    return SharedInterface(message.name, variables, message.interfaces)

def _get_variables(message: Message, prefix: str, recursive: bool = False):
    nonnull_variables = []
    nullable_variables = []
    enums = []
    inner_classes = [] 

    if recursive:
        if len(message.extends) == 1:
            result = _get_variables(message.extends[0].root, prefix, recursive)
            nonnull_variables += result[0]
            nullable_variables += result[1]
            enums += result[2]
            inner_classes += result[3]
        for interface in message.interfaces:
            result = _get_variables(interface.root, prefix, recursive)
            nonnull_variables += result[0]
            nullable_variables += result[1]
            enums += result[2]
            inner_classes += result[3]

    for property in message.properties:
        if property.method == "request":
            continue

        type = property.type
        name = property.name
        variable_name = camelcase(name)
        variable_type = _swift_type(type)
        nullable = property.nullable

        if property.enum:
            enum_options = []
            for enum_value in property.enum:
                enum_options.append(enum_value)
            enums.append((name, enum_options))
            variable_type = name
        if nullable:
            variable_type += "?"
            nullable_variables.append((name, variable_name, variable_type, None))
        else:
            nonnull_variables.append((name, variable_name, variable_type, None))

    for submessage in message.messages:
        name = submessage.name
        nullable = submessage.nullable

        if submessage.is_array:
            if not submessage.extends or (len(submessage.extends) == 1 and (submessage.properties or submessage.messages)):
                # inner class
                inner_classes.append((submessage, prefix))
                variable_type = "[" + prefix + name + "]"
            elif len(submessage.extends) == 1:
                # external class
                variable_type = "[" + submessage.extends[0].name + "]"
            elif len(submessage.interfaces) == 1 and submessage.interfaces[0].name == submessage.name:
                # external interface
                inner_classes.append((submessage, prefix))
                variable_type = "[" + submessage.name + "]"
            else:
                inner_classes.append((submessage, prefix))
                if protocol_as_innerclass:
                    variable_type = "[" + prefix + submessage.name + "]"
                else:
                    variable_type = ("[" + prefix + submessage.name + "]").replace(".", "")
            variable_name = camelcase(name) + "List"
        else:
            if not submessage.extends or (len(submessage.extends) == 1 and (submessage.properties or submessage.messages)):
                inner_classes.append((submessage, prefix))
                variable_type = prefix + name
            elif len(submessage.extends) == 1:
                variable_type = submessage.extends[0].name
            else:
                inner_classes.append((submessage, prefix))
                variable_type = prefix + submessage.name
            variable_name = camelcase(name)

        if nullable:
            variable_type += "?"
            nullable_variables.append((name, variable_name, variable_type, submessage))
        else:
            nonnull_variables.append((name, variable_name, variable_type, submessage))
    return nonnull_variables, nullable_variables, enums, inner_classes

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
    if type == 'long':
        return 'Int64'
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
