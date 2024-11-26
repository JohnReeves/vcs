import os
import re
import cmd
import json
import time
import difflib
import zipfile
import datetime


class VersionNumber:
    def __init__(self, major=0, minor=0):
        self.major = major
        self.minor = minor

    def __str__(self):
        """Returns the version as a string in 'major.minor' format"""
        return f"{self.major}.{self.minor}"
    
    @classmethod
    def parse(cls, version_str):
        """ Parses a version string in the form 'major.minor' and returns a VersionNumber instance"""
        if not re.match(r'^\d+\.\d+$', version_str):
            raise ValueError("Version number must be in the format 'major.minor' with integers")
        major, minor = map(int, version_str.split('.'))
        return cls(major, minor)

    def auto_increment(self):
        """ Returns the next minor version number, keeping the major version constant"""
        return VersionNumber(self.major, self.minor + 1)

    def is_consecutive(self, last_version):
        """Validates that this version is consecutive with the last version"""
        if self.major == last_version.major:
            return self.minor == last_version.minor + 1
        return False

    @staticmethod
    def validate_version(version, commit_log):
        """Validates that the version is unique and consecutive with the last version in the commit log"""
        if version in commit_log:
            raise ValueError(f"Version {version} already exists in the commit log")
        if commit_log:
            last_version = VersionNumber.parse(commit_log[-1]['version'])
            if not version.is_consecutive(last_version):
                raise ValueError(
                    f"Version {version} is not consecutive with the last version {last_version}"
                )


class Repository:
    def __init__(self, repo_dir, user):
        self.user = user
        self.repo_dir = os.path.join(repo_dir, "_versions")
        os.makedirs(self.repo_dir, exist_ok=True)

        self.current_branch = "main"
        self.remote_repo = None  # Simulating a remote repository
        self.locked = False  # Remote repository lock status
        self.metadata_file = os.path.join(self.repo_dir, f"{self.current_branch}_metadata.json")

        self.commit_log = CommitLog(self.metadata_file)

    # --- commit and log methods ---
    def commit_file(self, file_path):
        """Commit a file with a specific version"""
        if not os.path.exists(file_path):
            print(f"Error: File '{file_path}' does not exist")
            return

        suggested_version = self.commit_log.get_next_version(file_path)
        print(f"Commit {file_path} at version: {suggested_version}: press enter to continue, or type a new version number: ", end="")
        user_input = input().strip() or str(suggested_version)

        try:
            version = str(VersionNumber.parse(user_input))
            self.commit_log.validate_version(file_path, version)
        except ValueError as e:
            print(f"error {e}")
            return

        # Detect changes before committing
        last_commit = self.commit_log.get_last_commit(file_path)
        if last_commit:
            last_version = last_commit["version"]
            if not self.detect_file_changes(file_path, last_version):
                print(f"No changes detected in '{file_path}', skipping commit")
                return

        # Create versioned file and add commit
        versioned_file = FileVersion(file_path, version, self.repo_dir)
        versioned_file.zip_file(file_path)
        self.commit_log.add_commit(file_path, version, self.user)
        print(f"Committed '{file_path}' as version {version}")

    def detect_file_changes(self, file_path, last_version):
        """Detects if the file has changed compared to its last committed version"""
        file_name = os.path.basename(file_path)
        last_version_path = os.path.join(self.repo_dir, f"{file_name}_{last_version}.zip")

        if not os.path.exists(last_version_path):
            print(f"Warning: No previous version of '{file_name}' found")
            return True

        try:
            with open(file_path, "rb") as current_file:
                current_data = current_file.read()

            with zipfile.ZipFile(last_version_path, "r") as zip_file:
                with zip_file.open(file_name, "r") as previous_file:
                    previous_data = previous_file.read()

            return current_data != previous_data
        except Exception as e:
            print(f"Error comparing versions of '{file_name}': {e}")
            return True

    def log(self, filename=None):
        """Print the commit log for a file or all files"""
        log = self.commit_log.get_commit_log(filename)
        if not log:
            print(f"No commits found for '{filename}'" if filename else "No commits in the repository")
        else:
            for commit in log:
                print(f"File: {commit['file']} | Version: {commit['version']} | User: {commit['user']} | Timestamp: {time.ctime(commit['timestamp'])}")

    def list_files(self):
        """List all files in the repository"""
        files = self.commit_log.get_files()
        if not files:
            print("No files in the repository")
        else:
            print("Files in repository:")
            for file in files:
                print(f"  - {file} (Latest Version: {self.commit_log.get_version(file)})")

    def rollback_file(self, file_name, version):
        """Rollback a file to a specific version"""
        versioned_file = FileVersion(file_name, version, self.repo_dir)
        print(file_name, version, self.repo_dir)

        if not versioned_file.restore_file(versioned_file):
            print(f"Error: Version '{version}' of file '{file_name}' not found")
            return
        print(f"File '{file_name}' rolled back to version '{version}'")

    def rollback_commit(self, commit_index):
        """Rollback to a specific commit"""
        commits = self.commit_log.get_commit_log()
        if commit_index >= len(commits) or commit_index < 0:
            print("Error: Invalid commit index")
            return
        target_commit = commits[commit_index]
        file_name = target_commit["file"]
        version = target_commit["version"]
        self.rollback_file(file_name, version)

    # --- branch management ---
    def create_branch(self, branch_name):
        """Create a new branch."""
        branch_metadata_file = os.path.join(self.repo_dir, f"{branch_name}_metadata.json")
        if os.path.exists(branch_metadata_file):
            print(f"Branch '{branch_name}' already exists.")
            return
        with open(branch_metadata_file, "w") as f:
            json.dump({"files": {}, "commits": [], "tags": {}}, f)
        print(f"Branch '{branch_name}' created.")

    def switch_branch(self, branch_name):
        """Switch to an existing branch."""
        branch_metadata_file = os.path.join(self.repo_dir, f"{branch_name}_metadata.json")
        if not os.path.exists(branch_metadata_file):
            print(f"Branch '{branch_name}' does not exist.")
            return
        self.current_branch = branch_name
        self.metadata_file = branch_metadata_file
        self.commit_log = CommitLog(self.metadata_file)
        print(f"Switched to branch '{branch_name}'.")

    def list_branches(self):
        """List all branches in the repository."""
        branches = []
        for file_name in os.listdir(self.repo_dir):
            if file_name.endswith("_metadata.json"):
                branches.append(file_name.replace("_metadata.json", ""))
        if branches:
            print("Branches:")
            for branch in branches:
                print(f"  - {branch}")
        else:
            print("No branches found.")

    def merge_branch(self, source_branch):
        """Merge the changes from a source branch into the current branch."""
        if source_branch == self.current_branch:
            print("Error: Cannot merge a branch into itself.")
            return

        source_metadata_file = os.path.join(self.repo_dir, f"{source_branch}_metadata.json")
        if not os.path.exists(source_metadata_file):
            print(f"Error: Branch '{source_branch}' does not exist.")
            return

        # Load metadata from the source branch
        with open(source_metadata_file, "r") as f:
            source_metadata = json.load(f)

        # Merge commits and tags into the current branch
        current_metadata = self.commit_log.metadata
        current_files = current_metadata["files"]
        source_files = source_metadata["files"]

        # Merge files
        for file_name, file_versions in source_files.items():
            if file_name not in current_files:
                current_files[file_name] = file_versions
            else:
                # Merge versions uniquely
                existing_versions = {v["version"] for v in current_files[file_name]}
                for version_entry in file_versions:
                    if version_entry["version"] not in existing_versions:
                        current_files[file_name].append(version_entry)

        # Merge commits
        existing_commits = {(c["file"], c["version"]) for c in current_metadata["commits"]}
        for commit in source_metadata["commits"]:
            if (commit["file"], commit["version"]) not in existing_commits:
                current_metadata["commits"].append(commit)

        # Merge tags
        for tag_name, tag_data in source_metadata.get("tags", {}).items():
            if tag_name not in current_metadata["tags"]:
                current_metadata["tags"][tag_name] = tag_data

        # Save merged metadata
        self.commit_log.save_metadata()
        print(f"Branch '{source_branch}' merged into '{self.current_branch}'.")

    # --- tagging ---
    def create_tag(self, tag_name, file_name, version):
        """Create a tag for a specific file and version"""
        self.commit_log.metadata["tags"][tag_name] = {"file": file_name, "version": version}
        self.commit_log.save_metadata()
        print(f"Tag '{tag_name}' created for file '{file_name}' version '{version}'")

    def list_tags(self):
        """List all tags"""
        tags = self.commit_log.metadata.get("tags", {})
        if not tags:
            print("No tags found")
        else:
            print("Tags:")
            for tag, info in tags.items():
                print(f"  - {tag}: File '{info['file']}' Version '{info['version']}'")

    # --- remote repository management ---
    def push(self):
        """Push changes to the remote repository"""
        if self.locked:
            print("Error: Remote repository is locked")
            return
        if self.remote_repo is None:
            print("Error: No remote repository configured")
            return
        self.remote_repo.update(self.commit_log.metadata)
        print(f"Changes pushed to remote repository for branch '{self.current_branch}'")

    def pull(self):
        """Pull changes from the remote repository"""
        if self.remote_repo is None:
            print("Error: No remote repository configured")
            return
        remote_metadata = self.remote_repo.get_branch_metadata(self.current_branch)
        self.commit_log.metadata = remote_metadata
        self.commit_log.save_metadata()
        print(f"Changes pulled from remote repository for branch '{self.current_branch}'")

    def lock_remote(self):
        """Lock the remote repository to prevent updates"""
        self.locked = True
        print("Remote repository locked")

    def unlock_remote(self):
        """Unlock the remote repository to allow updates"""
        self.locked = False
        print("Remote repository unlocked")


class FileVersion:
    def __init__(self, file_name, version, versions_dir):
        self.file_name = file_name
        self.version = version
        self.versions_dir = versions_dir
        self.zip_name = os.path.join(versions_dir, f"{file_name}_{version}.zip")
    
    def __str__(self):
        """Returns the version as a string in 'major.minor' format"""
        return f"{self.zip_name}"

    def zip_file(self, file_path):
        """Zips a file and stores it as a version"""
        with zipfile.ZipFile(self.zip_name, 'w') as zipf:
            zipf.write(file_path, arcname=self.file_name)
    
    def unzip_file(self, output_dir="."):
        """Unzips the versioned file to the current directory"""
        with zipfile.ZipFile(self.zip_name, 'r') as zipf:
            zipf.extract(self.file_name, output_dir)

    def list_versions(self):
        """List all saved versions of the file from zip archives"""
        versions = [f for f in os.listdir(self.versions_dir) if f.endswith(".zip")]
        if not versions:
            print(f"No versions found for file '{self.file_path}'")
        else:
            print(f"Versions for file '{self.file_path}':")
            for version in versions:
                print(f"  - {os.path.splitext(version)[0]}")
        return [os.path.splitext(v)[0] for v in versions]

    def restore_file(self, version_name):
        """Restore a specific version of the file from a zip archive"""
        version_file = version_name.zip_name
        if not os.path.exists(version_file):
            print(f"Error: Version '{version_name}' does not exist for file '{self.file_name}'")
            return False
        with zipfile.ZipFile(version_file, "r") as zf:
            zf.extract(os.path.basename(self.file_name), os.path.dirname(self.file_name))
        # print(f"File '{self.file_name}' restored to version '{version_name}'")
        return True

    def show_diff(self, other_version):
        """Displays the differences between this version and another version"""
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
        """Displays the differences between this version and another version"""
        with zipfile.ZipFile(self.zip_name, 'r') as zipf1, \
             zipfile.ZipFile(other_version.zip_name, 'r') as zipf2:
            
            file1_content = zipf1.read(self.file_name).decode('utf-8').splitlines()
            file2_content = zipf2.read(other_version.file_name).decode('utf-8').splitlines()
        
        diff = difflib.unified_diff(file1_content, file2_content, 
                                    fromfile=f"{self.file_name}_{self.version}",
                                    tofile=f"{other_version.file_name}_{other_version.version}")
        
        additions = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        deletions = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))

        print(f"Changes between {self.file_name} {self.version} and {other_version.version}:")
        print(f"  Additions: {additions}")
        print(f"  Deletions: {deletions}")


class CommitLog:
    def __init__(self, metadata_file):
        self.metadata_file = metadata_file
        self.metadata = self._load_metadata()

    def _load_metadata(self):
        """Load metadata from the file, initializing if missing or corrupted"""
        try:
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, "r") as f:
                    return json.load(f)
            return {"files": {}, "commits": [], "tags": {}}
        except json.JSONDecodeError:
            print(f"Warning: Metadata file '{self.metadata_file}' is corrupted. Initializing a new metadata structure")
            return {"files": {}, "commits": [], "tags": {}}

    def save_metadata(self):
        """Save the metadata back to the file"""
        with open(self.metadata_file, "w") as f:
            json.dump(self.metadata, f, indent=4)

    def add_commit(self, file_name, version, user):
        """Add a new commit entry"""
        commit_entry = {
            "file": file_name,
            "version": version,
            "user": user,
            "timestamp": time.time(),
        }
        self.metadata["files"][file_name] = version
        self.metadata["commits"].append(commit_entry)
        self.save_metadata()

    def get_commit_log(self, filename=None):
        """Get the commit history for a specific file or all files"""
        if filename:
            return [c for c in self.metadata["commits"] if c["file"] == filename]
        return self.metadata["commits"]

    def get_last_commit(self, filename):
        """Retrieve the last commit entry for a file"""
        commits = self.get_commit_log(filename)
        return commits[-1] if commits else None

    def validate_version(self, file_name, version):
        """Validates that the version is unique and consecutive"""
        if file_name in self.metadata["files"] and self.metadata["files"][file_name] == version:
            raise ValueError(f"Error: Version '{version}' for file '{file_name}' already exists")

        last_commit = self.get_last_commit(file_name)
        if last_commit:
            last_version = VersionNumber.parse(last_commit["version"])
            new_version = VersionNumber.parse(version)
            if not new_version.is_consecutive(last_version):
                raise ValueError(f"Error: Version '{version}' is not consecutive with '{last_version}'")

    def get_files(self):
        """Return a list of all files in the repository"""
        return list(self.metadata["files"].keys())

    def get_version(self, file_name):
        """Get the latest committed version of a file"""
        return self.metadata["files"].get(file_name, None)

    def get_next_version(self, file_name):
        """Get the latest committed version of a file"""
        current_version = self.get_version(file_name)
        major, minor = map(int, current_version.split('.'))
        return VersionNumber(major, minor).auto_increment()


class VCSInterface(cmd.Cmd):
    def __init__(self, repo):
        super().__init__()
        self.repo = repo
        self.prompt = f"(vcs) {repo.user}@{repo.repo_dir}> "
        self.intro = "Welcome to your version control system!"
        self.intro = """
\033[4m\033[1mVCS commands\033[0m
    \033[1minit\033[0m create an empty zipfile repository

\033[1m \033[4mGet started commands\033[0m
    \033[1mset_user <user_name>\033[0m sets the current user who will be associated with commits
    \033[1mcommit <file_path> <version>\033[0m save a file to the zipfile repository at version <version>
    \033[1mcheckout <file_path> <version>\033[0m recovers a file from the zipfile repository at version <version>
    \033[1mlog <file_path>\033[0m displays the version history of a file in the zipfile repository

\033[1m \033[4mBranch commands\033[0m
    \033[1mcreate_branch <branch_name>\033[0m creates a new branch
    \033[1mswitch_branch <branch_name>\033[0m switches to the specified branch
    \033[1mmerge_branch <source_branch>\033[0m merges changes from the source branch into the current branch.

\033[1m \033[4mTagging commands\033[0m
    \033[1mcreate_tag <tag_name> <version>\033[0m creates a tag that points to a specific version
    \033[1mlist_tags\033[0m lists all tags associated with specific commits

\033[1m \033[4mRemote repository commands\033[0m
    \033[1mpush <remote_dir>\033[0m pushes the current branch to a remote directory
    \033[1mpull <remote_dir>\033[0m pulls the latest changes from a remote directory

\033[1m \033[4mCoding metric commands\033[0m
    \033[1mdiff <file_name> <version1> <version2>\033[0m list the differences in the committed file at version <version1> and <version2>
    \033[1mmetrics <file_name> <version1> <version2>033[0m display metrics for the committed file

    \033[1mexit or quit\033[0m

"""
    # --- commit and log commands ---
    def do_commit(self, args):
        """Commit a file. Usage: commit <filename>"""
        filename = args.strip()
        if not filename:
            print("Usage: commit <filename>")
            return
        self.repo.commit_file(filename)

    def do_checkout(self, args):
        """Checkout a specific version. Usage: checkout <file_name> <version>"""
        try:
            file_name, version = args.split()
            self.repo.rollback_file(file_name, version)
        except ValueError:
            print("Invalid arguments! Use: checkout <file_name> <version>")

    def do_log(self, _):
        """Show the commit log"""
        self.repo.log()

    def do_diff(self, args):
        """Show diff between two versions. Usage: diff <file_name> <version1> <version2>"""
        try:
            file_name, version1, version2 = args.split()
            version1_obj = FileVersion(file_name, version1, self.repo.repo_dir)
            version2_obj = FileVersion(file_name, version2, self.repo.repo_dir)
            version1_obj.show_diff(version2_obj)
        except ValueError:
            print("Invalid arguments! Use: diff <file_name> <version1> <version2>")

    def do_metrics(self, args):
        """Usage: metrics <file_name> <version1> <version2>"""
        try:
            file_name, version1, version2 = args.split()
            version1_obj = FileVersion(file_name, version1, self.repo.repo_dir)
            version2_obj = FileVersion(file_name, version2, self.repo.repo_dir)
            version1_obj.calculate_metrics(version2_obj)
        except ValueError:
            print("Invalid arguments! Use: metrics <file_name> <version1> <version2>")

    # --- branch commands ---
    def do_create_branch(self, branch_name):
        """Create a new branch. Usage: create_branch <branch_name>"""
        self.repo.create_branch(branch_name)

    def do_list_branches(self, _):
        """Lists all available branches. Usage: list_branches"""
        branches = self.repo.list_branches()
        print("Available branches:")
        for branch in branches:
            print(f"  - {branch}")

    def do_switch_branch(self, args):
        """Switch to a branch. Usage: switch_branch <branch_name>"""
        try:
            source_branch = args.split()
            self.repo.switch_branch(source_branch)
        except:
            print("Invalid arguments! Useage: switch_branch <source_branch>")

    def complete_switch_branch(self, text, line, begidx, endidx):
        """Auto-complete branch names for the switch_branch command"""
        with open(self.repo.metadata_file, "r") as f:
            metadata = json.load(f)
        branches = metadata["branches"].keys()
        return [branch for branch in branches if branch.startswith(text)]
    
    def do_merge_branch(self, args):
        """Merge a branch into the current branch. Usage: merge_branch <source_branch>"""
        try:
            source_branch = args.split()
            self.repo.merge_branch(source_branch)
        except:
            print("Invalid arguments! Useage: merge_branch <source_branch>")

    # --- tagging commands ---
    def do_create_tag(self, args):
        """Add a tag to a version. Usage: create_tag <tag_name> <filename> <version>"""
        try:
            tag_name, file_name, version = args.split()
            self.repo.create_tag(tag_name, version)
        except ValueError:
            print("Invalid arguments! Use: create_tag <tag_name> <version>")

    def do_list_tags(self, _):
        """List all tags in the repository"""
        self.repo.list_tags()

    # --- remote repository commands ---
    def do_push(self, _):
        """Push changes to a remote repository. Usage: push <remote_directory>"""
        self.repo.push()

    def do_pull(self, _):
        """Pull changes from a remote repository. Usage: pull <remote_directory>"""
        self.repo.pull()

    # --- miscellaneous commands ---
    def do_set_user(self, user_name):
        """Set the user for the repository. Usage: set_user <user_name>"""
        self.repo.user = user_name
        print(f"User set to {user_name}")

    def do_help(self, _):
        print(self.intro)

    def do_exit(self, _):
        """Exit the VCS interface"""
        print("Exiting...")
        return True
    
    def do_quit(self, _):
        """Exit the VCS interface"""
        print("Exiting...")
        return True


if __name__ == '__main__':
    user_name = input("Enter your username: ")
    repository = "./"
    repo = Repository(repo_dir=repository, user=user_name)
    interface = VCSInterface(repo)
    interface.cmdloop() 
