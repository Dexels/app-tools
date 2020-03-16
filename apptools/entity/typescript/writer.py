import os
import pathlib
import shutil

from typing import List, Dict, Any, Tuple, Set

from apptools.entity.navajo import Entity, Message
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


def _write_datamodel(writer: IndentedWriter, entity: Entity,
                     output: pathlib.Path) -> None:
    dependency_statements: Set[str] = set()

    dependencies = _dependencies(entity.root)
    if dependencies:
        for dependency in dependencies:
            name = dependency.root.name
            path = _rel_import(entity.package, dependency.package, name)
            statement = f"import {{ {name} }} from '{str(path)}';"

            dependency_statements.add(statement)

    if dependency_statements:
        for dependency_statement in sorted(dependency_statements):
            writer.writeln(dependency_statement)
        writer.newline()

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


def _dependencies(message: Message) -> List[Entity]:
    entities: List[Entity] = []
    if message.extends is not None:
        entities.append(message.extends)

    for sub_message in message.messages:
        entities += _dependencies(sub_message)

    return entities


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
            if sub_message.extends is None or len(sub_message.properties):
                interfaces.append(sub_message)
                type = f"{name}[]"
            else:
                type = f"{sub_message.extends.name}[]"
        else:
            if sub_message.extends is None or len(sub_message.properties):
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
        for variable in sorted(variables):
            writer.indented().writeln(variable)

        writer.writeln("}")
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
    elif raw == 'clocktime':
        return 'string'
    elif raw == 'float':
        return 'number'
    elif raw == 'binary':
        return 'string'
    else:
        return 'string'
