# App-tools
App-tools is a bundle of tools that are useful for writing client applications. Currently it consists of the following tools:
- app-entity

## Install/Update
```bash
python3 -m pip install .
```

## App-entity
App-entity is a tool to generate boiler plate client code for apps that use an entity based API. It supports multiple languages (writers) and new ones may be added. Depending on the target language, it will generate datamodel classes (objects), stubs for logic classes, and services to perform operations defined in the API.

The first argument should be which writer you wanna use. See app-entity -h for
all possible writers.

The tool displays all possible arguments when you run app-entity -h. Each
writer can have different arguments. To check them out run app-entity swift -h.

### Examples
The examples below show how the tool could be used:
```bash 
app-entity swift \
    --username **** \
    --password **** \
    --input "$GIT"/sportlink/scripts/entity/common/memberportal/app \
    --output "$GIT"/sportlinked-app-ios/app/Sportlinked \
    --xcodeproj "$GIT"/sportlinked-app-ios/app/sportlinked.xcodeproj
 ```

```bash 
app-entity java \
    --username **** \
    --password **** \
    --input "$GIT"/sportlink/scripts/entity/common/memberportal/app \
    --output "$GIT"/sportlinked-app-android/app/src/main/java/com/dexels/sportlinked
```

```bash 
app-entity typescript \
    --username **** \
    --password **** \
    --input "$GIT"/sportlink/scripts/entity/common/clubweb \
    --output "$GIT"/com.sportlink.club.web/src/@types/generated
```

