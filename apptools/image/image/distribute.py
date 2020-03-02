from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from json import dump
from os import makedirs
from os.path import join
from shutil import copyfile

from apptools.image.core.color import hex_to_rgba
from apptools.image.core.imagetype import ImageType
from apptools.image.image.blueprint import Blueprint
from apptools.image.image.file import file
from apptools.image.image.svg2png import svg2png
from apptools.image.image.work import should_do_work_for_platform, should_do_work_for_target


def distribute(spec, only_for_target):
    print("Distribute project: '%s'" % spec.project)

    jobs = []
    for image in spec.images:
        job = DistributeJob(spec, image, only_for_target)
        jobs.append(job)

    print("Executing %s jobs" % len(jobs))

    max_workers = 10
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        [executor.submit(job.run) for job in jobs]

    print("Done distribute project: '%s'" % spec.project)


class DistributeJob(object):
    def __init__(self, spec, image, only_for_target):
        super().__init__()

        self.spec = spec
        self.image = image
        self.only_for_target = only_for_target

    def run(self):
        print("Distribute image: '%s'" % self.image.basename)

        image_path = join(self.spec.shared_path, 'images', self.image.basename)

        filecontent = None
        if self.image.isSVG():
            print("Load into memory: '%s'" % image_path)

            filecontent = self.load(image_path)

        for platform in self.spec.platforms:
            if not should_do_work_for_platform(self.image, platform):
                print('Skip for platform %s', platform)
                continue

            for target in platform.targets:
                if not should_do_work_for_target(self.image, target,
                                                 self.only_for_target):
                    print('Skip for target %s', target)
                    continue

                # since we reuse the filecontent for all images, we need to copy it to be change
                # free each iteration. Filecontent can be None if it isn't a svg
                filecontent_copy = deepcopy(filecontent)
                colorized_filecontent = self.colorize(filecontent_copy,
                                                      platform, target)
                print('Save image for %s(%s) at %s', target, platform,
                      image_path)
                self.save(colorized_filecontent, image_path, platform, target)

    def load(self, path):
        try:
            with open(path) as fp:
                return fp.read()
        except:
            print('Cannot open image file at "%s"' % path)

        return None

    def colorize(self, filecontent, platform, target):
        if not self.image.isSVG() or not self.image.colorize:
            return filecontent

        selected_theme = None
        for theme in self.spec.themes:
            if theme.name == target.name:
                selected_theme = theme
                break
        else:
            print("Invalid theme: '%s' for image '%s'" %
                  (target.name, self.image.basename))
            return filecontent

        print("Colorize image: '%s' with theme: '%s'" %
              (self.image.basename, selected_theme.name))

        colorset = selected_theme.get(self.image.style)
        for color_name, color in self.spec.placeholder_colormap.items():
            new_color = colorset.get(color_name)
            if new_color is not None:
                if len(new_color) > 6:
                    new_color = "rgba(%s, %s, %s, %s)" % hex_to_rgba(new_color)

                    print(
                        "Image: '%s': replace color: '%s' with new color: '%s'"
                        % (self.image.basename, color, new_color))
                else:
                    print(
                        "Image: '%s': replace color: '%s' with new color: '%s'"
                        % (self.image.basename, color, new_color))

                filecontent = filecontent.replace(color, new_color)

        return filecontent

    def save(self, filecontent, image_path, platform, target):
        if platform.is_ios():
            self.save_ios(filecontent, image_path, platform, target)
        elif platform.is_android():
            self.save_android(filecontent, image_path, platform, target)
        else:
            print("Unknown platform '%s'" % platform.name)

    def save_ios(self, filecontent, image_path, platform, target):
        if self.image.type == ImageType.APPICON:
            self.save_ios_appiconset(filecontent, image_path, platform, target)
        else:
            self.save_ios_imageset(filecontent, image_path, platform, target)

    def save_ios_appiconset(self, filecontent, image_path, platform, target):
        imageset_name = file(self.image, '.' + self.image.type.to_set())
        imageset_directory_path = join(platform.path, target.assets,
                                       imageset_name)

        makedirs(imageset_directory_path, exist_ok=True)

        contents = {"images": [], "info": {"version": 1, "author": "xcode"}}

        blueprint = Blueprint.make_appiconset_blueprint()
        for definition in blueprint.definitions:
            filename = definition.filename('appicon')
            destination_path = join(imageset_directory_path, filename)

            contents['images'].append({
                "size":
                "%sx%s" % (definition.size.width, definition.size.height),
                "idiom":
                str(definition.idiom),
                "filename":
                filename,
                "scale":
                "%sx" % definition.scale
            })

            svg2png(filecontent, definition.scale, destination_path,
                    definition.size)

        contents_json_path = join(imageset_directory_path, 'Contents.json')
        self.save_ios_contents_json(contents_json_path, contents, indent=2)

    def save_ios_imageset(self, filecontent, image_path, platform, target):
        imageset_name = file(self.image, '.imageset')
        imageset_directory_path = join(platform.path, target.assets,
                                       imageset_name)

        makedirs(imageset_directory_path, exist_ok=True)

        contents = {"images": [], "info": {"version": 1, "author": "xcode"}}

        filecopied = False
        for scale in platform.scales:
            image_name = file(self.image, '@%sx.png' % int(scale.multiplier))
            destination_path = join(imageset_directory_path, image_name)

            if self.image.isSVG():
                contents['images'].append({
                    "idiom":
                    "universal",
                    "filename":
                    image_name,
                    "scale":
                    '%sx' % int(scale.multiplier)
                })
                scaled_at = self.image.premultiplier * scale.multiplier
                svg2png(filecontent, scaled_at, destination_path)
            elif self.image.isPNG():
                content = {
                    "idiom": "universal",
                    "scale": '%sx' % int(scale.multiplier)
                }

                if not filecopied:
                    content["scale"] = '%sx' % int(scale.multiplier)
                    content["filename"] = image_name
                    copyfile(image_path, destination_path)
                    filecopied = True

                contents['images'].append(content)
            else:
                print("Unknown filetype: '%s'" % self.image.basename)

        contents_json_path = join(imageset_directory_path, 'Contents.json')
        self.save_ios_contents_json(contents_json_path, contents)

    def save_ios_contents_json(self, path, data, indent=None):
        print("Write Contents.json at '%s'" % path)
        with open(path, 'w') as fp:
            # Platform iOS uses 2 indent for images
            dump(data, fp, indent=2)

    def save_android(self, filecontent, image_path, platform, target):
        image_name = file(self.image)

        for scale in platform.scales:
            destination_directory_path = join(platform.path, target.assets,
                                              scale.directory)
            makedirs(destination_directory_path, exist_ok=True)
            destination_path = join(destination_directory_path, image_name)

            if self.image.isSVG():
                scaled_at = self.image.premultiplier * scale.multiplier
                svg2png(filecontent, scaled_at, destination_path)

                print(
                    "Converted image: '%s' svg to png at scale: '%s' to: '%s'"
                    % (image_path, scaled_at, destination_path))
            elif self.image.basename.endswith('.png'):
                copyfile(image_path, destination_path)

                print("Copied image: '%s': to: '%s'" %
                      (image_path, destination_path))
                # pngs are only set in the first scale
                break
