# App-tools
App-tools is a bundle of tools that are useful for writing client applications. Currently it consists of the following tools:
- app-entity
- app-image
- app-strings

## Install/Update
Install python3.9. This could be done with `brew install python@3.9` on the mac.

```bash
python3 -m pip install .
```
After any change run the command again to install that change. Also when changing branches run this command again. It is possible to install it with the `-e` flag to make it dynamic, but couldn't get this to work on a non-apple system.

## App entity
App-entity is a tool to generate boiler plate client code for apps that use an entity based API. It supports multiple languages (writers) and new ones may be added. Depending on the target language, it will generate datamodel classes (objects), stubs for logic classes, and services to perform operations defined in the API.

When running multiple times it will always replace the Service and Datamodel classes. The logic will not be updated because it could contain app logic which we cannot recreate.

The first argument should be which writer you wanna use. See app-entity -h for
all possible writers.

The tool displays all possible arguments when you run app-entity -h. Each
writer can have different arguments. To check them out run app-entity swift -h.

### Examples
The examples below show how the tool could be used:

```bash 
app-entity swift \
    --input "$GIT"/sportlink/scripts/entity/common/memberportal/app \
    --output "$GIT"/sportlinked-app-ios/app/Sportlinked \
    --xcodeproj "$GIT"/sportlinked-app-ios/app/sportlinked.xcodeproj
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
A tool to generate all the required images from one source called the `app_spec.json`.

```bash
app-image\
	-s "../shared/app_spec.json"\
	-p "ios"
```

## App strings
A tool to generate and combine all the strings using json files that will be set in the correct place for Android and iOS.

```bash
app-strings swift\
	--platform ios\
	--input "../shared/strings"\
	--output "cashless-app-visitor-ios/Taronga/en.lproj/Localizable.strings"\
	--default en\
	--language en\
	--target taronga
```

The order in all the just files will be merged is:
- strings-{default}.json
- strings-{language}.json
- strings-{target}.json
