def should_do_work_for_platform(image, platform, only_for_platform):
    if only_for_platform is not None and only_for_platform != platform.name:
        return False

    if image.platforms is None and platform.is_default_platform:
        return True

    if image.platforms is not None and len(
            image.platforms) == 1 and image.platforms[0] == "*":
        return True

    if image.platforms is not None and platform.name in image.platforms:
        return True

    return False


def should_do_work_for_target(image, target):
    if image.targets is not None and target.name not in image.targets:
        return False

    return True
