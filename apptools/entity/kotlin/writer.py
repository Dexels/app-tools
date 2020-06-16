import pathlib

from typing import List, Dict, Any, Tuple

from apptools.entity.navajo import Entity, Message
from apptools.entity.io import IndentedWriter
from apptools.entity.text import camelcase


def write(entities: List[Entity], options: Dict[str, Any]) -> None:
    output = options["output"]
    package = _package(output, start="com")

    for entity in entities:
        _write_entity(entity, output, package)


def _write_entity(entity: Entity, output: pathlib.Path, package: str) -> None:
    if entity.methods:
       service = output / entity.package / "service"
       service.mkdir(parents=True, exist_ok=True)
       service_class = service / f"{entity.name}Service.kt"
       with IndentedWriter(path=service_class) as writer:
           _write_service(writer, entity, package)

    datamodel = output / entity.package / "datamodel"
    datamodel.mkdir(parents=True, exist_ok=True)
    datamodel_class = datamodel / f"{entity.name}Entity.kt"
    with IndentedWriter(path=datamodel_class) as writer:
        _write_datamodel(writer, entity, output, package)

    # logic = output / entity.package / "logic"
    # logic.mkdir(parents=True, exist_ok=True)
    # logic_class = logic / f"{entity.name}.kt"
    # if not logic_class.exists():
    #    with IndentedWriter(path=logic_class) as writer:
    #        _write_logic(writer, entity, package)


def _write_service(writer: IndentedWriter, entity: Entity,
                   package: str) -> None:
    writer.writeln(f"package {package}.{_package(entity.package)}.service")

    writer.newline()

    dependencies: List[str] = ["retrofit2.http.Query"]

    if "GET" in entity.methods or "PUT" in entity.methods or "POST" in entity.methods or "DELETE" in entity.methods:
        dependencies.append("io.reactivex.Single")
    if entity.version != -1:
        dependencies.append("retrofit2.http.Headers")
    if "PUT" in entity.methods or "POST" in entity.methods:
        dependencies.append("retrofit2.http.Body")
    for method in entity.methods:
        dependencies.append(f"retrofit2.http.{method}")
    if "GET" in entity.methods or "PUT" in entity.methods or "POST" in entity.methods or "DELETE" in entity.methods:
        dependencies.append(
            f"{package}.{_package(entity.package)}.logic.{entity.name}")

    for dependency in sorted(dependencies):
        writer.writeln(f"import {dependency}")

    writer.newline()
    writer.writeln(f"interface {entity.name}Service {{")
    writer.newline()

    for method in entity.methods:
        indented_writer = writer.indented()

        for key_id in entity.key_ids:
            parameter_list = []
            for key_property in entity.key_properties(key_id):
                variable_name = camelcase(key_property.name)
                variable_type = _kotlin_type(key_property.type)
                if key_property.nullable:
                    variable_type += '?'
                parameter_list.append(
                    f'@Query("{key_property.name}") {variable_name}: {variable_type}'
                )
            parameters = ', '.join(parameter_list)
            if entity.version != -1:
                indented_writer.writeln(
                    f'@Headers("X-Navajo-Version: {entity.version}")')
                indented_writer.writeln(
                    f'@{method}("{entity.path}?v={entity.version}")')
            else:
                indented_writer.writeln(f'@{method}("{entity.path}")')
            if method == "GET":
                indented_writer.writeln(
                    f'fun {entity.name[0].lower() + entity.name[1:]}({parameters}): Single<{entity.name}>')
            if method == "PUT":
                indented_writer.writeln(
                    f'fun update{entity.name}({parameters}, @Body {entity.name[0].lower() + entity.name[1:]}: {entity.name}): Single<{entity.name}>'
                )
            if method == "DELETE":
                indented_writer.writeln(
                    f'fun remove{entity.name}({parameters}): Single<{entity.name}>')
            if method == "POST":
                indented_writer.writeln(
                    f'fun insert{entity.name}({parameters}, @Body {entity.name[0].lower() + entity.name[1:]}: {entity.name}): Single<{entity.name}>'
                )
            indented_writer.newline()

        if not len(entity.key_ids):
            if entity.version != -1:
                indented_writer.writeln(
                    f'@Headers("X-Navajo-Version: {entity.version}")')
                indented_writer.writeln(
                    f'@{method}("{entity.path}?v={entity.version}")')
            else:
                indented_writer.writeln(f'@{method}("{entity.path}")')
            if method == "GET":
                indented_writer.writeln(
                    f'fun {entity.name[0].lower() + entity.name[1:]}(): Single<{entity.name}> ')
            if method == "PUT":
                indented_writer.writeln(
                    f'fun update{entity.name}(@Body {entity.name[0].lower() + entity.name[1:]}: {entity.name}): Single<{entity.name}>'
                )
            if method == "DELETE":
                indented_writer.writeln(f'fun remove{entity.name}(): Single<{entity.name}>')
            if method == "POST":
                indented_writer.writeln(
                    f'fun insert{entity.name}(@Body {entity.name[0].lower() + entity.name[1:]}: {entity.name}): Single<{entity.name}>'
                )
            indented_writer.newline()

    writer.writeln("}")
    writer.newline()


def _write_datamodel(writer: IndentedWriter, entity: Entity,
                     output: pathlib.Path, package: str) -> None:
    writer.writeln(f"package {package}.{_package(entity.package)}.datamodel")

    writer.newline()

    import_list = [
        "com.google.gson.annotations.SerializedName",
        "java.io.Serializable",
        f"{package}.{_package(entity.package)}.logic." + entity.name
    ]

    for superclass in _get_superclasses(entity.root):
        import_list.append(f"{package}.{_package(superclass.package)}.logic." +
                           superclass.name)

    for import_item in sorted(set(import_list)):
        writer.writeln(f"import {import_item}")

    writer.newline()

    _write_datamodel_class(writer, entity.root)


def _write_datamodel_class(writer: IndentedWriter,
                           message: Message,
                           prefix: str = '') -> None:
    writer.append(f"open class {message.name}Entity")

    prefix += message.name + "."

    nonnull_variables = []
    nullable_variables = []
    super_variables = []
    enums = []
    inner_classes = []

    if message.extends is not None:
        super_variables = _get_super_variables(message.extends.root)

    for property in message.properties:
        if property.method == "request":
            continue

        type = property.type
        name = property.name
        variable_name = camelcase(name)
        variable_type = _kotlin_type(type)
        nullable = property.nullable

        if property.enum is not None and len(property.enum):
            enum_options = []
            for enum_value in property.enum:
                enum_options.append(enum_value)
            enums.append((name, enum_options))
            variable_type = name
        if nullable:
            variable_type += "?"
            nullable_variables.append((name, variable_name, variable_type))
        else:
            nonnull_variables.append((name, variable_name, variable_type))

    for submessage in message.messages:
        name = submessage.name
        nullable = submessage.nullable

        if submessage.is_array:
            if submessage.extends is None or (len(submessage.properties) + len(submessage.messages)):
                inner_classes.append((submessage, prefix))
                variable_type = "MutableList<" + prefix + name + ">"
            else:
                variable_type = "MutableList<" + submessage.extends.name + ">"
            variable_name = camelcase(name) + "List"
        else:
            if submessage.extends is None or (len(submessage.properties) + len(submessage.messages)):
                inner_classes.append((submessage, prefix))
                variable_type = prefix + name
            else:
                variable_type = submessage.extends.name
            variable_name = camelcase(name)

        if nullable:
            variable_type += "?"
            nullable_variables.append((name, variable_name, variable_type))
        else:
            nonnull_variables.append((name, variable_name, variable_type))

    writer.appendln("(")

    indented_writer = writer.indented()
    if (len(super_variables)):
        for variable, has_more in lookahead(super_variables):
            indented_writer.write(f'{variable[0]}: {variable[1]}')
            if has_more or len(nonnull_variables):
                writer.writeln(',')
            else:
                writer.appendln('')

    if (len(nonnull_variables)):
        for variable, has_more in lookahead(nonnull_variables):
            indented_writer.write(f'@field:JvmField @field:SerializedName("{variable[0]}") var {variable[1]}: {variable[2]}')
            if has_more:
                writer.writeln(',')
            else:
                writer.writeln('')

    if message.extends is not None:
        indented_writer.appendln(f") : {message.extends.name}(")
        if len(super_variables):
            for variable, has_more in lookahead(super_variables):
                indented_writer.write(f'{variable[0]}')
                if has_more:
                    writer.writeln(',')
                else:
                    writer.writeln('')
        indented_writer.appendln("), Serializable {")
    else:
        indented_writer.appendln(") : Serializable {")

    writer.newline()

    for inner_class in inner_classes:
        _write_datamodel_class(indented_writer, inner_class[0], inner_class[1])

    for enum in enums:
        indented_writer.writeln(f"enum class {enum[0]} {{")
        indented_writer.indented().writeln(f'{", ".join(enum[1])}')
        indented_writer.writeln(f"}}")
        writer.newline()

    for variable in nullable_variables:
        indented_writer.writeln(f"@JvmField")
        indented_writer.writeln(f'@SerializedName("{variable[0]}")')
        indented_writer.writeln(f"var {variable[1]}: {variable[2]} = null")
        writer.newline()

    writer.writeln("}")
    writer.newline()


def _write_logic(writer: IndentedWriter, entity: Entity, package: str) -> None:
    writer.writeln(f"package {package}.{_package(entity.package)}.logic")

    writer.newline()

    import_list = [
        f"{package}.{_package(entity.package)}.datamodel.{entity.name}Entity",
        f"java.io.Serializable"
    ]

    for superclass in _get_superclasses(entity.root):
        import_list.append(f"{package}.{_package(superclass.package)}.logic." +
                           superclass.name)

    for import_item in sorted(set(import_list)):
        writer.writeln(f"import {import_item}")

    writer.newline()

    _write_logic_class(writer, entity.root)


def _write_logic_class(writer: IndentedWriter, message: Message) -> None:
    writer.write("public")

    writer.appendln(f" class {message.name} extends {message.name}Entity {{")
    writer.newline()

    indented_writer = writer.indented()

    super_variables = _get_super_variables(message)
    super_variables_string = []
    super_arguments_string = []

    for constructor_parameter in super_variables:
        name = constructor_parameter[0]
        type = constructor_parameter[1]

        super_variables_string.append(f'{name}: {type}')
        super_arguments_string.append(f'{name}')

    indented_writer.writeln(
        f'public {message.name}({", ".join(super_variables_string)}) {{'
    )
    indented_writer.indented().writeln(
        f'super({", ".join(super_arguments_string)});')
    indented_writer.writeln("}")

    for submessage in message.messages:
        name = submessage.name

        if submessage.is_array:
            if submessage.extends is None or submessage.properties or submessage.messages:
                _write_logic_class(indented_writer, submessage)
        else:
            if submessage.extends is None or (len(submessage.properties) + len(submessage.messages)):
                _write_logic_class(indented_writer, submessage)

    writer.writeln(f"}}")


def _get_super_variables(message: Message):
    super_variables: List[Tuple[str, str]] = []

    if message.extends is not None:
        super_variables += _get_super_variables(
            message.extends.root)

    for property in message.properties:
        type = property.type
        name = property.name
        method = property.method
        variable_name = camelcase(name)
        variable_type = _kotlin_type(type)
        nullable = property.nullable
        if property.enum is not None and len(property.enum):
            variable_type = name
        if not nullable and method != "request":
            super_variables.append((variable_name, variable_type))

    for message in message.messages:
        name = message.name
        nullable = message.nullable
        # special case for array messages
        if message.is_array:
            if message.extends is None or (len(message.properties) + len(message.messages)):
                variable_type = f"MutableList<{name}>"
            else:
                variable_type = f"MutableList<{message.extends.name}>"
            variable_name = camelcase(name) + "List"
        else:
            if message.extends is None or (len(message.properties) + len(message.messages)):
                variable_type = name
            else:
                variable_type = message.extends.name
            variable_name = camelcase(name)

        if not nullable:
            super_variables.append((variable_name, variable_type))
    return super_variables


def _get_superclasses(message: Message):
    superclasses = []
    if message.extends is not None:
        superclasses.append(message.extends)
        superclasses += _get_superclasses(message.extends.root)

    for message in message.messages:
        superclasses += _get_superclasses(message)

    return superclasses


def _package(path: pathlib.Path, start: str = None) -> str:
    parts: List[str] = []
    match = False
    for part in path.parts:
        if part == start or start is None:
            match = True

        if match:
            parts.append(part)

    return ".".join(parts)


def _kotlin_type(entity_type: str) -> str:
    if entity_type == "integer":
        return "Int"
    elif entity_type == "string":
        return "String"
    elif entity_type == "boolean":
        return "Boolean"
    elif entity_type == "date":
        return "String"
    elif entity_type == "clocktime":
        return "String"
    elif entity_type == "float":
        return "Double"
    else:
        return "String"

def lookahead(iterable):
    """Pass through all values from the given iterable, augmented by the
    information if there are more values to come after the current one
    (True), or if it is the last value (False).
    """
    # Get an iterator and pull the first value.
    it = iter(iterable)
    last = next(it)
    # Run the iterator to exhaustion (starting from the second value).
    for val in it:
        # Report the *previous* value (more to come).
        yield last, True
        last = val
    # Report the last value.
    yield last, False
