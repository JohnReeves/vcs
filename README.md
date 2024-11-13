# vcs
a version control system in python
## cli available commands
- `init` to create an empty zipfile repository
- `commit <file_path> <version>` save a file to the zipfile repository at version <version>
- `diff <file_name> <version1> <version2>` list the differences in the committed file at version <version1> and <version2>
- `metrics <file_name> <version1> <version2>` displays the additions and deletions at version <version1> and <version2>
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
## planned improvements
- more verbose cli 
- object oriented coding style
- line counts at version <version1> and <version2>
- path and data complexity
