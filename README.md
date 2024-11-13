# vcs
a version control system in python

## the basic requirements
- create a cli to
  - initialise the zipfile repository
  - commit and checkout files and track change
  - show differences between versions
  - display simple metrics

## class structure
- `Repository` manages the repository (initialization, commits, file versioning)
- `FileVersion` represents a versioned file, handles zipping/unzipping and comparison between versions
- `VCSInterface` defines the vcs application command-line interface using cmd
- `CommitLog` manages commits and commit history

## the file structure
```
my_vcs/
  ├── .vcs/
  │   ├── versions/
  │   │   ├── file1_1.0.txt
  │   │   ├── file1_1.1.txt
  │   └── metadata.json
  ├── repository_manager.py
  └── file1.txt
```

## available commands
- init
-- create an empty zipfile repository

- commit <file_path> <version>
-- save a file to the zipfile repository at version <version>

- checkout <file_path> <version>
-- recovers a file from the zipfile repository at version <version>

- log <file_path> <version>
-- displays the version history of a file in the zipfile repository

- diff <file_name> <version1> <version2>
-- list the differences in the committed file at version <version1> and <version2>

- metrics <file_name> <version1> <version2>
-- display metrics for the committed file
-- currently displays the additions and deletions at version <version1> and <version2>

## planned improvements
- more verbose cli 
- object oriented coding style
- line counts at version <version1> and <version2>
- path and data complexity
