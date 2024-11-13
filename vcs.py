import os
import json
import difflib
import zipfile
import cmd

class Repository:
    def __init__(self, repo_dir=".vcs"):
        self.repo_dir = repo_dir
        self.versions_dir = os.path.join(repo_dir, "versions")
        self.metadata_file = os.path.join(repo_dir, "metadata.json")
        self.init_repo()

    def init_repo(self):
        """Initializes the repository by creating necessary directories and files."""
        os.makedirs(self.versions_dir, exist_ok=True)
        
        # Initialize metadata if it doesn't exist
        if not os.path.exists(self.metadata_file):
            with open(self.metadata_file, "w") as f:
                json.dump({"commits": [], "current_version": {}}, f)
        
        print("Repository initialized.")
    
    def commit_file(self, file_path, version):
        """Commits a file by creating a new version and updating metadata."""
        file_name = os.path.basename(file_path)
        versioned_file = FileVersion(file_name, version, self.versions_dir)
        versioned_file.zip_file(file_path)

        # Update metadata
        with open(self.metadata_file, "r+") as f:
            metadata = json.load(f)
            metadata["current_version"][file_name] = version
            metadata["commits"].append({
                "file": file_name,
                "version": version
            })
            f.seek(0)
            json.dump(metadata, f, indent=4)
        
        print(f"Committed {file_name} as version {version}.")

    def log(self):
        """Prints the commit history."""
        with open(self.metadata_file, "r") as f:
            metadata = json.load(f)
        
        print("Commit history:")
        for commit in metadata["commits"]:
            print(f"File: {commit['file']} | Version: {commit['version']}")
    
    def checkout(self, file_name, version):
        """Restores a file from a specific version."""
        versioned_file = FileVersion(file_name, version, self.versions_dir)
        versioned_file.unzip_file()
        print(f"Checked out {file_name} version {version}.")


class FileVersion:
    def __init__(self, file_name, version, versions_dir):
        self.file_name = file_name
        self.version = version
        self.zip_name = os.path.join(versions_dir, f"{file_name}_{version}.zip")
    
    def zip_file(self, file_path):
        """Zips a file and stores it as a version."""
        with zipfile.ZipFile(self.zip_name, 'w') as zipf:
            zipf.write(file_path, arcname=self.file_name)
    
    def unzip_file(self, output_dir="."):
        """Unzips the versioned file to the current directory."""
        with zipfile.ZipFile(self.zip_name, 'r') as zipf:
            zipf.extract(self.file_name, output_dir)
    
    def show_diff(self, other_version):
        """Displays the differences between this version and another version."""
        with zipfile.ZipFile(self.zip_name, 'r') as zipf1, \
             zipfile.ZipFile(other_version.zip_name, 'r') as zipf2:
            
            file1_content = zipf1.read(self.file_name).decode('utf-8').splitlines()
            file2_content = zipf2.read(other_version.file_name).decode('utf-8').splitlines()
        
        diff = difflib.unified_diff(file1_content, file2_content, 
                                    fromfile=f"{self.file_name}_{self.version}",
                                    tofile=f"{other_version.file_name}_{other_version.version}")

        for line in diff:
            print(line)

    def calculate_metrics(self, other_version):
        """Displays the differences between this version and another version."""
        with zipfile.ZipFile(self.zip_name, 'r') as zipf1, \
             zipfile.ZipFile(other_version.zip_name, 'r') as zipf2:
            
            file1_content = zipf1.read(self.file_name).decode('utf-8').splitlines()
            file2_content = zipf2.read(other_version.file_name).decode('utf-8').splitlines()
        
        diff = difflib.unified_diff(file1_content, file2_content, 
                                    fromfile=f"{self.file_name}_{self.version}",
                                    tofile=f"{other_version.file_name}_{other_version.version}")
        
        additions = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        deletions = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))

        print(f"Changes between {self.file_name} {self.version1} and {other_version.version}:")
        print(f"  Additions: {additions}")
        print(f"  Deletions: {deletions}")


class CommitLog:
    def __init__(self, metadata_file):
        self.metadata_file = metadata_file
    
    def add_commit(self, file_name, version):
        """Adds a new commit entry to the metadata file."""
        with open(self.metadata_file, "r+") as f:
            metadata = json.load(f)
            metadata["commits"].append({"file": file_name, "version": version})
            f.seek(0)
            json.dump(metadata, f, indent=4)
    
    def get_commits(self):
        """Fetches all commits from the metadata."""
        with open(self.metadata_file, "r") as f:
            return json.load(f)["commits"]


class VCSInterface(cmd.Cmd):
    prompt = "vcs> "

    def __init__(self, repository):
        super().__init__()
        self.repo = repository

    def do_commit(self, args):
        """Commit a file. Usage: commit <file_path> <version>"""
        try:
            file_path, version = args.split()
            self.repo.commit_file(file_path, version)
        except ValueError:
            print("Invalid arguments! Use: commit <file_path> <version>")

    def do_log(self, args):
        """Show the commit log."""
        self.repo.log()

    def do_checkout(self, args):
        """Checkout a specific version. Usage: checkout <file_name> <version>"""
        try:
            file_name, version = args.split()
            self.repo.checkout(file_name, version)
        except ValueError:
            print("Invalid arguments! Use: checkout <file_name> <version>")
    
    def do_diff(self, args):
        """Show diff between two versions. Usage: diff <file_name> <version1> <version2>"""
        try:
            file_name, version1, version2 = args.split()
            version1_obj = FileVersion(file_name, version1, self.repo.versions_dir)
            version2_obj = FileVersion(file_name, version2, self.repo.versions_dir)
            version1_obj.show_diff(version2_obj)
        except ValueError:
            print("Invalid arguments! Use: diff <file_name> <version1> <version2>")

    def do_metrics(self, args):
        """Usage: metrics <file_name> <version1> <version2>"""
        try:
            file_name, version1, version2 = args.split()
            version1_obj = FileVersion(file_name, version1, self.repo.versions_dir)
            version2_obj = FileVersion(file_name, version2, self.repo.versions_dir)
            version1_obj.calculate_metrics(version2_obj)
        except ValueError:
            print("Invalid arguments! Use: metrics <file_name> <version1> <version2>")

    def do_exit(self, args):
        """Exit the VCS interface."""
        print("Exiting...")
        return True
    
    def do_quit(self, args):
        """Exit the VCS interface."""
        print("Exiting...")
        return True


if __name__ == '__main__':
    repo = Repository()
    vcs_interface = VCSInterface(repo)
    vcs_interface.cmdloop()    
