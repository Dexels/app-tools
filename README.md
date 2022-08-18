# App-tools
App-tools is a bundle of tools that are useful for writing client applications. Currently it consists of the following tools:
- app-entity
- app-image
- app-strings

## Install/Update
The app-tools use python3.9. This needs to be installed, which could be done with `brew install python@3.9` on the Mac.

```bash
python3 -m pip install .
```
Any changes are only available for use after they have been installed using the previous command. Thus, if you change anything or change the branch, run this command again. It should be possible to install it with the `-e` flag to remove the need for re-running this command, but this has only worked on Stefan's system (Mac) for now.

## App entity
App-entity is a tool to generate boiler plate client code for apps that use an API based on Navajo Entities. It supports multiple client languages (writers) and new ones may be added. Depending on the target language, it will generate datamodel classes (objects), stubs for logic classes, and services to perform operations defined in the Entity API.

When running multiple times it will always replace the Service and Datamodel classes. The logic will not be updated because it could contain hand-crafted app logic which we cannot recreate (eg "isPlayer" -> roleId field equals "PLAYER").

The first argument should be which writer you want to use. See app-entity -h for
all possible writers.

The tool displays all possible arguments when you run app-entity -h. Each
writer can have different arguments. To check them out run eg. app-entity swift -h.

### Examples
The examples below show how the tool could be used:

```bash 
app-entity swift \
    --input "$GIT"/sportlink/scripts/entity/common/memberportal/app \
    --output "$GIT"/sportlinked-app-ios/app/Sportlinked \
 ```

```bash 
app-entity java \
    --input "$GIT"/sportlink/scripts/entity/common/memberportal/app \
    --output "$GIT"/sportlinked-app-android/app/src/main/java/com/dexels/sportlinked
```

```bash 
app-entity typescript \
    --input "$GIT"/sportlink/scripts/entity/common/clubweb \
    --output "$GIT"/com.sportlink.club.web/src/@types/generated
```

### Future
App entity was build for Java and Objective-C. Currently we use it for Kotlin and Swift. The latter languages are more advanced and could simplify the generation tool. Currently we have what we call a Logic class so we can update the datamodel always without worries and have the logic in the logic class. 
In both languages we can extend classes without subclassing so we might get away with just creating the datamodels and added logic through extensions which would decrease the complexity of the generation script by a lot.
Also Swift currently has automatic encoding and decoding build in the compile time. So we do not have to generate it anymore.

## App image
A tool to generate all the required images from one source called the `app_spec.json`. The files referred to in this json need to exist relative to the json file.

```bash
app-image\
	-s "../shared/app_spec.json"\
	-p "ios"
```

### app_spec.json
This file states which platform receives which images and in what scales. Both platform has different scales and different locations the images needs to be put. Most important is the `images` array.

Possible keys:
* The `basename` is a relative path in the shared directory to an actual image.
* The `platforms` states which platform receives the images (eg ios/android).
* The `targets` states which target will receive the image (eg ras, taronga).
* The `size` is a string stating the size the lowest scale should be. For that point we scale up.

#### Future
The `placeholder_colormap` and the `themes` keys should no longer be used. For iOS and Android development you can now use tint colors to style an image to a different colorset. This needs to be removed from the app-image toolset.

## App strings
A tool to generate and combine all the strings defined using json files that will be set in the correct place for Android and iOS.

```bash
app-strings swift\
	--platform ios\
	--input "../shared/strings"\
	--output "cashless-app-visitor-ios/Taronga/en.lproj/Localizable.strings"\
	--default en\
	--language en\
	--target taronga
```

The order the files will be merged in is:
- strings-{default}.json
- strings-{language}.json
- strings-{target}.json

In other words, a definition in strings-{target}.json overrules one in strings-{language}.json and strings-{default}.json, and one in strings-{language}.json overrules the one in strings-{default}.json, if not specified in strings-{target}.json. 
