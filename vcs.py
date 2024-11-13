import os
import json
import shutil
import difflib
import zipfile
import cmd

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
    zip_name = os.path.join(VERSIONS_DIR, f"{file_name}_{version}.zip")

    # Create a zip archive for the version
    with zipfile.ZipFile(zip_name, 'w') as zipf:
        zipf.write(file_path, arcname=file_name)

    # Update metadata
    with open(METADATA_FILE, "r+") as f:
        metadata = json.load(f)
        metadata["current_version"][file_name] = version
        metadata["commits"].append({
            "file": file_name,
            "version": version
        })
        f.seek(0)
        json.dump(metadata, f, indent=4)
    
    print(f"Committed {file_name} as version {version} (zipped).")

def show_diff(file_name, version1, version2):
    zip1 = os.path.join(VERSIONS_DIR, f"{file_name}_{version1}.zip")
    zip2 = os.path.join(VERSIONS_DIR, f"{file_name}_{version2}.zip")

    # Extract files from the zip archives
    with zipfile.ZipFile(zip1, 'r') as zipf1, zipfile.ZipFile(zip2, 'r') as zipf2:
        file1_content = zipf1.read(file_name).decode('utf-8').splitlines()
        file2_content = zipf2.read(file_name).decode('utf-8').splitlines()

    diff = difflib.unified_diff(file1_content, file2_content, 
                                fromfile=f"{file_name}_{version1}",
                                tofile=f"{file_name}_{version2}")

    for line in diff:
        print(line)

def calculate_metrics(file_name, version1, version2):
    zip1 = os.path.join(VERSIONS_DIR, f"{file_name}_{version1}.zip")
    zip2 = os.path.join(VERSIONS_DIR, f"{file_name}_{version2}.zip")

    # Extract files from the zip archives
    with zipfile.ZipFile(zip1, 'r') as zipf1, zipfile.ZipFile(zip2, 'r') as zipf2:
        file1_content = zipf1.read(file_name).decode('utf-8').splitlines()
        file2_content = zipf2.read(file_name).decode('utf-8').splitlines()
    
    diff = difflib.unified_diff(file1_content, file2_content)

    additions = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
    deletions = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))

    print(f"Changes between {file_name} {version1} and {version2}:")
    print(f"  Additions: {additions}")
    print(f"  Deletions: {deletions}")


class VCS(cmd.Cmd):
    prompt = "vcs> "

    def do_init(self):
        """Usage: init_repo"""
        try:
            init_repo()
        except ValueError:
            print("Invalid arguments! Use: init")

    def do_commit(self, args):
        """Usage: commit <file_path> <version>"""
        try:
            file_path, version = args.split()
            commit_file(file_path, version)
        except ValueError:
            print("Invalid arguments! Use: commit <file_path> <version>")

    def do_diff(self, args):
        """Usage: diff <file_name> <version1> <version2>"""
        try:
            file_name, version1, version2 = args.split()
            show_diff(file_name, version1, version2)
        except ValueError:
            print("Invalid arguments! Use: diff <file_name> <version1> <version2>")

    def do_metrics(self, args):
        """Usage: metrics <file_name> <version1> <version2>"""
        try:
            file_name, version1, version2 = args.split()
            calculate_metrics(file_name, version1, version2)
        except ValueError:
            print("Invalid arguments! Use: metrics <file_name> <version1> <version2>")

    def do_exit(self, args):
        """Exit the VCS interface."""
        print("Exiting...")
        return True
        

if __name__ == '__main__':
    vcs = VCS()
    vcs.cmdloop()
