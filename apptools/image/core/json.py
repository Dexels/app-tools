def json_get(key, container, required=True, fallback=None):
    if key not in container:
        if required:
            raise KeyError("Missing required key: '%s' in %r" %
                           (key, container))
        return fallback

    return container[key]
