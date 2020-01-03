# App-entity
Tool to transform the entities to code. We have support for multiple languages.
The first argument should be which writer you wanna use. See app-entity -h for
all possible writers.

## Install/Update
```bash
python3 -m pip install .
```

For now this will install a single tool called app-entity. In the future there
could be more.

The tool should display all the arguments when you run app-entity -h. Each
writer can have different arguments. To check them out run app-entity swift -h.

## Examples
Couple examples how to run:
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

