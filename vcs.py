import os
import json
import shutil
import difflib

REPO_DIR = ".vcs"
VERSIONS_DIR = os.path.join(REPO_DIR, "versions")
METADATA_FILE = os.path.join(REPO_DIR, "metadata.json")

def init_repo():
    os.makedirs(VERSIONS_DIR, exist_ok=True)
    
    if not os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "w") as f:
            json.dump({"commits": [], "current_version": {}}, f)
    
    print("Repository initialized.")


def commit_file(file_path, version):
    file_name = os.path.basename(file_path)
    versioned_file = os.path.join(VERSIONS_DIR, f"{file_name}_{version}.txt")

    shutil.copy(file_path, versioned_file)

    with open(METADATA_FILE, "r+") as f:
        metadata = json.load(f)
        metadata["current_version"][file_name] = version
        metadata["commits"].append({
            "file": file_name,
            "version": version
        })
        f.seek(0)
        json.dump(metadata, f, indent=4)
    
    print(f"Committed {file_name} as version {version}.")


def show_diff(file_name, version1, version2):
    file1 = os.path.join(VERSIONS_DIR, f"{file_name}_{version1}.txt")
    file2 = os.path.join(VERSIONS_DIR, f"{file_name}_{version2}.txt")

    with open(file1, "r") as f1, open(file2, "r") as f2:
        diff = difflib.unified_diff(f1.readlines(), f2.readlines(), 
                                    fromfile=f"{file_name}_{version1}",
                                    tofile=f"{file_name}_{version2}")

    for line in diff:
        print(line, end="")

def calculate_metrics(file_name, version1, version2):
    file1 = os.path.join(VERSIONS_DIR, f"{file_name}_{version1}.txt")
    file2 = os.path.join(VERSIONS_DIR, f"{file_name}_{version2}.txt")

    with open(file1, "r") as f1, open(file2, "r") as f2:
        lines1 = f1.readlines()
        lines2 = f2.readlines()
    
    diff = difflib.unified_diff(lines1, lines2)

    additions = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
    deletions = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))

    print(f"Changes between {file_name} {version1} and {version2}:")
    print(f"  Additions: {additions}")
    print(f"  Deletions: {deletions}")


if __name__ == "__main__":
    init_repo()
    commit_file("file1.txt", "1.0")
    show_diff("file1.txt", "1.0", "1.1")
    calculate_metrics("file1.txt", "1.0", "1.1")

