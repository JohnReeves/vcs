# vcs
a version control system in python
## the basic ideas
- create a cli to
  - initialise the repository
  - commit files and track change
  - show differences between versions
  - display simple metrics
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
