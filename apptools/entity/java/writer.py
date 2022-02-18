import pathlib

from typing import List, Dict, Any, Tuple, Set

from apptools.entity.navajo import Entity, Message
from apptools.entity.io import IndentedWriter
from apptools.entity.text import camelcase


def write(entities: List[Entity], options: Dict[str, Any]) -> None:
    output = options["output"]
    package = _package(output, start="com")

    for entity in entities:
        _write_entity(entity, output, package)


def _write_entity(entity: Entity, output: pathlib.Path, package: str) -> None:
    #if entity.name != "UserHomeContent":
    #    return
    if entity.methods:
        service = output / entity.package / "service"
        service.mkdir(parents=True, exist_ok=True)
        service_class = service / f"{entity.name}Service.java"
        with IndentedWriter(path=service_class) as writer:
            _write_service(writer, entity, package)

    datamodel = output / entity.package / "datamodel"
    datamodel.mkdir(parents=True, exist_ok=True)
    datamodel_class = datamodel / f"{entity.name}Entity.java"
    import_list = None
    with IndentedWriter(path=datamodel_class) as writer:
        import_list = _write_datamodel(writer, entity, output, package, None)
    with IndentedWriter(path=datamodel_class) as writer:
        _write_datamodel(writer, entity, output, package, import_list)

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

    dependencies: List[str] = []

    if entity.key_ids:
        dependencies.append("retrofit2.http.Query")

    import_non_null = False
    import_nullable = False

    for key_id in entity.key_ids:
        for key_property in entity.key_properties(key_id):
            if key_property.nullable:
                import_nullable = True
            else:
                import_non_null = True

    if "GET" in entity.methods or "PUT" in entity.methods or "POST" in entity.methods or "DELETE" in entity.methods:
        dependencies.append("io.reactivex.Single")
    if entity.version != -1:
        dependencies.append("retrofit2.http.Headers")
    if "PUT" in entity.methods or "POST" in entity.methods:
        import_non_null = True
        dependencies.append("retrofit2.http.Body")
    for method in entity.methods:
        dependencies.append(f"retrofit2.http.{method}")
    if "GET" in entity.methods or "PUT" in entity.methods or "POST" in entity.methods:
        dependencies.append(
            f"{package}.{_package(entity.package)}.logic.{entity.name}")
    if import_non_null:
        dependencies.append("androidx.annotation.NonNull")
    if import_nullable:
        dependencies.append("androidx.annotation.Nullable")

    previous_dependency = None
    for dependency in sorted(dependencies):
        if previous_dependency is not None and previous_dependency.split(".")[0] != dependency.split(".")[0]:
            writer.newline()
        writer.writeln(f"import {dependency};")
        previous_dependency = dependency

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
                    f'@Headers("X-Navajo-Entity-Version: {entity.version}")')
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
                    f'Single<{entity.name}> remove{entity.name}({parameters});')
            if method == "POST":
                indented_writer.writeln(
                    f'Single<{entity.name}> insert{entity.name}({parameters}, @NonNull @Body {entity.name} {entity.name[0].lower() + entity.name[1:]});'
                )
            indented_writer.newline()

        if not len(entity.key_ids):
            if entity.version != -1:
                indented_writer.writeln(
                    f'@Headers("X-Navajo-Entity-Version: {entity.version}")')
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
                indented_writer.writeln(f'Single<{entity.name}> remove{entity.name}();')
            if method == "POST":
                indented_writer.writeln(
                    f'Single<{entity.name}> insert{entity.name}(@NonNull @Body {entity.name} {entity.name[0].lower() + entity.name[1:]});'
                )
            indented_writer.newline()

    writer.writeln("}")
    writer.newline()


def _write_datamodel(writer: IndentedWriter, entity: Entity,
                     output: pathlib.Path, package: str, import_list: Set) -> None:
    writer.writeln(f"package {package}.{_package(entity.package)}.datamodel;")

    writer.newline()

    if import_list is not None:
        import_list.update({
            "java.io.Serializable"
        })

        for dependency in _get_dependencies(entity):
            import_list.add(f"{package}.{_package(dependency.package)}.logic." +
                               dependency.name)


        for import_item in sorted(import_list):
            writer.writeln(f"import {import_item};")
    else:
        import_list = set()

    writer.newline()

    import_list = _write_datamodel_class(writer, entity.root, import_list)

    return import_list


def _write_datamodel_class(writer: IndentedWriter,
                           message: Message,
                           import_list: Set,
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
            import_list.add("androidx.annotation.Nullable")
        else:
            constructor_parameters.append((variable_name, variable_type))
            indented_writer.writeln(f'@NonNull')
            import_list.add("androidx.annotation.NonNull")

        indented_writer.writeln(f'@SerializedName("{name}")')
        import_list.add("com.google.gson.annotations.SerializedName")
        indented_writer.writeln(f"public {variable_type} {variable_name};")
        indented_writer.newline()

    for submessage in message.messages:
        name = submessage.name
        nullable = submessage.nullable

        if submessage.is_array:
            if submessage.extends is None or submessage.is_non_empty:
                import_list.update(_write_datamodel_class(indented_writer, submessage, import_list, prefix))
                variable_type = "List<" + prefix + name + ">"
            else:
                variable_type = "List<" + submessage.extends.name + ">"
            variable_name = camelcase(name) + "List"
            import_list.add("java.util.List")
        else:
            if submessage.extends is None or submessage.is_non_empty:
                import_list.update(_write_datamodel_class(indented_writer, submessage, import_list, prefix))
                variable_type = prefix + name
            else:
                variable_type = submessage.extends.name
            variable_name = camelcase(name)

        if nullable:
            indented_writer.writeln('@Nullable')
            import_list.add("androidx.annotation.Nullable")
        else:
            constructor_parameters.append((variable_name, variable_type))
            indented_writer.writeln('@NonNull')
            import_list.add("androidx.annotation.NonNull")
        indented_writer.writeln(f'@SerializedName("{name}")')
        import_list.add("com.google.gson.annotations.SerializedName")
        indented_writer.writeln(f'public {variable_type} {variable_name};')
        indented_writer.newline()

    super_constructor_parameters = []
    constructor_parameters_string = []

    if message.extends is not None:
        super_constructor_parameters, super_import_list = _get_super_constructor_parameters(
            message.extends.root)
        import_list.update(super_import_list)

        for constructor_parameter in super_constructor_parameters:
            name = constructor_parameter[0]
            type = constructor_parameter[1]

            constructor_parameters_string.append(f'@NonNull {type} {name}')
            import_list.add("androidx.annotation.NonNull")

    for constructor_parameter in constructor_parameters:
        name = constructor_parameter[0]
        type = constructor_parameter[1]

        constructor_parameters_string.append(f'@NonNull {type} {name}')
        import_list.add("androidx.annotation.NonNull")

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

    return import_list


def _write_logic(writer: IndentedWriter, entity: Entity, package: str) -> None:
    writer.writeln(f"package {package}.{_package(entity.package)}.logic;")

    writer.newline()

    import_list = [
        f"{package}.{_package(entity.package)}.datamodel.{entity.name}Entity",
        f"java.io.Serializable", "androidx.annotation.NonNull",
        "androidx.annotation.Nullable", "java.util.List"
    ]

    for dependency in _get_dependencies(entity):
        import_list.append(f"{package}.{_package(dependency.package)}.logic." +
                           dependency.name)

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

    constructor_parameters, super_import_list = _get_super_constructor_parameters(message)
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
            if submessage.extends is None or submessage.is_non_empty:
                _write_logic_class(indented_writer, submessage)

    writer.writeln(f"}}")


def _get_super_constructor_parameters(message: Message):
    constructor_parameters: List[Tuple[str, str]] = []
    import_list = set()

    if message.extends is not None:
        super_constructor_parameters, super_import_list = _get_super_constructor_parameters(
            message.extends.root)
        constructor_parameters += super_constructor_parameters
        import_list.update(super_import_list)

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
            if message.extends is None or message.is_non_empty:
                variable_type = f"List<{name}>"
            else:
                variable_type = f"List<{message.extends.name}>"
            variable_name = camelcase(name) + "List"
            import_list.add("java.util.List")
        else:
            if message.extends is None or message.is_non_empty:
                variable_type = name
            else:
                variable_type = message.extends.name
            variable_name = camelcase(name)

        if not nullable:
            constructor_parameters.append((variable_name, variable_type))
    return constructor_parameters, import_list

# dependencies of an entity
# - the direct parent logic file (for extends) "A extends B"

# - the logic file itself (in case of inner classes)
#   - parent logic files of inner classes

# - all (in)direct top level nonnull messages that extend an entity and keep same name (for constructor) A(X x){super(x)}
def _get_constructor_dependencies(entity: Entity):
    dependencies = []
    if entity.root.extends is not None:
        dependencies += _get_constructor_dependencies(entity.root.extends)

    for message in entity.root.messages:
        if message.nullable:
            continue
        if message.extends is not None:
            if message.extends.name != message.name and message.is_non_empty:
                dependencies.append(entity)
            else:
                dependencies.append(message.extends)
        else:
            dependencies.append(entity)
    return dependencies

def _get_variable_dependencies(entity: Entity, root: Message):
    dependencies = []
    for message in root.messages:
        if message.extends is not None:
            dependencies.append(message.extends)
            if message.extends.name != message.name and message.is_non_empty:
                # we will have an inner class for this variable
                dependencies.append(entity)
                dependencies += _get_constructor_dependencies(message.extends)
        else:
            # we will have an inner class for this variable
            dependencies.append(entity)
        for submessage in message.messages:
            if submessage.extends is not None:
                dependencies.append(submessage.extends)
                if submessage.extends.name != submessage.name and submessage.is_non_empty:
                    dependencies += _get_variable_dependencies(submessage.extends, submessage.extends.root)
                    dependencies += _get_variable_dependencies(submessage.extends, submessage)
            else:
                dependencies += _get_variable_dependencies(entity, submessage)
    return dependencies


def _get_dependencies(entity: Entity):
    dependencies = []
    if entity.root.extends is not None:
        dependencies.append(entity.root.extends)
        dependencies += _get_constructor_dependencies(entity.root.extends)

    dependencies += _get_variable_dependencies(entity, entity.root)

    return dependencies


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
    elif entity_type == "long":
        return "Long"
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
