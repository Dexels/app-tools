require 'xcodeproj'
require 'pathname'

# Script to modify the pbxproj file so Xcode sees file we create.

# input:
xcodeproj_path = ARGV[0]
paths = ARGV.drop(1)

project = Xcodeproj::Project.open(xcodeproj_path)

paths.each { |path|
    # Make all the directories if needed. Notice the path.dirname so we do not
    # create the file reference here.
    pathname = Pathname.new(path)
    group = project.main_group

    pathname.dirname.descend { |component|
        dirname = component.basename.to_s

        next_group = group.children.find { |child| child.path == dirname }
        if next_group.nil?
            next_group = group.new_group(dirname, dirname)
        end

        # Needed for the next loop
        group = next_group
    }

    # Method pathname.basename returns a / at the end sometimes so we use the
    # method on File instead.
    filename = File.basename(pathname.to_s)

    file = group.files.find { |file| file.path == filename }
    if file.nil?
        file = group.new_file(filename)

        project.targets.each do |target|
            target.add_file_references([file])
        end
    end
}

project.save()

exit 0
