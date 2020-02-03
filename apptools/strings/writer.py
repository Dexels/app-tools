import json
import pathlib

from typing import Any, Dict, Optional, Callable

Options = Dict[str, Any]
Writer = Callable[[Dict[str, Dict[str, str]], Options], int]


def write(writer: Writer, options: Options) -> int:
    input: pathlib.Path = options["input"]
    default_language: str = options["default"]
    language: Optional[str] = options.get("language")
    platform: Optional[str] = options.get("platform")

    strings = read(input / filename(default_language), platform)

    if language is not None:
        strings = {**strings, **read(input / filename(language), platform)}

        target: Optional[str] = options.get("target")
        if target is not None:
            strings = {
                **strings,
                **read(input / filename(language, target), platform)
            }

    return writer(strings, options)


def filename(language: str, target: Optional[str] = None) -> str:
    if target is None:
        return f"strings-{language}.json"

    return f"strings-{language}-{target}.json"


def read(path: pathlib.Path,
         platform: Optional[str] = None) -> Dict[str, Dict[str, str]]:
    print(f"Reading {str(path)}")

    try:
        with open(path) as fp:
            content = fp.read()
            strings = json.loads(content)

            map = {}
            for tuple in strings:
                if "platform" not in tuple or tuple["platform"] == platform:
                    map[tuple["key"]] = tuple

            return map
    except:
        pass

    return {}
