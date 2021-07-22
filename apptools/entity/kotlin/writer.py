import pathlib

from typing import List, Dict, Any, Tuple, Set

from apptools.entity.navajo import Entity, Message
from apptools.entity.io import IndentedWriter
from apptools.entity.text import camelcase

debug = False

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
    def __init__(self, network_name: str, name: str, type: str, primitive: bool, nullable: bool):
        super().__init__()

        self.network_name = network_name
        self.name = name
        self.type = type
        self.primitive = primitive
        self.nullable = nullable

    def __eq__(self, other):
        if isinstance(other, Variable):
            return self.network_name == other.network_name
        return NotImplemented

def write(entities: List[Entity], options: Dict[str, Any]) -> None:
    global debug
    output = options["output"]
    package = _package(output, start="com")
    force: bool = options.get("force", False)
    debug = options.get("debug", False)

    for entity in entities:
        _write_entity(entity, output, package, force)


def _write_entity(entity: Entity, output: pathlib.Path, package: str, force: bool) -> None:
    if entity.methods:
       service = output / entity.package / "service"
       service.mkdir(parents=True, exist_ok=True)
       service_class = service / f"{entity.name}Service.kt"
       with IndentedWriter(path=service_class) as writer:
           _write_service(writer, entity, package)

    datamodel = output / entity.package / "datamodel"
    datamodel.mkdir(parents=True, exist_ok=True)
    datamodel_class = datamodel / f"{entity.name}Entity.kt"
    import_list = None
    with IndentedWriter(path=datamodel_class) as writer:
        import_list = _write_datamodel(writer, entity, output, package, None)
    with IndentedWriter(path=datamodel_class) as writer:
        _write_datamodel(writer, entity, output, package, import_list)


    logic = output / entity.package / "logic"
    logic.mkdir(parents=True, exist_ok=True)
    logic_class = logic / f"{entity.name}.kt"
    if force or not logic_class.exists():
        with IndentedWriter(path=logic_class) as writer:
            _write_logic(writer, entity, package)


def _write_service(writer: IndentedWriter, entity: Entity,
                   package: str) -> None:
    writer.writeln(f"package {package}.{_package(entity.package)}.service")

    writer.newline()

    dependencies = set()
    dependencies.update(["retrofit2.http.Query", "com.google.gson.TypeAdapterFactory", f"com.sendrato.app.sdk.gson.RuntimeTypeAdapterFactory"])

    if "GET" in entity.methods or "PUT" in entity.methods or "POST" in entity.methods or "DELETE" in entity.methods:
        dependencies.add("io.reactivex.Single")
    if entity.version != -1:
        dependencies.add("retrofit2.http.Headers")
    if "PUT" in entity.methods or "POST" in entity.methods:
        dependencies.add("retrofit2.http.Body")
    for method in entity.methods:
        dependencies.add(f"retrofit2.http.{method}")
    if "GET" in entity.methods or "PUT" in entity.methods or "POST" in entity.methods or "DELETE" in entity.methods:
        dependencies.add(
            f"{package}.{_package(entity.package)}.logic.{entity.name}")
    for dependency in _get_dependencies(entity):
        dependencies.add(f"{package}.{_package(dependency.package)}.logic." + dependency.name)

    for dependency in sorted(dependencies):
        writer.writeln(f"import {dependency}")

    writer.newline()
    writer.writeln(f"interface {entity.name}Service {{")
    writer.newline()

    indented_writer = writer.indented()

    for method in entity.methods:

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

        if not entity.key_ids:
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
    indented_writer.writeln("companion object {")
    companion_writer = indented_writer.indented()
    companion_writer.writeln("var typeFactoryAdapterList = listOf<TypeAdapterFactory>(")
    _write_service_typeadapterfactories(companion_writer, entity.root, "")
    companion_writer.writeln(")")
    indented_writer.writeln("}")

    writer.writeln("}")
    writer.newline()

def _write_service_typeadapterfactories(writer: IndentedWriter, message: Message, prefix: str):
    prefix += message.name
    indented_writer = writer.indented()
    if len(message.extends) > 1:
        indented_writer.writeln("RuntimeTypeAdapterFactory")
        indented_indented_writer = indented_writer.indented()
        if message.interfaces and message.name == message.interfaces[0].name:
            indented_indented_writer.writeln(f'.of({message.name}::class.java, "__type__")')
        else:
            indented_indented_writer.writeln(f'.of({prefix}::class.java, "__type__")')
        for extends in message.extends:
            indented_indented_writer.writeln(f'.registerSubtype({prefix}{extends.name}::class.java, "{pathlib.Path(*extends.path.parts[1:])}")')
    elif len(message.extends) == 1:
        _write_service_typeadapterfactories(writer, message.extends[0].root, "")
    prefix += "."
    for submessage in message.messages:
       _write_service_typeadapterfactories(writer, submessage, prefix)


def _write_datamodel(writer: IndentedWriter, entity: Entity,
                     output: pathlib.Path, package: str, import_list: Set) -> None:
    writer.writeln(f"package {package}.{_package(entity.package)}.datamodel")

    writer.newline()

    if import_list is not None:
        import_list.update({
            "java.io.Serializable",
            "com.sendrato.app.sdk.datamodel.Entity",
            f"{package}.{_package(entity.package)}.logic.{entity.name}"
        })

        for dependency in _get_dependencies(entity):
            import_list.add(f"{package}.{_package(dependency.package)}.logic." +
                               dependency.name)
            import_list.add(f"{package}.{_package(dependency.package)}.datamodel." +
                               dependency.name + "Entity")


        for import_item in sorted(import_list):
            writer.writeln(f"import {import_item}")
    else:
        import_list = set()

    writer.newline()

    import_list = _write_datamodel_inner(writer, entity.root, import_list)

    return import_list

def _write_datamodel_inner(writer: IndentedWriter,
                           message: Message,
                           import_list: Set,
                           prefix: str = '') -> Set:
    if message.is_interface:
        shared_interface = _get_shared_interface(message)
        parents = []
        parents.append("Serializable")
        parents.append("Entity")
        for parent in shared_interface.parents:
            parents.append(f"{parent.name}, " )
        writer.writeln(f"interface {message.name}Entity : {', '.join(parents)} {{")
        indented_writer = writer.indented()
        
        for enum in shared_interface.enums:
            indented_writer.writeln(f"enum class {enum[0]} {{")
            indented_writer.indented().writeln(f'{", ".join(enum[1])}')
            indented_writer.writeln(f"}}")
            writer.newline()
        for variable in shared_interface.variables:
            indented_writer.writeln(f"var {variable.name}: {variable.type}" )
        if message.messages:
            variables = _get_variables(message, prefix + message.name + ".")
            for inner_class in variables[3]:
                import_list.update(_write_datamodel_inner(indented_writer, inner_class[0], import_list, inner_class[1]))
        
        else:
            writer.newline()
        
        writer.writeln("}")
        writer.newline()
        return import_list
    elif len(message.extends) > 1:
        shared_interface = _get_shared_interface(message)

        if message.interfaces and len(message.interfaces) > 1:
            assert False, f"This is not yet supported, multiple inheritance + multiple interfaces, not sure what code to generate"
    
        if message.interfaces and len(message.interfaces) == 1 and message.interfaces[0].root.name == message.name:
            # add import
            pass
        else:
            if message.interfaces:
                writer.writeln(f"interface {message.name}Entity : {message.interfaces[0].root.name}, Entity {{")
            else:
                writer.writeln(f"interface {message.name}Entity : Entity {{")
            indented_writer = writer.indented()
            for enum in shared_interface.enums:
                indented_writer.writeln(f"enum class {enum[0]} {{")
                indented_writer.indented().writeln(f'{", ".join(enum[1])}')
                indented_writer.writeln(f"}}")
                writer.newline()
            for variable in shared_interface.variables:
                indented_writer.writeln(f"var {variable.name}: {variable.type}")
            writer.writeln("}")
            writer.newline()


        for extends in message.extends:
            import_list.update(_write_datamodel_class(writer, extends.root, import_list, prefix, shared_interface))
            writer.newline()
            
        return import_list
    else:
        return _write_datamodel_class(writer, message, import_list, prefix)

def _write_datamodel_class(writer: IndentedWriter,
                           message: Message,
                           import_list: Set,
                           prefix: str = '',
                           shared_interface: SharedInterface = None) -> Set:
    if shared_interface is None:
        writer.write(f"open class {message.name}Entity")
    else:
        writer.write(f"open class {shared_interface.name}{message.name}Entity")

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

    constructor_vars = []
    member_vars = []    

    if len(message.extends) == 1:
        super_variables = _get_variables(message.extends[0].root, message.extends[0].root.name + ".", True)[0]
    for super_interface in message.interfaces:
        super_interface_variables = _get_variables(super_interface.root, prefix)

        super_interface_nonnull_variables += super_interface_variables[0]
        super_interface_nullable_variables += super_interface_variables[1]
    if shared_interface:
        for parent in shared_interface.parents:
            shared_interface_super_nonnull_variables += _get_variables(parent.root, prefix)[0]
            shared_interface_super_nullable_variables += _get_variables(parent.root, prefix)[1]

    indented_writer = writer.indented()

    if (super_variables or nonnull_variables or super_interface_nonnull_variables or shared_interface or shared_interface_super_nonnull_variables or shared_interface_super_nullable_variables):
        writer.appendln("(")

        if (super_variables):
            for variable in super_variables:
                if debug:
                    indented_writer.writeln('/* super variable */ ')
                indented_writer.writeln(f'{variable.name}: {variable.type},')
                constructor_vars.append(variable)
        
        if (super_interface_nonnull_variables):
            for variable in super_interface_nonnull_variables:
                if variable in shared_interface_super_nonnull_variables + nonnull_variables:
                    continue
                if shared_interface:
                    if debug:
                        indented_writer.writeln('/* super interface non null shared variable */ ')
                    indented_writer.writeln(f'override var {variable.name}: {variable.type},')
                else:
                    import_list.add("com.google.gson.annotations.SerializedName")
                    if debug:
                        indented_writer.writeln('/* super interface non null variable */ ')
                    indented_writer.writeln(f'@SerializedName("{variable.network_name}") override var {variable.name}: {variable.type},')
                constructor_vars.append(variable)

        if (nonnull_variables):
            for variable in nonnull_variables:
                import_list.add("com.google.gson.annotations.SerializedName")
                if shared_interface:
                    if variable in super_interface_nonnull_variables:
                        if debug:
                            indented_writer.writeln('/* non null shared override variable */ ')    
                        indented_writer.writeln(f'{variable.name}: {variable.type},')
                    else:
                        if debug:
                            indented_writer.writeln('/* non null shared variable */ ')    
                        indented_writer.writeln(f'{variable.name}: {variable.type},')
                else:
                    if variable in super_interface_nonnull_variables:
                        if debug:
                            indented_writer.writeln('/* non null override variable */ ')    
                        indented_writer.writeln(f'@SerializedName("{variable.network_name}") override var {variable.name}: {variable.type},')
                    else:
                        if debug:
                            indented_writer.writeln('/* non null variable */ ')
                        indented_writer.writeln(f'@SerializedName("{variable.network_name}") open var {variable.name}: {variable.type},')
                    
                constructor_vars.append(variable)

        if (shared_interface):
            for variable in shared_interface.variables:
                import_list.add("com.google.gson.annotations.SerializedName")
                if debug:
                    indented_writer.writeln('/* shared interface variable */ ')
                indented_writer.writeln(f'@SerializedName("{variable.network_name}") override var {variable.name}: {variable.type},')
                constructor_vars.append(variable)

        if (shared_interface_super_nonnull_variables):
            for variable in shared_interface_super_nonnull_variables:
                if variable in nonnull_variables:
                    continue
                if debug:
                    indented_writer.writeln('/* shared interface super nonnull variable */ ')
                indented_writer.writeln(f'@SerializedName("{variable.network_name}") override var {variable.name}: {variable.type},')
                constructor_vars.append(variable)
                
        writer.write(")")
    if shared_interface:
        writer.append(f" : {message.name}")
        if super_variables or super_interface_nonnull_variables or nonnull_variables:
            vars = []
            if super_variables:
                for variable in super_variables:
                    vars.append(f'{variable.name}')
            if (super_interface_nonnull_variables):
                for variable in super_interface_nonnull_variables:
                    if variable in nonnull_variables:
                        continue
                    vars.append(f'{variable.name} /* super interface */')
            if nonnull_variables:
                for variable in nonnull_variables:
                    vars.append(f'{variable.name}')
            writer.append(f'({", ".join(vars)})')

        if shared_interface.is_inner:
            writer.append(f", {prefix + shared_interface.name}")
        else:
            writer.append(f", {shared_interface.name}")
        # if shared_interface.variables:
            # writer.append("(")
            # for variable in shared_interface.variables:
            #     writer.append(f'{variable.name}, ')
            # writer.append(")")
        writer.append(", Serializable, Entity")
    elif not message.extends:
        writer.append(" : Serializable, Entity")
    else:
        writer.append(f" : {message.extends[0].name}")
        if super_variables:
            writer.appendln("(")
            for variable, has_more in lookahead(super_variables):
                indented_writer.write(f'{variable.name}')
                if has_more:
                    writer.appendln(',')
                else:
                    writer.appendln('')
            writer.write(")")
        writer.append(", Serializable, Entity")
    if not shared_interface:
        for message_interface in message.interfaces:
            writer.append(f", {message_interface.name}")

    hasId = False
    if not shared_interface:
        for variable in nonnull_variables:
            if variable.network_name == "Id" and variable.type == "String" and not variable.nullable:
                hasId = True

    
    writer.appendln(" {")
    writer.newline()

    if (shared_interface_super_nullable_variables):
        for variable in shared_interface_super_nullable_variables:
            if variable in nullable_variables:
                continue
            else:
                if debug:
                    indented_writer.writeln('/* shared interface super nullable variable */ ')
                indented_writer.writeln(f'@SerializedName("{variable.network_name}") override var {variable.name}: {variable.type} = null')
                member_vars.append(variable)

    for inner_class in inner_classes:
        import_list.update(_write_datamodel_inner(indented_writer, inner_class[0], import_list, inner_class[1]))

    for enum in enums:
        indented_writer.writeln(f"enum class {enum[0]} {{")
        indented_writer.indented().writeln(f'{", ".join(enum[1])}')
        indented_writer.writeln(f"}}")
        writer.newline()

    if not shared_interface:
        for variable in nullable_variables:
            import_list.add("com.google.gson.annotations.SerializedName")
            indented_writer.writeln(f'@SerializedName("{variable.network_name}")')
            indented_writer.writeln(f"open var {variable.name}: {variable.type} = null")
            member_vars.append(variable)
            writer.newline()

        for variable in super_interface_nullable_variables:
            import_list.add("com.google.gson.annotations.SerializedName")
            indented_writer.writeln(f'@SerializedName("{variable.network_name}")')
            indented_writer.writeln(f"override var {variable.name}: {variable.type} = null")
            member_vars.append(variable)
            writer.newline()
    
    if hasId:
        indented_writer.writeln("override fun hashCode(): Int {")
        indented_writer.indented().writeln("return id.hashCode()")
        indented_writer.writeln("}")
        indented_writer.newline()
        indented_writer.writeln("override fun equals(other: Any?): Boolean {")
        indented_writer.indented().writeln(f"if (other is {message.name}Entity) {{")
        indented_writer.indented().indented().writeln("return this === other || (id == other.id && id != INSERT_ID)")
        indented_writer.indented().writeln("}")
        indented_writer.indented().writeln("return super.equals(other)")
        indented_writer.writeln("}")
        indented_writer.newline()
        indented_writer.writeln("companion object {")
        indented_writer.indented().writeln('const val INSERT_ID = "insert"')
        indented_writer.writeln("}")
        indented_writer.newline()

    logic_type = f"{prefix}{shared_interface.name}{message.name}" if shared_interface else f"{prefix[:-1]}"
    indented_writer.writeln("@Transient")
    indented_writer.writeln(f"private lateinit var original: {logic_type}")
    indented_writer.newline()
    indented_writer.writeln("override fun saveOriginal() {")
    indented_writer.indented().writeln(f"original = copy()")
    indented_writer.writeln("}")
    indented_writer.newline()
    
    indented_writer.writeln(f"override fun copy(): {logic_type} {{")
    indented_writer.indented().write(f"val copy = {logic_type}(")
    for variable in constructor_vars:
        indented_writer.append(f"{variable.name}{'.map { it.copy() }.map { it as ' + variable.type[12:-1] + ' }.toMutableList()' if variable.name.endswith('List') else ''}{'' if variable.primitive or variable.name.endswith('List') else ('.copy() as ' + variable.type)}, ")
    indented_writer.appendln(")")
    indented_writer.indented().writeln(f"copy.copyNullableVariables(this as {logic_type})")
    indented_writer.indented().writeln(f"return copy")
    indented_writer.writeln("}")
    indented_writer.newline()
    indented_writer.writeln(f"fun copyNullableVariables(from: {logic_type}) {{")
    if message.extends or shared_interface:
        indented_writer.indented().writeln(f"super.copyNullableVariables(from)")
    for variable in member_vars:
        if variable.primitive:
            indented_writer.indented().writeln(f"{variable.name} = from.{variable.name}")
        else:
            if variable.name.endswith("List"):
                if variable.nullable:
                    indented_writer.indented().writeln(f"{variable.name} = from.{variable.name}?.map {{ it.copy() }}?.map {{ it as {variable.type[12:-2]} }}?.toMutableList()")
                else:
                    indented_writer.indented().writeln(f"{variable.name} = from.{variable.name}.map {{ it.copy() }}.map {{ it as {variable.type[12:-1]} }}.toMutableList()")
            else:
                indented_writer.indented().writeln(f"{variable.name} = from.{variable.name}{'?' if variable.nullable else ''}.copy() as {variable.type}")
    indented_writer.writeln("}")
    indented_writer.newline()
    
    indented_writer.writeln(f"override fun deepEquals(other: Any?): Boolean {{")

    if message.extends:
        indented_writer.indented().writeln(f"if (!super.deepEquals(other)) {{")
        indented_writer.indented().indented().writeln("return false")
        indented_writer.indented().writeln("}")
    indented_writer.indented().writeln(f"return other is {logic_type}")
    for variable in (constructor_vars + member_vars):
        if variable.primitive:
            indented_writer.indented().indented().writeln(f"&& {variable.name} == other.{variable.name}")
        else:
            if variable.name.endswith("List"):
                indented_writer.indented().indented().writeln(f"&& {f'if ({variable.name} == null || other.{variable.name} == null) {variable.name} == other.{variable.name} else' if variable.nullable else ''} {variable.name}!!.size == other.{variable.name}!!.size && {variable.name}!!.zip(other.{variable.name}!!) {{ a, b -> a.deepEquals(b) }}.fold(true) {{ x, y -> x && y}}")
            else:
                indented_writer.indented().indented().writeln(f"&& {f'if ({variable.name} == null) other.{variable.name} == null else {variable.name}?' if variable.nullable else variable.name}.deepEquals(other.{variable.name}){' == true' if variable.nullable else ''}")
            
    indented_writer.writeln("}")
    indented_writer.newline()
    if message.extends or shared_interface:
        indented_writer.write("override ")
    else:
        indented_writer.write("open ")
    indented_writer.appendln(f"fun hasChanged(): Boolean {{")
    indented_writer.indented().writeln(f"return !deepEquals(original)")
    indented_writer.writeln("}")

    indented_writer.newline()
    indented_writer.writeln(f"override fun toOriginal() : {logic_type} {{")
    indented_writer.indented().writeln(f"val result = original")
    indented_writer.indented().writeln(f"original.saveOriginal()")
    indented_writer.indented().writeln(f"return result")
    indented_writer.writeln("}")

    writer.writeln("}")
    

    return import_list


def _write_logic(writer: IndentedWriter, entity: Entity, package: str) -> None:
    writer.writeln(f"package {package}.{_package(entity.package)}.logic")

    writer.newline()

    import_list = [
        f"{package}.{_package(entity.package)}.datamodel.{entity.name}Entity"
    ]

    for dependency in _get_dependencies(entity, False): # set this to True to reduce imports, but will give false negatives at the moment
        import_list.append(f"{package}.{_package(dependency.package)}.logic." +
                           dependency.name)
        import_list.append(f"{package}.{_package(dependency.package)}.datamodel." + dependency.name + "Entity")

    for import_item in sorted(set(import_list)):
        writer.writeln(f"import {import_item}")

    writer.newline()

    _write_logic_inner(writer, entity.root)

def _write_logic_inner(writer: IndentedWriter, message: Message) -> None:
    if message.is_interface:
        writer.writeln(f"interface {message.name} : {message.name}Entity {{")
        indented_writer = writer.indented()
        if message.messages:
            for submessage in message.messages:
                name = submessage.name
                if submessage.is_array:
                    if len(submessage.extends) != 1 or submessage.properties or submessage.messages:
                        _write_logic_inner(indented_writer, submessage)
                else:
                    if len(submessage.extends) != 1 or submessage.properties or submessage.messages:
                        _write_logic_inner(indented_writer, submessage)
    elif len(message.extends) > 1:
        shared_interface = _get_shared_interface(message)

        if message.interfaces and len(message.interfaces) > 1:
            assert False, f"This is not yet supported, multiple inheritance + multiple interfaces, not sure what code to generate"
    
        if message.interfaces and len(message.interfaces) == 1 and message.interfaces[0].root.name == message.name:
            # add import
            pass
        else:
            #if message.interfaces:
            writer.writeln(f"interface {message.name} : {message.name}Entity {{")
            #else:
            #    writer.writeln(f"interface {message.name} {{")
            indented_writer = writer.indented()
            # for variable in shared_interface.variables:
            #     indented_writer.writeln(f"var {variable.name}: {variable.type}")
            writer.writeln("}")
            writer.newline()
        
        

        for extends in message.extends:
            _write_logic_class(writer, extends.root, shared_interface)
            writer.newline()
    else:
        _write_logic_class(writer, message)

def _write_logic_class(writer: IndentedWriter, message: Message, shared_interface: SharedInterface = None) -> None:
    if shared_interface:
        writer.write(f"open class {shared_interface.name}{message.name}")
    else:
        writer.write(f"open class {message.name}")

    super_nonnull_variables = _get_variables(message, "", True)[0]
    super_nullable_variables = _get_variables(message, "", True)[1]
    shared_interface_super_nonnull_variables = []
    shared_interface_super_nullable_variables = []
    if shared_interface:
        for parent in shared_interface.parents:
            shared_interface_super_nonnull_variables += _get_variables(parent.root, "")[0]
            shared_interface_super_nullable_variables += _get_variables(parent.root, "")[1]

    indented_writer = writer.indented()

    writer.appendln("(")
    if (super_nonnull_variables or shared_interface_super_nonnull_variables or shared_interface_super_nullable_variables):    
        for constructor_parameter in super_nonnull_variables:
            name = constructor_parameter.name
            type = constructor_parameter.type
            indented_writer.writeln(f'{name}: {type},')
        if shared_interface:
            for variable in shared_interface.variables:
                if variable not in super_nonnull_variables:
                    indented_writer.writeln(f'{variable.name}: {variable.type},')
        if shared_interface_super_nonnull_variables:
            for variable in shared_interface_super_nonnull_variables:
                if variable not in super_nonnull_variables:
                    indented_writer.writeln(f'{variable.name}: {variable.type},')
        # if shared_interface_super_nullable_variables:
        #     for variable in shared_interface_super_nullable_variables:
        #         if variable not in super_nullable_variables:
        #             indented_writer.writeln(f'{variable.name}: {variable.type},')

        if shared_interface:
            writer.writeln(f") : {shared_interface.name}{message.name}Entity(")
        else:
            writer.writeln(f") : {message.name}Entity(")
        for constructor_parameter in super_nonnull_variables:
            name = constructor_parameter.name
            if debug:
                indented_writer.writeln('/* super variable */ ')
            indented_writer.writeln(f'{name},') 
        if shared_interface:
            for variable in shared_interface.variables:
                if variable not in super_nonnull_variables:
                    if debug:
                        indented_writer.writeln('/* shared interface variable */ ')
                    indented_writer.writeln(f'{variable.name},') 
        if shared_interface_super_nonnull_variables:
            for variable in shared_interface_super_nonnull_variables:
                if variable not in super_nonnull_variables:
                    if debug:
                        indented_writer.writeln('/* shared interface super nonnull variable */ ')
                    indented_writer.writeln(f'{variable.name},')
        # if shared_interface_super_nullable_variables:
        #     for variable in shared_interface_super_nullable_variables:
        #         if variable not in super_nullable_variables:
        #             if debug:
        #                 indented_writer.writeln('/* shared interface super nullable variable */ ')
        #             indented_writer.writeln(f'{variable.name},')      
        writer.write(f")")
    else:
        if shared_interface:
            writer.writeln(f") : {shared_interface.name}{message.name}Entity()")
        else:
            writer.writeln(f") : {message.name}Entity()")
    hasId = False
    if not shared_interface:
        for variable in super_nonnull_variables:
            if variable.network_name == "Id" and variable.type == "String" and not variable.nullable:
                hasId = True
    
    if hasId or message.messages:
        hasSubClass = False
        for submessage in message.messages:
            name = submessage.name

            if submessage.is_array:
                if len(submessage.extends) != 1 or submessage.properties or submessage.messages or submessage.interfaces:
                    if not hasSubClass:
                        writer.appendln(" {")
                        hasSubClass = True
                    _write_logic_inner(indented_writer, submessage)
            else:
                if len(submessage.extends) != 1 or submessage.properties or submessage.messages or submessage.interfaces:
                    if not hasSubClass:
                        writer.appendln(" {")
                        hasSubClass = True
                    _write_logic_inner(indented_writer, submessage)
        if hasId:
            if not hasSubClass:
                writer.appendln(" {")
                hasSubClass = True
            indented_writer.newline()
            indented_writer.writeln("companion object {")  
            indented_writer.indented().write("fun create(")
            for constructor_parameter in super_nonnull_variables:
                name = constructor_parameter.name
                type = constructor_parameter.type
                if name != 'id':
                    indented_writer.append(f'{name}: {type}, ')      
            indented_writer.append(") = " + message.name + "(INSERT_ID")
            for constructor_parameter in super_nonnull_variables:
                name = constructor_parameter.name
                type = constructor_parameter.type
                if name != 'id':
                    indented_writer.append(f', {name}')
            indented_writer.appendln(")")
            indented_writer.writeln("}")  
        if hasSubClass:
            writer.writeln("}")
        else:
            writer.newline()
    else:
        writer.newline()
    
    if (shared_interface and (super_nonnull_variables or shared_interface_super_nonnull_variables or shared_interface_super_nullable_variables)):
        constructor_writer = indented_writer.indented()
        writer.writeln("{")
    
        indented_writer.writeln("constructor(")
        constructor_writer.writeln(f"{camelcase(message.name)}: {message.name},")
        for constructor_parameter in shared_interface_super_nonnull_variables:
            if constructor_parameter not in super_nonnull_variables:
                constructor_writer.writeln(f'{constructor_parameter[1]}: {constructor_parameter[2]},') #last one without comma
        # for constructor_parameter in shared_interface_super_nullable_variables:
        #     if constructor_parameter not in super_nullable_variables:
        #         constructor_writer.writeln(f'{constructor_parameter[1]}: {constructor_parameter[2]},') #last one without comma    
        for variable in shared_interface.variables:
            if variable not in super_nonnull_variables:
                constructor_writer.writeln(f"{variable.name}: {variable.type},")
        indented_writer.writeln(") : this(")
        for constructor_parameter in super_nonnull_variables:
            name = constructor_parameter.name
            constructor_writer.writeln(f'{camelcase(message.name)}.{name},') #last one without comma
        for constructor_parameter in shared_interface_super_nonnull_variables:
            if constructor_parameter not in super_nonnull_variables:
                name = constructor_parameter.name
                constructor_writer.writeln(f'{name},') #last one without comma    
        # for constructor_parameter in shared_interface_super_nullable_variables:
        #     name = constructor_parameter[1]
        #     if constructor_parameter not in super_nullable_variables:
        #         constructor_writer.writeln(f'{name},') #last one without comma    
        for variable in shared_interface.variables:
            if variable not in super_nonnull_variables:
                constructor_writer.writeln(f'{variable.name},')
        indented_writer.writeln(") {")
        indented_writer.indented().writeln(f"copyNullableVariables({camelcase(message.name)})")
        indented_writer.writeln("}")
        writer.writeln("}")
    
def _get_shared_interface(message: Message) -> SharedInterface:
    variables = []
    enums = []

    for property in message.properties:
        if property.method == "request":
            continue

        type = property.type
        name = property.name
        variable_name = camelcase(name)
        variable_type = _kotlin_type(type)
        nullable = property.nullable

        if property.enum:
            variable_type = message.name + "Entity." + name
            enum_options = []
            for enum_value in property.enum:
                enum_options.append(enum_value)
            enums.append((name, enum_options))
            # assert False, "This is not supported, because of Swift :-("
        if nullable:
            variable_type += "?"
        variables.append(Variable(name, variable_name, variable_type, True, nullable))

    for submessage in message.messages:
        name = submessage.name
        nullable = submessage.nullable

        if submessage.is_array:
            if not submessage.extends or (len(submessage.extends) == 1 and (submessage.properties or submessage.messages)):
                # assert False, "This is not supported, because of Swift :-("
                variable_type = "MutableList<" + submessage.name + ">"
            elif len(submessage.extends) == 1:
                variable_type = "MutableList<" + submessage.extends[0].name + ">"
            else:
                variable_type = "MutableList<" + submessage.name + ">"
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
        variables.append(Variable(name, variable_name, variable_type, False, nullable))
    return SharedInterface(message.name, variables, message.interfaces, enums)

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
        variable_type = _kotlin_type(type)
        variable_type_primitive = True
        nullable = property.nullable

        if property.enum:
            enum_options = []
            for enum_value in property.enum:
                enum_options.append(enum_value)
            enums.append((name, enum_options))
            if message.is_interface:
                variable_type = f"{message.name}Entity.{name}"
            else:
                variable_type = name
        if nullable:
            variable_type += "?"
            nullable_variables.append(Variable(name, variable_name, variable_type, variable_type_primitive, nullable))
        else:
            nonnull_variables.append(Variable(name, variable_name, variable_type, variable_type_primitive, nullable))

    for submessage in message.messages:
        name = submessage.name
        nullable = submessage.nullable
        variable_type_primitive = False
        if submessage.is_array:
            if not submessage.extends or (submessage.interfaces and submessage.name != submessage.interfaces[0].name) or (len(submessage.extends) == 1 and (submessage.properties or submessage.messages)):
                # inner class
                inner_classes.append((submessage, prefix))
                variable_type = "MutableList<" + prefix + name + ">"
            elif len(submessage.extends) == 1:
                # external class
                variable_type = "MutableList<" + submessage.extends[0].name + ">"
            elif len(submessage.interfaces) == 1 and submessage.interfaces[0].name == submessage.name:
                # external interface
                inner_classes.append((submessage, prefix))
                variable_type = "MutableList<" + submessage.name + ">"
            else:
                inner_classes.append((submessage, prefix))
                variable_type = "MutableList<" + prefix + submessage.name + ">"
            variable_name = camelcase(name) + "List"
        else:
            if not submessage.extends or (submessage.interfaces and submessage.name != submessage.interfaces[0].name) or (len(submessage.extends) == 1 and (submessage.properties or submessage.messages)):
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
            nullable_variables.append(Variable(name, variable_name, variable_type, variable_type_primitive, nullable))
        else:
            nonnull_variables.append(Variable(name, variable_name, variable_type, variable_type_primitive, nullable))
    
    if recursive:
        if len(message.extends) == 1:
            result = _get_variables(message.extends[0].root, prefix, recursive)
            nonnull_variables = result[0] + nonnull_variables
            nullable_variables += result[1] + nullable_variables
            enums += result[2]
            inner_classes += result[3]
        for interface in message.interfaces:
            result = _get_variables(interface.root, prefix, recursive)
            for variable in result[0]:
                if variable not in nonnull_variables:
                    nonnull_variables.insert(0, variable)
            for variable in result[1]:
                if variable not in nullable_variables:
                    nullable_variables.insert(0, variable)
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
        
        if message.interfaces:
            for interface in message.interfaces:
                dependencies.append(interface)
                dependencies += _get_variable_dependencies(interface, interface.root, logic)
        
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

    for interface in entity.root.interfaces:
        dependencies.append(interface)
        dependencies += _get_variable_dependencies(interface, interface.root, logic)

    dependencies += _get_variable_dependencies(entity, entity.root, logic)

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


def _kotlin_type(entity_type: str) -> str:
    if entity_type == "integer":
        return "Int"
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
