import pathlib
import re

from typing import Any, Dict, Optional, Callable

Options = Dict[str, Any]


def write(strings: Dict[str, Dict[str, str]], options: Options):
    output: pathlib.Path = options["output"]

    print(f"Writing to {output}")

    regex = re.compile(r"%(\d+\$)?(s)")

    with open(output, "w") as fp:
        for key in sorted(strings):
            value = regex.sub("%\\1@", strings[key]["value"])
            escaped_value = escape(value)

            fp.write(f"\"{key}\" = \"{escaped_value}\";\n")


def escape(content: str) -> str:
    content = content.replace("\n", "\\n")
    content = content.replace('"', '\\"')

    return content
