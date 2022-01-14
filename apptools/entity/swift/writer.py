import pathlib
import os

from typing import List, Dict, Any, Tuple, Set

from apptools.entity.navajo import Entity, Message, Property
from apptools.entity.io import IndentedWriter
from apptools.entity.text import camelcase, capitalize

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

class SharedInterface(object):
    def __init__(self, name: str, variables: List[str], parents: List[Entity] = [], enums: List = []):
        super().__init__()

        self.name = name
        self.variables = variables
        self.parents = parents
        self.enums = enums
        self.is_inner = True
        for parent in parents:
            if parent.name == self.name:
                self.is_inner = False

class Variable(object):
    def __init__(self, network_name: str, name: str, type: str, primitive: bool, nullable: bool, message: Message):
        super().__init__()

        self.network_name = network_name
        self.name = name
        self.type = type
        self.primitive = primitive
        self.nullable = nullable
        self.message = message

    def __eq__(self, other):
        if isinstance(other, Variable):
            return self.network_name == other.network_name
        return NotImplemented

def write(entities: List[Entity], options: Dict[str, Any]) -> None:
    output = options["output"]
    force = options.get("force", False)

    for entity in entities:
        _write_entity(entity, output, force)

def _write_entity(entity: Entity, output: pathlib.Path, force: bool):
    datamodel = output / _capitalize_path(entity.package) / "DataModel"
    datamodel.mkdir(parents=True, exist_ok=True)
    datamodel_class = datamodel / f"{entity.name}Entity.swift"

    with IndentedWriter(path=datamodel_class) as writer:
        print(f"Write {str(datamodel_class)}")

        _write_datamodel(writer, entity)

    logic = output / _capitalize_path(entity.package) / "Logic"
    logic.mkdir(parents=True, exist_ok=True)
    logic_class = logic / f"{entity.name}.swift"

    if force or not logic_class.exists():
        with IndentedWriter(path=logic_class) as writer:
            print(f"Write {str(logic_class)}")

            _write_logic(writer, entity)

    if entity.methods:
        service = output / _capitalize_path(entity.package) / "Service"
        service.mkdir(parents=True, exist_ok=True)
        service_class = service / f"{entity.name}Service.swift"

        with IndentedWriter(path=service_class) as writer:
            print(f"Write {str(service_class)}")

            _write_service(writer, entity)


def _write_datamodel(writer: IndentedWriter, entity: Entity) -> None:
    writer.writeln("import Foundation")
    writer.writeln("import SendratoAppSDK")
    writer.newline()
    postfix = _write_datamodel_inner(writer, entity.root)
    writer.newline()
    writer.writeln(postfix)

def _write_datamodel_inner(writer: IndentedWriter,
                           message: Message,
                           prefix: str = '') -> str:
    postfix = ""
    if len(message.extends) > 1:
        shared_interface = _get_shared_interface(message, prefix)
    
        postfix += f'protocol {prefix.replace(".", "")}{message.name}Entity {{\n'
        indented_writer = writer.indented()
        for enum in shared_interface.enums:
            with IndentedWriter(path=None) as enum_writer:
                _write_enum(enum_writer, f'{prefix.replace(".", "")}{message.name}Entity{enum[0]}', enum[1])
                enum_writer.fp.seek(0)
                postfix = enum_writer.fp.read() + "\n" + postfix
        for variable in shared_interface.variables:
            postfix += f"\tvar {variable.name}: {variable.type} {{ get set }}\n"
        postfix += "}\n\n"
        for extends in message.extends:
            postfix += _write_datamodel_class(writer, extends.root, prefix, shared_interface)
            postfix += "\n"
    else:
        postfix += _write_datamodel_class(writer, message, prefix)
    return postfix

def _write_datamodel_class(writer: IndentedWriter,
                           message: Message,
                           prefix: str,
                           shared_interface: SharedInterface = None) -> str:
    postfix = ""
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
    if shared_interface:
        for parent in shared_interface.parents:
            shared_interface_super_nonnull_variables += _get_variables(parent.root, prefix)[0]
            shared_interface_super_nullable_variables += _get_variables(parent.root, prefix)[1]

    hasId = False
    if not shared_interface:
        for variable in nonnull_variables:
            if variable.network_name == "Id" and variable.type == "String" and not variable.nullable:
                hasId = True

    if shared_interface:
        if shared_interface.is_inner:
            writer.append(f': {message.name}, {prefix.replace(".", "")}{shared_interface.name}')
        else:
            writer.append(f": {message.name}")
            if not already_implements(message, shared_interface):
                writer.append(f", {shared_interface.name}")
    elif not message.extends:
        writer.append(f": Codable")
    else:
        writer.append(f": {message.extends[0].name}")
    
    if hasId:
        writer.append(", Hashable")
    writer.append(" {")
    writer.newline()
    indented_writer = writer.indented()
    if hasId:
        indented_writer.writeln('private static let insertId = "insert"')
        indented_writer.newline()
        indented_writer.writeln("func hash(into hasher: inout Hasher) {")
        indented_writer.indented().writeln("hasher.combine(id)")
        indented_writer.writeln("}")
        indented_writer.newline()
        indented_writer.writeln(f"static func == (lhs: {message.name}Entity, rhs: {message.name}Entity) -> Bool {{")
        indented_writer.indented().writeln("return isEqual(lhs, rhs)")
        indented_writer.writeln("}")
        indented_writer.newline()
        indented_writer.writeln("class func isEqual(_ lhs: AnyObject, _ rhs: AnyObject) -> Bool {")
        indented_writer.indented().writeln(f"guard let lhs = lhs as? {message.name}Entity,")
        indented_writer.indented().indented().writeln(f"let rhs = rhs as? {message.name}Entity else {{")
        indented_writer.indented().indented().indented().writeln("return false")
        indented_writer.indented().writeln("}")
        indented_writer.indented().writeln("return lhs === rhs || (lhs.id == rhs.id && lhs.id != insertId)")
        indented_writer.writeln("}")
        indented_writer.newline()
    for inner_class in inner_classes:
        postfix += _write_datamodel_inner(indented_writer, inner_class[0], inner_class[1])

    for enum in enums:
        _write_enum(indented_writer, enum[0], enum[1])

    if shared_interface:
        for variable in shared_interface_super_nonnull_variables:
            if variable not in nonnull_variables:
                indented_writer.writeln(f"var {variable.name}: {variable.type}")

        for variable in shared_interface_super_nullable_variables:
            if variable not in nullable_variables:
                indented_writer.writeln(f"var {variable.name}: {variable.type}")

        for variable in shared_interface.variables:
            indented_writer.writeln(f"var {variable.name}: {variable.type}")
                
    else:
        for variable in nonnull_variables:
            indented_writer.writeln(f"var {variable.name}: {variable.type}")

        for variable in nullable_variables:
            indented_writer.writeln(f"var {variable.name}: {variable.type}")

        for variable in super_interface_nonnull_variables:
            if variable not in nonnull_variables:
                indented_writer.writeln(f"var {variable.name}: {variable.type}")
        
        for variable in super_interface_nullable_variables:
            if variable not in nullable_variables:
                indented_writer.writeln(f"var {variable.name}: {variable.type}")


    writer.newline()
    
    own_nonnull_variables = False
    for variable in nonnull_variables:
        if not (variable in super_variables) and not (variable in shared_interface_super_nonnull_variables) and not shared_interface:
            own_nonnull_variables = True

    own_nullable_variables = False
    for variable in nullable_variables:
        if not variable in shared_interface_super_nullable_variables:
            own_nullable_variables = True

    constructor_vars = []
    member_vars = []

    init_elements = []
    for variable in super_variables:
        init_elements.append(f'{variable.name}: {variable.type}')
        constructor_vars.append(variable)
    for variable in super_interface_nonnull_variables:
        if variable in shared_interface_super_nonnull_variables + nonnull_variables:
            continue
        if shared_interface:
            init_elements.append(f'{variable.name}: {variable.type}')
        else:
            init_elements.append(f'{variable.name}: {variable.type}')
        constructor_vars.append(variable)
    for variable in nonnull_variables:
        if shared_interface:
            init_elements.append(f'{variable.name}: {variable.type}')
        else:
            init_elements.append(f'{variable.name}: {variable.type}')
        constructor_vars.append(variable)
    if shared_interface:                
        for variable in shared_interface.variables:
            init_elements.append(f'{variable.name}: {variable.type}')
            constructor_vars.append(variable)
    for variable in shared_interface_super_nonnull_variables:
        if variable in nonnull_variables:
            continue
        init_elements.append(f'{variable.name}: {variable.type}')
        constructor_vars.append(variable)

    # init
    if own_nonnull_variables or own_nullable_variables:
        if super_variables or nonnull_variables or super_interface_nonnull_variables or shared_interface or shared_interface_super_nonnull_variables or shared_interface_super_nullable_variables:
            # if we have a super and no additional vars then we should use override
            #if (super_variables and not (own_nonnull_variables)) or (shared_interface_super_nonnull_variables and not (own_nonnull_variables)):
            if (super_variables or (nonnull_variables and shared_interface and not shared_interface.variables)) and not (own_nonnull_variables):
                indented_writer.write(f"override init(")
            else:
                indented_writer.write(f"init(")
            

            indented_writer.append(", ".join(init_elements))

            indented_writer.appendln(") {")

            init_writer = indented_writer.indented()
            
            if (super_interface_nonnull_variables):
                for variable in super_interface_nonnull_variables:
                    if variable in shared_interface_super_nonnull_variables + nonnull_variables:
                        continue
                    if shared_interface:
                        init_writer.writeln(f'self.{variable.name} = {variable.name}')
                    else:
                        init_writer.writeln(f'self.{variable.name} = {variable.name}')
                    member_vars.append(variable)

            if (shared_interface):
                for variable in shared_interface.variables:
                    init_writer.writeln(f'self.{variable.name} = {variable.name}')

            if (shared_interface_super_nonnull_variables):
                for variable in shared_interface_super_nonnull_variables:
                    if variable in nonnull_variables:
                        continue
                    init_writer.writeln(f'self.{variable.name} = {variable.name}')
                    member_vars.append(variable)

            if (nonnull_variables):
                if shared_interface:
                    init_elements = []
                    init_writer.write('super.init(')
                    for variable in nonnull_variables:
                        init_elements.append(f'{variable.name}: {variable.name}')
                    init_writer.append(", ".join(init_elements))
                    init_writer.appendln(')')
                else:
                    for variable in nonnull_variables:
                        init_writer.writeln(f'self.{variable.name} = {variable.name}')
                        # member_vars.append(variable)
            
            if (super_variables):
                init_elements = []
                init_writer.write('super.init(')
                for variable in super_variables:
                    init_elements.append(f'{variable.name}: {variable.name}')
                init_writer.append(", ".join(init_elements))
                init_writer.appendln(')')
                

            indented_writer.writeln("}")
        elif not message.extends:
            writer.newline()
            writer.indented().writeln("init() { }")

    if own_nonnull_variables or own_nullable_variables:
        _write_coding(writer.indented(), message, prefix, shared_interface)


    ## write Entity functions
    #logic_type = f"{prefix}{shared_interface.name}{message.name}" if shared_interface else f"{prefix[:-1]}"
    #indented_writer.writeln(f"private var original: {logic_type}? = nil")
    #indented_writer.newline()
    #if message.extends or shared_interface:
    #    indented_writer.write("override ")
    #else:
    #    indented_writer.write("")
    #indented_writer.appendln("func saveOriginal() {")
    #indented_writer.indented().writeln(f"original = (copy() as? {logic_type})")
    #indented_writer.writeln("}")
    #indented_writer.newline()
    #if message.extends or shared_interface:
    #    indented_writer.write("override ")
    #else:
    #    indented_writer.write("")
    #indented_writer.appendln(f"func copy() -> Entity {{")
    #indented_writer.indented().write(f"let copy = {logic_type}(")
    #items = []
    #for variable in constructor_vars:
    #    items.append(f"{variable.name}: {variable.name}{f'.map {{ $0.copy() as! {variable.type[1:-1]} }}' if variable.name.endswith('List') else ''}{'' if variable.primitive or variable.name.endswith('List') else ('.copy() as! ' + variable.type)}")
    #indented_writer.append(", ".join(items))
    #indented_writer.appendln(")")
    #indented_writer.indented().writeln(f"copy.copyNullableVariables(from: self as! {logic_type})")
    #indented_writer.indented().writeln(f"return copy")
    #indented_writer.writeln("}")
    #indented_writer.newline()
    #indented_writer.writeln(f"func copyNullableVariables(from: {logic_type}) {{")
    #if message.extends or shared_interface:
    #    indented_writer.indented().writeln(f"super.copyNullableVariables(from: from)")
    #for variable in member_vars:
    #    if variable.primitive:
    #        indented_writer.indented().writeln(f"{variable.name} = from.{variable.name}")
    #    else:
    #        if variable.name.endswith("List"):
    #            if variable.nullable:
    #                indented_writer.indented().writeln(f"{variable.name} = from.{variable.name}?.map {{ $0.copy() }}")
    #            else:
    #                indented_writer.indented().writeln(f"{variable.name} = from.{variable.name}.map {{ $0.copy() }}")
    #        else:
    #            indented_writer.indented().writeln(f"{variable.name} = from.{variable.name}{'?' if variable.nullable else ''}.copy()")
    #indented_writer.writeln("}")
    #indented_writer.newline()
    
    #if message.extends or shared_interface:
    #    indented_writer.write("override ")
    #else:
    #    indented_writer.write("")
    #indented_writer.appendln(f"func deepEquals(other: Entity?) -> Bool {{")

    #if message.extends:
    #    indented_writer.indented().writeln(f"if (!super.deepEquals(other: other)) {{")
    #    indented_writer.indented().indented().writeln("return false")
    #    indented_writer.indented().writeln("}")
    ## 
    #indented_writer.indented().writeln(f"if let other = (other as? {logic_type}) {{")
    #indented_writer.indented().indented().writeln(f"return true")
    #for variable in (constructor_vars + member_vars):
    #    if variable.primitive:
    #        indented_writer.indented().indented().indented().writeln(f"&& {variable.name} == other.{variable.name}")
    #    else:
    #        if variable.name.endswith("List"):
    #            indented_writer.indented().indented().indented().writeln(f"&& {f'if ({variable.name} == null || other.{variable.name} == null) {variable.name} == other.{variable.name} else' if variable.nullable else ''} self.{variable.name}.count == other.{variable.name}.count && zip({variable.name}, other.{variable.name}).allSatisfy {{ $0.0.deepEquals(other: $0.1) }}")
    #        else:
    #            indented_writer.indented().indented().indented().writeln(f"&& {f'if ({variable.name} == null) other.{variable.name} == null else {variable.name}?' if variable.nullable else variable.name}.deepEquals(other: other.{variable.name}){' == true' if variable.nullable else ''}")
    #indented_writer.indented().writeln("} else {")
    #indented_writer.indented().indented().writeln("return false")
    #indented_writer.indented().writeln("}")
    #indented_writer.writeln("}")
    #indented_writer.newline()
    #if message.extends or shared_interface:
    #    indented_writer.write("override ")
    #else:
    #    indented_writer.write("")
    #indented_writer.appendln(f"func hasChanged() -> Bool {{")
    #indented_writer.indented().writeln(f"return !deepEquals(other: original)")
    #indented_writer.writeln("}")

    #indented_writer.newline()
    #if message.extends or shared_interface:
    #    indented_writer.write("override ")
    #else:
    #    indented_writer.write("")
    #indented_writer.appendln(f"func toOriginal() -> Entity {{")
    #indented_writer.indented().writeln(f"let result = original")
    #indented_writer.indented().writeln(f"original?.saveOriginal()")
    #indented_writer.indented().writeln(f"return result!")
    #indented_writer.writeln("}")

    writer.writeln("}")
    writer.newline()
    return postfix


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
                    f'case {variable.name} = "{variable.network_name}"')

            for variable in nullable_variables:
                writer.indented().writeln(
                    f'case {variable.name} = "{variable.network_name}"')

        for variable in shared_interface_super_nonnull_variables:
            if variable not in nonnull_variables:
                writer.indented().writeln(
                    f'case {variable.name} = "{variable.network_name}"')

        for variable in shared_interface_super_nullable_variables:
            if variable not in nullable_variables:
                writer.indented().writeln(
                    f'case {variable.name} = "{variable.network_name}"')

        for variable in super_interface_nonnull_variables:
            if variable not in nonnull_variables:
                writer.indented().writeln(
                    f'case {variable.name} = "{variable.network_name}"')

        for variable in super_interface_nullable_variables:
            if variable not in nullable_variables:
                writer.indented().writeln(
                    f'case {variable.name} = "{variable.network_name}"')
        
        writer.indented().writeln(
                f'case entityType = "__type__"')

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
                if variable.message and len(variable.message.extends) > 1:
                    codingPrefix = prefix + variable.message.name
                    # TODO this piece is not only for nonnull_variables                    
                    indented_writer.writeln(f"var {variable.name}NestedUnkeyedContainer = try container.nestedUnkeyedContainer(forKey: .{variable.name})")
                    indented_writer.writeln(f"var {variable.name}TmpNestedUnkeyedContainer = {variable.name}NestedUnkeyedContainer")
                    if variable.type[0] == '[':
                        indented_writer.writeln(f"var {variable.name} = {variable.type}()")
                        indented_writer.writeln(f"while !{variable.name}NestedUnkeyedContainer.isAtEnd {{")
                        indented_indented_writer.writeln(f"let typeContainer = try {variable.name}NestedUnkeyedContainer.nestedContainer(keyedBy: CodingKeys.self)")
                        indented_indented_writer.writeln("let type = try typeContainer.decode(String.self, forKey: .entityType)")
                        indented_indented_writer.writeln("switch type {")
                        for extends in variable.message.extends:
                            indented_indented_writer.indented().writeln(f'case "{pathlib.Path(*extends.path.parts[1:])}":')
                            indented_indented_indented_writer.indented().writeln(f"{variable.name}.append(try {variable.name}TmpNestedUnkeyedContainer.decode({codingPrefix}{extends.name}.self))")
                        indented_indented_writer.indented().writeln(f"default:")
                        indented_indented_indented_writer.indented().writeln(f'fatalError("should not happen")')
                        indented_indented_writer.writeln("}")
                        indented_writer.writeln("}")
                        indented_writer.writeln(f"self.{variable.name} = {variable.name}")
                    else:
                        indented_writer.writeln(f"let typeContainer = try {variable.name}NestedUnkeyedContainer.nestedContainer(keyedBy: CodingKeys.self)")
                        indented_writer.writeln("let type = try typeContainer.decode(String.self, forKey: .entityType)")
                        indented_writer.writeln("switch type {")
                        for extends in variable.message.extends:
                            indented_indented_writer.writeln(f'case "{pathlib.Path(*extends.path.parts[1:])}":')
                            indented_indented_indented_writer.writeln(f"self.{variable.name} = (try {variable.name}TmpNestedUnkeyedContainer.decode({codingPrefix}{extends.name}.self))")
                        indented_indented_writer.writeln(f"default:")
                        indented_indented_indented_writer.writeln(f'fatalError("should not happen")')
                        indented_writer.writeln("}")
                else:
                    writer.indented().writeln(f'{variable.name} = try container.decode({variable.type}.self, forKey: .{variable.name})')

            for variable in nullable_variables:
                if variable.message and len(variable.message.extends) > 1:
                    codingPrefix = prefix + variable.message.name
                    # TODO this piece is not only for nonnull_variables                    
                    indented_writer.writeln(f"var {variable.name}NestedUnkeyedContainer = try container.nestedUnkeyedContainer(forKey: .{variable.name})")
                    indented_writer.writeln(f"var {variable.name}TmpNestedUnkeyedContainer = {variable.name}NestedUnkeyedContainer")
                    if variable.type[0] == '[':
                        indented_writer.writeln(f"var {variable.name} = {variable.type}()")
                        indented_writer.writeln(f"while !{variable.name}NestedUnkeyedContainer.isAtEnd {{")
                        indented_indented_writer.writeln(f"let typeContainer = try {variable.name}NestedUnkeyedContainer.nestedContainer(keyedBy: CodingKeys.self)")
                        indented_indented_writer.writeln("let type = try typeContainer.decodeIfPresent(String.self, forKey: .entityType)")
                        indented_indented_writer.writeln("switch type {")
                        for extends in variable.message.extends:
                            indented_indented_writer.indented().writeln(f'case "{pathlib.Path(*extends.path.parts[1:])}":')
                            indented_indented_indented_writer.indented().writeln(f"{variable.name}.append(try {variable.name}TmpNestedUnkeyedContainer.decodeIfPresent({codingPrefix}{extends.name}.self))")
                        indented_indented_writer.indented().writeln(f"default:")
                        indented_indented_indented_writer.indented().writeln(f'break')
                        indented_indented_writer.writeln("}")
                        indented_writer.writeln("}")
                        indented_writer.writeln(f"self.{variable.name} = {variable.name}")
                    else:
                        indented_writer.writeln(f"let typeContainer = try {variable.name}NestedUnkeyedContainer.nestedContainer(keyedBy: CodingKeys.self)")
                        indented_writer.writeln("let type = try typeContainer.decodeIfPresent(String.self, forKey: .entityType)")
                        indented_writer.writeln("switch type {")
                        for extends in variable.message.extends:
                            indented_indented_writer.writeln(f'case "{pathlib.Path(*extends.path.parts[1:])}":')
                            indented_indented_indented_writer.writeln(f"self.{variable.name} = (try {variable.name}TmpNestedUnkeyedContainer.decodeIfPresent({codingPrefix}{extends.name}.self))")
                        indented_indented_writer.writeln(f"default:")
                        indented_indented_indented_writer.writeln(f'break')
                        indented_writer.writeln("}")
                else:
                    writer.indented().writeln(f'{variable.name} = try container.decodeIfPresent({variable.type[:-1]}.self, forKey: .{variable.name})')

        for variable in shared_interface_super_nonnull_variables:
            if variable not in nonnull_variables:
                writer.indented().writeln(f'{variable.name} = try container.decode({variable.type}.self, forKey: .{variable.name})')

        for variable in shared_interface_super_nullable_variables:
            if variable not in nullable_variables:
                writer.indented().writeln(f'{variable.name} = try container.decodeIfPresent({variable.type[:-1]}.self, forKey: .{variable.name})')

        for variable in super_interface_nonnull_variables:
            if variable not in nonnull_variables:
                writer.indented().writeln(f'{variable.name} = try container.decode({variable.type}.self, forKey: .{variable.name})')

        for variable in super_interface_nullable_variables:
            if variable not in nullable_variables:
                writer.indented().writeln(f'{variable.name} = try container.decodeIfPresent({variable.type[:-1]}.self, forKey: .{variable.name})')


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
                if variable.message and len(variable.message.extends) > 1:
                    codingPrefix = prefix + variable.message.name
                    # TODO this piece is not only for nonnull_variables
                    indented_writer.writeln(f"var {variable.name}Container = container.nestedUnkeyedContainer(forKey: .{variable.name})")
                    if variable.type[0] == '[':
                        indented_writer.writeln(f"for element in {variable.name} {{")
                        indented_indented_writer.writeln(f"var typeContainer = {variable.name}Container.nestedContainer(keyedBy: CodingKeys.self)")
                        indented_indented_writer.writeln("switch element {")
                        for extends in variable.message.extends:
                            indented_indented_writer.indented().writeln(f"case let {camelcase(extends.name)} as {codingPrefix}{extends.name}:")
                            indented_indented_indented_writer.indented().writeln(f'try typeContainer.encode("{pathlib.Path(*extends.path.parts[1:])}", forKey: .entityType)')
                            indented_indented_indented_writer.indented().writeln(f"try {variable.name}Container.encode({camelcase(extends.name)})")
                        indented_indented_writer.indented().writeln(f"default:")
                        indented_indented_indented_writer.indented().writeln(f'fatalError("should not happen")')
                        indented_indented_writer.writeln("}")
                        indented_writer.writeln("}")
                    else:                        
                        indented_writer.writeln(f"var typeContainer = {variable.name}Container.nestedContainer(keyedBy: CodingKeys.self)")
                        indented_writer.writeln(f"switch {variable.name} {{")
                        for extends in variable.message.extends:
                            indented_indented_writer.writeln(f"case let {camelcase(extends.name)} as {codingPrefix}{extends.name}:")
                            indented_indented_indented_writer.writeln(f'try typeContainer.encode("{pathlib.Path(*extends.path.parts[1:])}", forKey: .entityType)')
                            indented_indented_indented_writer.writeln(f"try {variable.name}Container.encode({camelcase(extends.name)})")
                        indented_indented_writer.writeln(f"default:")
                        indented_indented_indented_writer.writeln(f'fatalError("should not happen")')
                        indented_writer.writeln("}")
                else:
                    writer.indented().writeln(f'try container.encode({variable.name}, forKey: .{variable.name})')

            for variable in nullable_variables:
                if variable.message and len(variable.message.extends) > 1:
                    codingPrefix = prefix + variable.message.name
                    # TODO this piece is not only for nonnull_variables
                    indented_writer.writeln(f"var {variable.name}Container = container.nestedUnkeyedContainer(forKey: .{variable.name})")
                    if variable.type[0] == '[':
                        indented_writer.writeln(f"for element in {variable.name} {{")
                        indented_indented_writer.writeln(f"var typeContainer = {variable.name}Container.nestedContainer(keyedBy: CodingKeys.self)")
                        indented_indented_writer.writeln("switch element {")
                        for extends in variable.message.extends:
                            indented_indented_writer.indented().writeln(f"case let {camelcase(extends.name)} as {codingPrefix}{extends.name}:")
                            indented_indented_indented_writer.indented().writeln(f'try typeContainer.encode("{pathlib.Path(*extends.path.parts[1:])}", forKey: .entityType)')
                            indented_indented_indented_writer.indented().writeln(f"try {variable.name}Container.encode({camelcase(extends.name)})")
                        indented_indented_writer.indented().writeln(f"default:")
                        indented_indented_indented_writer.indented().writeln(f'break')
                        indented_indented_writer.writeln("}")
                        indented_writer.writeln("}")
                    else:                        
                        indented_writer.writeln(f"var typeContainer = {variable.name}Container.nestedContainer(keyedBy: CodingKeys.self)")
                        indented_writer.writeln(f"switch {variable.name} {{")
                        for extends in variable.message.extends:
                            indented_indented_writer.writeln(f"case let {camelcase(extends.name)} as {codingPrefix}{extends.name}:")
                            indented_indented_indented_writer.writeln(f'try typeContainer.encode("{pathlib.Path(*extends.path.parts[1:])}", forKey: .entityType)')
                            indented_indented_indented_writer.writeln(f"try {variable.name}Container.encode({camelcase(extends.name)})")
                        indented_indented_writer.writeln(f"default:")
                        indented_indented_indented_writer.writeln(f'break')
                        indented_writer.writeln("}")
                else:
                    writer.indented().writeln(f'try container.encode({variable.name}, forKey: .{variable.name})')

        for variable in shared_interface_super_nonnull_variables:
            if variable not in nonnull_variables:
                writer.indented().writeln(f'try container.encode({variable.name}, forKey: .{variable.name})')

        for variable in shared_interface_super_nullable_variables:
            if variable not in nullable_variables:
                writer.indented().writeln(f'try container.encode({variable.name}, forKey: .{variable.name})')

        for variable in super_interface_nonnull_variables:
            if variable not in nonnull_variables:
                writer.indented().writeln(f'try container.encode({variable.name}, forKey: .{variable.name})')

        for variable in super_interface_nullable_variables:
            if variable not in nullable_variables:
                writer.indented().writeln(f'try container.encode({variable.name}, forKey: .{variable.name})')

    writer.writeln("}")

    writer.newline()


def _write_enum(writer: IndentedWriter, name: str,
                cases: List[str]) -> None:
    writer.writeln(
        f"enum {'`Type`' if name == 'Type' else name}: String, Codable, CaseIterable, CaseOrderComparable {{")
    for case in cases:
        case_name = _to_case(case)
        value = case

        if case_name != value:
            writer.indented().writeln(f'case {_to_case(case)} = "{case}"')
        else:
            writer.indented().writeln(f'case {_to_case(case)}')

    writer.writeln("}")


def _write_logic(writer: IndentedWriter, entity: Entity) -> None:
    writer.writeln("import Foundation")
    writer.newline()
    postfix = _write_logic_inner(writer, entity.root, "")
    
    writer.newline()
    writer.writeln(postfix)

def _write_logic_inner(writer: IndentedWriter, message: Message, prefix: str) -> str:
    postfix = ""
    if len(message.extends) > 1:
        shared_interface = _get_shared_interface(message, prefix)
        postfix += f"protocol {prefix}{message.name}: {prefix}{message.name}Entity {{\n"
        indented_writer = writer.indented()
        postfix += "}\n"
        postfix += "\n"
        for extends in message.extends:
            postfix += _write_logic_class(writer, extends.root, shared_interface, prefix)
            postfix += "\n"
    else:
        postfix += _write_logic_class(writer, message, None, prefix)
    return postfix


def _write_logic_class(writer: IndentedWriter, message: Message, shared_interface: SharedInterface, prefix: str) -> str:
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
                constructor_elements.append(f'{constructor_parameter.name}: {constructor_parameter.type}')
        for variable in shared_interface.variables:
            if constructor_parameter not in super_nonnull_variables:
                constructor_elements.append(f"{variable.name}: {variable.type}")
        if shared_interface:
            for variable in shared_interface.variables:
                if variable not in super_nonnull_variables:
                    constructor_elements.append(f'{variable.name}: {variable.type}')
        indented_writer.writeln(f'convenience init({", ".join(constructor_elements)}) {{')
        super_elements = []
        
        for constructor_parameter in super_nonnull_variables:
            name = constructor_parameter.name
            super_elements.append(f'{name}: {camelcase(message.name)}.{name}')
        for constructor_parameter in shared_interface_super_nonnull_variables:
            if constructor_parameter not in super_nonnull_variables:
                name = constructor_parameter.name
                super_elements.append(f'{name}: {name}')
        if shared_interface:
            for variable in shared_interface.variables:
                if variable not in super_nonnull_variables:
                    super_elements.append(f'{variable.name}: {variable.name}')
        constructor_writer.writeln(f'self.init({", ".join(super_elements)})')
        indented_writer.writeln("}")
        

    writer.writeln("}")
    return postfix


def _write_service(writer: IndentedWriter, entity: Entity) -> None:
    writer.writeln(f"import Alamofire")
    writer.writeln(f"import SendratoAppSDK")
    writer.newline()
    writer.writeln(f"private enum {entity.name}Service {{")

    indented_writer = writer.indented(indent=2)

    indented_writer.writeln(f'static let path = "/{entity.path}"')
    indented_writer.writeln(f'static let version = {max(entity.version, 0)}')
    indented_writer.writeln(f"static let headers = HTTPHeaders([")
    indented_writer.indented(indent=2).writeln(
        '"X-Navajo-Entity-Version": String(version)'
    )
    indented_writer.writeln("])")
    writer.writeln("}")

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
                _write_service_get(writer, entity, parameters,
                                   properties, required_properties,
                                   optional_properties)
            if method == "PUT":
                _write_service_put(writer, entity, parameters,
                                   properties, required_properties,
                                   optional_properties)
            if method == "POST":
                _write_service_post(writer, entity, parameters,
                                    properties, required_properties,
                                    optional_properties)
            if method == "DELETE":
                _write_service_delete(writer, entity, parameters,
                                      properties, required_properties,
                                      optional_properties)

            if j != len(entity.key_ids) - 1:
                writer.newline()

        if not entity.key_ids:
            if method == "GET":
                _write_service_get(writer, entity)
            if method == "PUT":
                _write_service_put(writer, entity)
            if method == "POST":
                _write_service_post(writer, entity)
            if method == "DELETE":
                _write_service_delete(writer, entity)

        if i != len(entity.methods) - 1:
            writer.newline()

    # writer.writeln("}")


def _write_service_get(writer: IndentedWriter,
                       entity: Entity,
                       parameters: List[str] = [],
                       properties: List[Property] = [],
                       required_properties: List[Property] = [],
                       optional_properties: List[Property] = []) -> None:
    writer.writeln(
        f"extension Service where ResponseSerializer == DecodableResponseSerializer<{entity.name}> {{"
    )

    indented_writer = writer.indented(indent=2)
    indented_writer.writeln(f"static func {camelcase(entity.name)}({', '.join(parameters)}) -> Self {{")

    method_writer = indented_writer.indented(indent=2)
    method_writer.writeln(".init(")
    method_writer.indented(indent=2).writeln(f"path: {entity.name}Service.path,")
    method_writer.indented(indent=2).writeln(f"headers: {entity.name}Service.headers,")
    if parameters:
        method_writer.indented(indent=2).writeln(f"requestModifier: .parameters([")
        for property in required_properties + optional_properties:
            method_writer.indented(indent=4).writeln(f'"{property.name}": {_variable_name(property.name)},')
        method_writer.indented(indent=2).writeln(f"]),")
    method_writer.indented(indent=2).writeln(f"responseSerializer: .decodable(of: {entity.name}.self)")
    method_writer.writeln(")")

    indented_writer.writeln(f"}}")

    writer.writeln(f"}}")

def _write_service_put(writer: IndentedWriter,
                       entity: Entity,
                       parameters: List[str] = [],
                       properties: List[Property] = [],
                       required_properties: List[Property] = [],
                       optional_properties: List[Property] = []) -> None:
    writer.writeln(
        f"extension Service where ResponseSerializer == DecodableResponseSerializer<{entity.name}> {{"
    )

    indented_writer = writer.indented(indent=2)
    indented_writer.writeln(
        f"static func update(_ {_variable_name(entity.name)}: {entity.name}) -> Self {{"
    )

    method_writer = indented_writer.indented(indent=2)
    method_writer.writeln(".init(")
    method_writer.indented(indent=2).writeln(f"path: {entity.name}Service.path,")
    method_writer.indented(indent=2).writeln(f"method: .put,")
    method_writer.indented(indent=2).writeln(f"headers: {entity.name}Service.headers,")
    if parameters:
        method_writer.indented(indent=2).writeln(f"requestModifier: .multi(")
        method_writer.indented(indent=4).writeln(f".parameters([")
        for property in required_properties + optional_properties:
            method_writer.indented(indent=6).writeln(f'"{property.name}": {_variable_name(entity.name)}.{_variable_name(property.name)},')
        method_writer.indented(indent=4).writeln(f"]),")
        method_writer.indented(indent=4).writeln(f".encode({_variable_name(entity.name)})")
        method_writer.indented(indent=2).writeln(f"),")
    else:
        method_writer.indented(indent=2).writeln(f"requestModifier: .encode({_variable_name(entity.name)}),")
    method_writer.indented(indent=2).writeln(f"responseSerializer: .decodable(of: {entity.name}.self)")
    method_writer.writeln(")")
    indented_writer.writeln("}")

    writer.writeln(f"}}")


def _write_service_post(writer: IndentedWriter,
                        entity: Entity,
                        parameters: List[str] = [],
                        properties: List[Property] = [],
                        required_properties: List[Property] = [],
                        optional_properties: List[Property] = []) -> None:
    writer.writeln(
        f"extension Service where ResponseSerializer == DecodableResponseSerializer<{entity.name}> {{"
    )

    indented_writer = writer.indented(indent=2)
    indented_writer.writeln(
        f"static func insert(_ {_variable_name(entity.name)}: {entity.name}) -> Self {{"
    )

    method_writer = indented_writer.indented(indent=2)
    method_writer.writeln(".init(")
    method_writer.indented(indent=2).writeln(f"path: {entity.name}Service.path,")
    method_writer.indented(indent=2).writeln(f"method: .post,")
    method_writer.indented(indent=2).writeln(f"headers: {entity.name}Service.headers,")
    if parameters:
        method_writer.indented(indent=2).writeln(f"requestModifier: .multi(")
        method_writer.indented(indent=4).writeln(f".parameters([")
        for property in required_properties + optional_properties:
            method_writer.indented(indent=6).writeln(f'"{property.name}": {_variable_name(entity.name)}.{_variable_name(property.name)},')
        method_writer.indented(indent=4).writeln(f"]),")
        method_writer.indented(indent=4).writeln(f".encode({_variable_name(entity.name)})")
        method_writer.indented(indent=2).writeln(f"),")
    else:
        method_writer.indented(indent=2).writeln(f"requestModifier: .encode({_variable_name(entity.name)}),")
    method_writer.indented(indent=2).writeln(f"responseSerializer: .decodable(of: {entity.name}.self)")
    method_writer.writeln(")")
    indented_writer.writeln("}")

    writer.writeln(f"}}")


def _write_service_delete(writer: IndentedWriter,
                          entity: Entity,
                          parameters: List[str] = [],
                          properties: List[Property] = [],
                          required_properties: List[Property] = [],
                          optional_properties: List[Property] = []) -> None:
    writer.writeln(
        f"extension Service where ResponseSerializer == DecodableResponseSerializer<{entity.name}> {{"
    )

    indented_writer = writer.indented(indent=2)
    indented_writer.writeln(
        f"static func delete({', '.join(parameters)}) -> Self {{"
    )

    method_writer = indented_writer.indented(indent=2)
    method_writer.writeln(".init(")
    method_writer.indented(indent=2).writeln(f"path: {entity.name}Service.path,")
    method_writer.indented(indent=2).writeln(f"method: .delete,")
    method_writer.indented(indent=2).writeln(f"headers: {entity.name}Service.headers,")
    method_writer.indented(indent=2).writeln(f"requestModifier: .parameters([")
    for property in required_properties + optional_properties:
        method_writer.indented(indent=4).writeln(f'"{property.name}": {_variable_name(property.name)},')
    method_writer.indented(indent=2).writeln(f"]),")
    method_writer.indented(indent=2).writeln(f"responseSerializer: .decodable(of: {entity.name}.self)")
    method_writer.writeln(")")
    indented_writer.writeln("}")

    writer.writeln(f"}}")

def _get_shared_interface(message: Message, prefix: str) -> SharedInterface:
    variables = []
    enums = []

    for property in message.properties:
        if property.method == "request":
            continue

        type = property.type
        name = property.name
        variable_name = camelcase(name)
        variable_type = _swift_type(type)
        nullable = property.nullable

        if property.enum:
            variable_type = (prefix + message.name + "Entity" + name).replace(".", "")
            enum_options = []
            for enum_value in property.enum:
                enum_options.append(enum_value)
            enums.append((name, enum_options))
        if nullable:
            variable_type += "?"
        variables.append(Variable(name, variable_name, variable_type, True, nullable, None))

    for submessage in message.messages:
        name = submessage.name
        nullable = submessage.nullable

        if submessage.is_array:
            if not submessage.extends or (len(submessage.extends) == 1 and (submessage.properties or submessage.messages)):
                variable_type = "[" + submessage.name + "]"
            elif len(submessage.extends) == 1:
                variable_type = "[" + submessage.extends[0].name + "]"
            else:
                variable_type = "[" + submessage.name + "]"
            variable_name = camelcase(name) + "List"
        else:
            if not submessage.extends or (len(submessage.extends) == 1 and (submessage.properties or submessage.messages)):
                variable_type = submessage.name
            elif len(submessage.extends) == 1:
                variable_type = submessage.extends[0].name
            else:
                variable_type = submessage.name
            variable_name = camelcase(name)

        if nullable:
            variable_type += "?"
        variables.append(Variable(name, variable_name, variable_type, False, nullable, submessage))
    return SharedInterface(message.name, variables, [], enums)

def _get_variables(message: Message, prefix: str, recursive: bool = False):
    nonnull_variables = []
    nullable_variables = []
    enums = []
    inner_classes = [] 

    for property in message.properties:
        if property.method == "request":
            continue

        type = property.type
        name = property.name
        variable_name = camelcase(name)
        variable_type = _swift_type(type)
        variable_type_primitive = True
        nullable = property.nullable

        if property.enum:
            enum_options = []
            for enum_value in property.enum:
                enum_options.append(enum_value)
            enums.append((name, enum_options))
            variable_type = name
        if nullable:
            variable_type += "?"
            nullable_variables.append(Variable(name, variable_name, variable_type, variable_type_primitive, nullable, None))
        else:
            nonnull_variables.append(Variable(name, variable_name, variable_type, variable_type_primitive, nullable, None))

    for submessage in message.messages:
        name = submessage.name
        nullable = submessage.nullable
        variable_type_primitive = False
        if submessage.is_array:
            if not submessage.extends or (len(submessage.extends) == 1 and (submessage.properties or submessage.messages)):
                # inner class
                inner_classes.append((submessage, prefix))
                variable_type = ("[" + prefix + name + "]")
            elif len(submessage.extends) == 1:
                # external class
                variable_type = "[" + submessage.extends[0].name + "]"
            else:
                inner_classes.append((submessage, prefix))
                variable_type = ("[" + prefix + submessage.name + "]").replace(".", "")
            variable_name = camelcase(name) + "List"
        else:
            if not submessage.extends or (len(submessage.extends) == 1 and (submessage.properties or submessage.messages)):
                inner_classes.append((submessage, prefix))
                variable_type = (prefix + name)
            elif len(submessage.extends) == 1:
                variable_type = submessage.extends[0].name
            else:
                inner_classes.append((submessage, prefix))
                variable_type = (prefix + submessage.name).replace(".", "")
            variable_name = camelcase(name)

        if nullable:
            variable_type += "?"
            nullable_variables.append(Variable(name, variable_name, variable_type, variable_type_primitive, nullable, submessage))
        else:
            nonnull_variables.append(Variable(name, variable_name, variable_type, variable_type_primitive, nullable, submessage))
    
    if recursive:
        if len(message.extends) == 1:
            result = _get_variables(message.extends[0].root, prefix, recursive)
            nonnull_variables = result[0] + nonnull_variables
            nullable_variables += result[1] + nullable_variables
            enums += result[2]
            inner_classes += result[3]

    return nonnull_variables, nullable_variables, enums, inner_classes

# dependencies of an entity
# - the direct parent logic file (for extends) "A extends B"

# - the logic file itself (in case of inner classes)
#   - parent logic files of inner classes

# - all (in)direct top level nonnull messages that extend an entity and keep same name (for constructor) A(X x){super(x)}
def _get_constructor_dependencies(entity: Entity):
    dependencies = []
    if len(entity.root.extends) == 1:
        dependencies += _get_constructor_dependencies(entity.root.extends[0])

    for message in entity.root.messages:
        if message.nullable:
            continue
        if len(message.extends) == 1:
            if message.is_non_empty:
                dependencies.append(entity)
            else:
                dependencies.append(message.extends[0])
        elif len(message.extends) > 1:
            shared_interface = _get_shared_interface(entity.root, '')
            for parent in shared_interface.parents:
                dependencies.add(parent)
        else:
            dependencies.append(entity)
    return dependencies

def _get_variable_dependencies(entity: Entity, root: Message, logic: bool = False):
    dependencies = []
    for message in root.messages:
        if message.nullable and logic:
            continue
        
        if message.extends:
            for extends in message.extends:
                if message.is_non_empty:
                    # we will have an inner class for this variable
                    dependencies.append(extends)
                    dependencies.append(entity)
                else:                    
                    dependencies.append(extends)
                dependencies += _get_constructor_dependencies(extends)
            if len(message.extends) > 1:
                dependencies.append(entity)
        else:
            # we will have an inner class for this variable
            if not logic:
                dependencies.append(entity)
        for submessage in message.messages:
            if submessage.nullable and logic:
                continue
            if submessage.extends:
                for extends in submessage.extends:
                    dependencies.append(extends)
                    if extends.name != submessage.name and submessage.is_non_empty:
                        dependencies += _get_variable_dependencies(extends, extends.root, logic)
                        dependencies += _get_variable_dependencies(extends, submessage, logic)
                if len(submessage.extends) > 1:
                    dependencies.append(entity)
            else:
                dependencies += _get_variable_dependencies(entity, submessage, logic)
    return dependencies


def _get_dependencies(entity: Entity, logic: bool = False):
    dependencies = []
    if entity.root.extends:
        for extends in entity.root.extends:
            dependencies.append(extends)
            dependencies += _get_constructor_dependencies(extends)

    dependencies += _get_variable_dependencies(entity, entity.root, logic)

    return dependencies


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

def already_implements(message: Message, interface: SharedInterface) -> bool:
    if not message.extends:
        return False
    else:
        return already_implements(message.extends[0].root, interface)


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
