def should_do_work_for_platform(image, platform):
    if image.platforms is None and platform.is_default_platform:
        return True

    if image.platforms is not None and len(
            image.platforms) == 1 and image.platforms[0] == "*":
        return True

    if image.platforms is not None and platform.name in image.platforms:
        return True

    return False


def should_do_work_for_target(image, target, only_for_target):
    if only_for_target is not None and only_for_target != target.name:
        return False

    if image.targets is not None and target.name not in image.targets:
        return False

    return True
