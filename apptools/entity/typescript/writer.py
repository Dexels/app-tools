import os
import pathlib
import shutil

from typing import List, Dict, Any, Tuple, Set

from apptools.entity.navajo import Entity, Message, Property
from apptools.entity.io import IndentedWriter
from apptools.entity.text import camelcase, capitalize


def write(entities: List[Entity], options: Dict[str, Any]) -> None:
    output = options["output"]
    # Make sure to remove all previously generated files in correct folder
    remove_all(output)

    for entity in entities:
        _write_entity(entity, output)


def remove_all(output: pathlib.Path) -> None:
    shutil.rmtree(output)


def _write_entity(entity: Entity, output: pathlib.Path) -> None:
    datamodel = output / entity.package
    datamodel.mkdir(parents=True, exist_ok=True)
    datamodel_class = datamodel / f"{entity.name}.ts"
    with IndentedWriter(path=datamodel_class) as writer:
        _write_datamodel(writer, entity, output)


def _write_enums(writer: IndentedWriter, message: Message) -> None:
    for property in message.properties:
        name = property.name
        if property.enum is not None:
            type = property.name

            _write_enum(writer, property, property.enum)

    for sub_message in message.messages:
        _write_enums(writer, sub_message)


def _write_enum(writer: IndentedWriter, property: Property,
                cases: List[str]) -> None:
    writer.writeln(
        f"export enum {property.name} {{")

    for case in cases:
        value = "'" + case + "'"
        if case.isnumeric() or case.replace('.', '', 1).isdigit():
            name = "'" + property.name + "_" + case + "'"
            value = case
        elif case.find(".") != -1:
            name = "'" + case + "'"
        else:
            name = case

        writer.indented().writeln(f"{name} = {value},")

    writer.writeln("}")
    writer.newline()


def _write_datamodel(writer: IndentedWriter, entity: Entity,
                     output: pathlib.Path) -> None:
    dependency_statements: Set[str] = set()

    dependencies = _get_dependencies(entity)
    if dependencies:
        for dependency in dependencies:
            print(dependency)
            name = dependency.name
            path = _rel_import(entity.package, dependency.package, name)
            statement = f"import {{ {name} }} from '{str(path)}';"

            dependency_statements.add(statement)

    if dependency_statements:
        for dependency_statement in sorted(dependency_statements):
            writer.writeln(dependency_statement)
        writer.newline()

    _write_enums(writer, entity.root)
    _write_datamodel_class(writer, entity.root)


def _rel_import(source: pathlib.Path, destination: pathlib.Path,
                name: str) -> str:
    # Do not use the pathlib.Path join method otherwise it will remove the
    # current dir dot.
    # For example: "./Official" becomes "Official" which is not the same as an
    # import statement.
    tmp_path = pathlib.Path(os.path.relpath(destination, source)).as_posix()
    prefix = ""
    if not tmp_path.startswith("."):
        prefix = "./"
    return prefix + str(tmp_path) + "/" + name


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
            shared_interface = _get_shared_interface(entity.root)
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

def _write_datamodel_class(writer: IndentedWriter,
                           message: Message,
                           prefix: str = '') -> None:
    writer.write(f"export interface {message.name}")
    if message.extends is not None:
        writer.append(f" extends {message.extends.name}")

    variables: Set[str] = set()

    for property in message.properties:
        if property.method == "request":
            continue

        name = property.name

        if property.enum is not None:
            type = name
        else:
            type = _type(property.type)

        variable = name
        variable += f": {type}"
        if property.nullable:
            variable += " | null"
        variable += ";"

        variables.add(variable)

    interfaces: List[Message] = []

    for sub_message in message.messages:
        name = sub_message.name
        type = sub_message.name

        if sub_message.is_array:
            if sub_message.extends is None or len(sub_message.messages) or len(sub_message.properties):
                interfaces.append(sub_message)
                type = f"{name}[]"
            else:
                type = f"{sub_message.extends.name}[]"
        else:
            if sub_message.extends is None or len(sub_message.messages) or len(sub_message.properties):
                interfaces.append(sub_message)
            else:
                type = sub_message.extends.name

        variable = name
        variable += f": {type}"
        if sub_message.nullable:
            variable += " | null"
        variable += ";"

        variables.add(variable)

    # When there are no variables, then just render an empty interface, but with {} on 1 line
    if variables:
        writer.appendln(" {")
        for variable in sorted(variables, key=lambda x: x.split(":")[0]):
            writer.indented().writeln(variable)

        writer.appendln("}")
    else:
        writer.appendln(" {}")

    if interfaces:
        writer.newline()

        for interface in interfaces:
            _write_datamodel_class(writer, interface)


def _type(raw: str) -> str:
    if raw == 'integer':
        return 'number'
    elif raw == 'string':
        return 'string'
    elif raw == 'boolean':
        return 'boolean'
    elif raw == 'date':
        return 'Date'
    elif raw == 'timestamp':
        return 'Date'
    elif raw == 'clocktime':
        return 'string'
    elif raw == 'float':
        return 'number'
    elif raw == 'binary':
        return 'string'
    elif raw == 'money':
        return 'number'
    else:
        return 'string'
