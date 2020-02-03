import pathlib

from typing import Any, Dict, Optional, Callable

Options = Dict[str, Any]


def write(strings: Dict[str, Dict[str, str]], options: Options):
    output: pathlib.Path = options["output"]

    print(f"Writing to {output}")

    with open(output, "w") as fp:
        fp.write('<?xml version="1.0" encoding="utf-8"?>\n')
        fp.write(
            '<resources xmlns:tools="http://schemas.android.com/tools" tools:ignore="TypographyDashes">\n'
        )

        for key in sorted(strings):
            value = strings[key]["value"]
            escaped_value = escape(value)

            fp.write(
                f"\t<string name=\"{key}\" formatted=\"false\">\"{escaped_value}\"</string>\n"
            )

        fp.write('</resources>\n')


def escape(content):
    content = content.replace("&", "&amp;")
    content = content.replace("\n", "\\n")
    content = content.replace("'", "\\'")

    return content
