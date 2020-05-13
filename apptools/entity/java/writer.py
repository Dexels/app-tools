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
        service_class = service / f"{entity.name}Service.java"
        with IndentedWriter(path=service_class) as writer:
            _write_service(writer, entity, package)

    datamodel = output / entity.package / "datamodel"
    datamodel.mkdir(parents=True, exist_ok=True)
    datamodel_class = datamodel / f"{entity.name}Entity.java"
    with IndentedWriter(path=datamodel_class) as writer:
        _write_datamodel(writer, entity, output, package)

    logic = output / entity.package / "logic"
    logic.mkdir(parents=True, exist_ok=True)
    logic_class = logic / f"{entity.name}.java"
    if not logic_class.exists():
        with IndentedWriter(path=logic_class) as writer:
            _write_logic(writer, entity, package)


def _write_service(writer: IndentedWriter, entity: Entity,
                   package: str) -> None:
    writer.writeln(f"package {package}.{_package(entity.package)}.service;")

    writer.newline()

    dependencies: List[str] = ["retrofit2.http.Query"]

    # TODO: Are the non_null and nullable libraries not always imported? Because the default is on True.
    import_non_null = True
    import_nullable = True

    for property in entity.root.properties:
        if property.is_key:
            import_non_null = import_non_null or not property.nullable
            import_nullable = import_nullable or property.nullable

    if import_non_null:
        dependencies.append("androidx.annotation.NonNull")
    if import_nullable:
        dependencies.append("androidx.annotation.Nullable")
    if "GET" in entity.methods or "PUT" in entity.methods:
        dependencies.append("io.reactivex.Single")
    if "POST" in entity.methods or "DELETE" in entity.methods:
        dependencies.append("io.reactivex.Completable")
    if entity.version != -1:
        dependencies.append("retrofit2.http.Headers")
    if "PUT" in entity.methods or "POST" in entity.methods:
        dependencies.append("retrofit2.http.Body")
    for method in entity.methods:
        dependencies.append(f"retrofit2.http.{method}")
    if "GET" in entity.methods or "PUT" in entity.methods or "POST" in entity.methods:
        dependencies.append(
            f"{package}.{_package(entity.package)}.logic.{entity.name}")

    for dependency in sorted(dependencies):
        writer.writeln(f"import {dependency};")

    writer.newline()
    writer.writeln(f"public interface {entity.name}Service {{")
    writer.newline()

    for method in entity.methods:
        indented_writer = writer.indented()

        for key_id in entity.key_ids:
            parameter_list = []
            for key_property in entity.key_properties(key_id):
                variable_name = camelcase(key_property.name)
                variable_type = _java_type(key_property.type)
                nullable = '@NonNull'
                if key_property.nullable:
                    nullable = '@Nullable'
                parameter_list.append(
                    f'{nullable} @Query("{key_property.name}") {variable_type} {variable_name}'
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
                    f'Single<{entity.name}> get{entity.name}({parameters});')
            if method == "PUT":
                indented_writer.writeln(
                    f'Single<{entity.name}> update{entity.name}({parameters}, @NonNull @Body {entity.name} {entity.name[0].lower() + entity.name[1:]});'
                )
            if method == "DELETE":
                indented_writer.writeln(
                    f'Completable remove{entity.name}({parameters});')
            if method == "POST":
                indented_writer.writeln(
                    f'Completable insert{entity.name}({parameters}, @NonNull @Body {entity.name} {entity.name[0].lower() + entity.name[1:]});'
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
                    f'Single<{entity.name}> get{entity.name}();')
            if method == "PUT":
                indented_writer.writeln(
                    f'Single<{entity.name}> update{entity.name}(@NonNull @Body {entity.name} {entity.name[0].lower() + entity.name[1:]});'
                )
            if method == "DELETE":
                indented_writer.writeln(f'Completable remove{entity.name}();')
            if method == "POST":
                indented_writer.writeln(
                    f'Completable insert{entity.name}(@NonNull @Body {entity.name} {entity.name[0].lower() + entity.name[1:]});'
                )
            indented_writer.newline()

    writer.writeln("}")
    writer.newline()


def _write_datamodel(writer: IndentedWriter, entity: Entity,
                     output: pathlib.Path, package: str) -> None:
    writer.writeln(f"package {package}.{_package(entity.package)}.datamodel;")

    writer.newline()

    import_list = [
        "com.google.gson.annotations.SerializedName", "java.util.List",
        "java.io.Serializable", "androidx.annotation.NonNull",
        "androidx.annotation.Nullable",
        f"{package}.{_package(entity.package)}.logic." + entity.name
    ]

    for superclass in _get_superclasses(entity.root):
        import_list.append(f"{package}.{_package(superclass.package)}.logic." +
                           superclass.name)

    for import_item in sorted(set(import_list)):
        writer.writeln(f"import {import_item};")

    writer.newline()

    _write_datamodel_class(writer, entity.root)


def _write_datamodel_class(writer: IndentedWriter,
                           message: Message,
                           prefix: str = '') -> None:
    writer.write("public")
    if prefix != '':
        writer.append(" static")

    writer.append(f" class {message.name}Entity")
    if message.extends is not None:
        writer.append(f" extends {message.extends.name}")
    writer.appendln(" implements Serializable {")

    writer.newline()

    prefix += message.name + "."

    indented_writer = writer.indented()

    constructor_parameters = []

    for property in message.properties:
        if property.method == "request":
            continue

        type = property.type
        name = property.name
        variable_name = camelcase(name)
        variable_type = _java_type(type)
        nullable = property.nullable

        if property.enum is not None and len(property.enum):
            indented_writer.writeln(f'public enum {name} {{')
            for enum_value in property.enum:
                enum_writer = indented_writer.indented()
                enum_writer.writeln(f'{enum_value},')
            indented_writer.writeln('}')
            indented_writer.newline()
            variable_type = name
        if nullable:
            indented_writer.writeln(f'@Nullable')
        else:
            constructor_parameters.append((variable_name, variable_type))
            indented_writer.writeln(f'@NonNull')

        indented_writer.writeln(f'@SerializedName("{name}")')
        indented_writer.writeln(f"public {variable_type} {variable_name};")
        indented_writer.newline()

    for submessage in message.messages:
        name = submessage.name
        nullable = submessage.nullable

        if submessage.is_array:
            if submessage.extends is None or (len(submessage.properties) + len(submessage.messages)):
                _write_datamodel_class(indented_writer, submessage, prefix)
                variable_type = "List<" + prefix + name + ">"
            else:
                variable_type = "List<" + submessage.extends.name + ">"
            variable_name = camelcase(name) + "List"
        else:
            if submessage.extends is None or (len(submessage.properties) + len(submessage.messages)):
                _write_datamodel_class(indented_writer, submessage, prefix)
                variable_type = prefix + name
            else:
                variable_type = submessage.extends.name
            variable_name = camelcase(name)

        if nullable:
            indented_writer.writeln('@Nullable')
        else:
            constructor_parameters.append((variable_name, variable_type))
            indented_writer.writeln('@NonNull')
        indented_writer.writeln(f'@SerializedName("{name}")')
        indented_writer.writeln(f'public {variable_type} {variable_name};')
        indented_writer.newline()

    super_constructor_parameters = []
    constructor_parameters_string = []

    if message.extends is not None:
        super_constructor_parameters = _get_super_constructor_parameters(
            message.extends.root)

        for constructor_parameter in super_constructor_parameters:
            name = constructor_parameter[0]
            type = constructor_parameter[1]

            constructor_parameters_string.append(f'@NonNull {type} {name}')

    for constructor_parameter in constructor_parameters:
        name = constructor_parameter[0]
        type = constructor_parameter[1]

        constructor_parameters_string.append(f'@NonNull {type} {name}')

    indented_writer.writeln(
        f'public {message.name}Entity({", ".join(constructor_parameters_string)}) {{'
    )

    super_arguments_string = []

    for constructor_parameter in super_constructor_parameters:
        name = constructor_parameter[0]
        super_arguments_string.append(name)

    body_writer = indented_writer.indented()
    body_writer.writeln(f'super({", ".join(super_arguments_string)});')

    for constructor_parameter in constructor_parameters:
        name = constructor_parameter[0]

        body_writer.writeln(f'this.{name} = {name};')

    indented_writer.writeln('}')
    indented_writer.newline()

    writer.writeln("}")
    writer.newline()


def _write_logic(writer: IndentedWriter, entity: Entity, package: str) -> None:
    writer.writeln(f"package {package}.{_package(entity.package)}.logic;")

    writer.newline()

    import_list = [
        f"{package}.{_package(entity.package)}.datamodel.{entity.name}Entity",
        f"java.io.Serializable", "androidx.annotation.NonNull",
        "androidx.annotation.Nullable", "java.util.List"
    ]

    for superclass in _get_superclasses(entity.root):
        import_list.append(f"{package}.{_package(superclass.package)}.logic." +
                           superclass.name)

    for import_item in sorted(set(import_list)):
        writer.writeln(f"import {import_item};")

    writer.newline()

    _write_logic_class(writer, entity.root)


def _write_logic_class(writer: IndentedWriter, message: Message) -> None:
    writer.write("public")
    if writer.indent > 0:
        writer.append(" static")

    writer.appendln(f" class {message.name} extends {message.name}Entity {{")
    writer.newline()

    indented_writer = writer.indented()

    constructor_parameters = _get_super_constructor_parameters(message)
    constructor_parameters_string = []
    super_arguments_string = []

    for constructor_parameter in constructor_parameters:
        name = constructor_parameter[0]
        type = constructor_parameter[1]

        constructor_parameters_string.append(f'@NonNull {type} {name}')
        super_arguments_string.append(f'{name}')

    indented_writer.writeln(
        f'public {message.name}({", ".join(constructor_parameters_string)}) {{'
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


def _get_super_constructor_parameters(message: Message):
    constructor_parameters: List[Tuple[str, str]] = []

    if message.extends is not None:
        constructor_parameters += _get_super_constructor_parameters(
            message.extends.root)

    for property in message.properties:
        type = property.type
        name = property.name
        method = property.method
        variable_name = camelcase(name)
        variable_type = _java_type(type)
        nullable = property.nullable
        if property.enum is not None and len(property.enum):
            variable_type = name
        if not nullable and method != "request":
            constructor_parameters.append((variable_name, variable_type))

    for message in message.messages:
        name = message.name
        nullable = message.nullable
        # special case for array messages
        if message.is_array:
            if message.extends is None or (len(message.properties) + len(message.messages)):
                variable_type = f"List<{name}>"
            else:
                variable_type = f"List<{message.extends.name}>"
            variable_name = camelcase(name) + "List"
        else:
            if message.extends is None or (len(message.properties) + len(message.messages)):
                variable_type = name
            else:
                variable_type = message.extends.name
            variable_name = camelcase(name)

        if not nullable:
            constructor_parameters.append((variable_name, variable_type))
    return constructor_parameters


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


def _java_type(entity_type: str) -> str:
    if entity_type == "integer":
        return "Integer"
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
