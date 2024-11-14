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
  - create an empty zipfile repository
- commit <file_path> <version>
  - save a file to the zipfile repository at version <version>
- checkout <file_path> <version>
  - recovers a file from the zipfile repository at version <version>
- log <file_path> <version>
  - displays the version history of a file in the zipfile repository
- diff <file_name> <version1> <version2>
  - list the differences in the committed file at version <version1> and <version2>
- metrics <file_name> <version1> <version2>
  - display metrics for the committed file
  - currently displays the additions and deletions at version <version1> and <version2>
- create_branch <branch_name>
  - creates a new branch
- switch_branch <branch_name>
  - switches to the specified branch
- merge_branch <source_branch>
  - merges changes from the source branch into the current branch.
- add_tag <tag_name> <version>
  - creates a tag that points to a specific version
- list_tags
  - lists all tags associated with specific commits
- push <remote_dir>
  - pushes the current branch to a remote directory
- pull <remote_dir>
  - pulls the latest changes from a remote directory
- set_user <user_name>
  - sets the current user who will be associated with commits

## planned improvements
- more verbose cli 
- object oriented coding style
- push & pull to a 'remote' repository
- feature branches
- support multiple users
  - user names
  - remote repo locking
- line count, path and data complexity
