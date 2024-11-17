import os
import json
import time
import shutil
import difflib
import zipfile
import readline
import cmd

class Repository:
    def __init__(self, repo_dir, user):
        self.user = user
        self.repo_dir = repo_dir
        self.current_branch = "main"

        self.metadata_file = os.path.join(self.repo_dir, f"{self.current_branch}_metadata.json")
        self.versions_dir = os.path.join(self.repo_dir, "versions")

        os.makedirs(self.versions_dir, exist_ok=True)

        # Initialize the main branch if it doesn't exist
        if not os.path.exists(self.metadata_file):
            self.save_branch_metadata("main", {"files": {}, "commits": [], "tags": {}})
        else:
            print(f"Loaded repository at {self.repo_dir}")

    def validate_file_path(self, file_path):
        """Checks if the file exists and is accessible"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Error: File '{file_path}' does not exist")
        if not os.path.isfile(file_path):
            raise ValueError(f"Error: '{file_path}' is not a valid file")

    def load_branch_metadata(self, branch_name):
        """Loads metadata for a specific branch from its dedicated file"""
        branch_metadata_file = os.path.join(self.repo_dir, f"{branch_name}_metadata.json")
        if os.path.exists(branch_metadata_file):
            try:
                with open(branch_metadata_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                raise ValueError(f"Error: Metadata file for branch '{branch_name}' is corrupted")
        else:
            # Initialize default metadata structure for a new branch
            return {"files": {}, "commits": [], "tags": {}}

    def save_branch_metadata(self, branch_name, metadata):
        """Saves metadata for a specific branch to its dedicated file"""
        branch_metadata_file = os.path.join(self.repo_dir, f"{branch_name}_metadata.json")
        with open(branch_metadata_file, "w") as f:
            json.dump(metadata, f, indent=4)

    def detect_file_changes(self, file_path, last_version):
        """Detects if the file has changed compared to its last committed version"""
        file_name = os.path.basename(file_path)
        last_version_path = os.path.join(self.versions_dir, f"{file_name}_v{last_version}.zip")

        if not os.path.exists(last_version_path):
            print(f"Warning: No previous version of '{file_name}' found. Assuming changes")
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

    def commit_file(self, file_path, version):
        """Commits a file by saving its version in the current branch metadata"""
        try:
            self.validate_file_path(file_path)
        except (FileNotFoundError, ValueError) as e:
            print(e)
            return

        file_name = os.path.basename(file_path)
        branch_metadata = self.load_branch_metadata(self.current_branch)

        # Validate version string
        if not version.isdigit():
            print("Error: Version must be a numeric string")
            return

        # Check for file changes before committing
        if file_name in branch_metadata["files"]:
            last_version = branch_metadata["files"][file_name]
            if not self.detect_file_changes(file_path, last_version):
                print(f"No changes detected in '{file_name}', skipping commit")
                return

        # Save the new version
        try:
            versioned_file = FileVersion(file_name, version, self.versions_dir)
            versioned_file.zip_file(file_path)
        except Exception as e:
            print(f"Error during commit: {e}")
            return

        # Update metadata
        branch_metadata["files"][file_name] = version
        branch_metadata["commits"].append({
            "file": file_name,
            "version": version,
            "user": self.user,
            "timestamp": time.time(),
        })
        self.save_branch_metadata(self.current_branch, branch_metadata)
        print(f"Committed '{file_name}' as version {version} by '{self.user}'")

    def checkout(self, file_name, version):
        """Restores a file from a specific version"""
        try:
            versioned_file = FileVersion(file_name, version, self.versions_dir)
            versioned_file.unzip_file()
            print(f"Checked out {file_name} version {version}.")
        except FileNotFoundError:
            print(f"Error: Version '{version}' of '{file_name}' does not exist")
        except Exception as e:
            print(f"Error during checkout: {e}")

    def log(self):
        """Prints the commit history"""
        with open(self.metadata_file, "r") as f:
            metadata = json.load(f)
        
        print("Commit history:")
        for commit in metadata["commits"]:
            print(f"File: {commit['file']} | Version: {commit['version']}")

    def create_branch(self, branch_name):
        """Creates a new branch based on the current branch"""
        current_metadata = self.load_branch_metadata(self.current_branch)
        self.save_branch_metadata(branch_name, current_metadata)
        print(f"Branch '{branch_name}' created based on '{self.current_branch}'")

    def list_branches(self):
        """Lists all available branches in the repository"""
        branches = []
        for file in os.listdir(self.repo_dir):
            if file.endswith("_metadata.json"):
                branch_name = file.replace("_metadata.json", "")
                branches.append(branch_name)
        return branches
    
    def switch_branch(self, branch_name):
        """Switches to a different branch"""
        branch_metadata_file = os.path.join(self.repo_dir, f"{branch_name}_metadata.json")
        if not os.path.exists(branch_metadata_file):
            print(f"Error: Branch '{branch_name}' does not exist")
            return

        self.current_branch = branch_name
        self.metadata_file = branch_metadata_file
        print(f"Switched to branch '{branch_name}'")

    def merge_branch(self, source_branch):
        """Merges changes from the source branch into the current branch"""
        source_metadata = self.load_branch_metadata(source_branch)
        current_metadata = self.load_branch_metadata(self.current_branch)

        for file_name, source_version in source_metadata["files"].items():
            if file_name not in current_metadata["files"]:
                # No conflict, add the file
                current_metadata["files"][file_name] = source_version
            else:
                # Check for conflicts and incremental changes
                current_version = current_metadata["files"][file_name]
                if source_version != current_version:
                    print(f"Conflict detected in '{file_name}'")
                    choice = input(f"Choose 'current' or 'source' for '{file_name}': ").strip().lower()
                    if choice == "source":
                        current_metadata["files"][file_name] = source_version
                    else:
                        print(f"Kept current version for '{file_name}'")
                else:
                    print(f"No changes detected in '{file_name}', skipping merge")

        self.save_branch_metadata(self.current_branch, current_metadata)
        print(f"Merged '{source_branch}' into '{self.current_branch}'")
                
    def add_tag(self, tag_name):
        """Tags the latest commit on the current branch"""
        branch_metadata = self.load_branch_metadata(self.current_branch)
        if tag_name in branch_metadata["tags"]:
            print(f"Error: Tag '{tag_name}' already exists")
            return

        if not branch_metadata["commits"]:
            print("Error: No commits available to tag")
            return

        last_commit = branch_metadata["commits"][-1]
        branch_metadata["tags"][tag_name] = last_commit
        self.save_branch_metadata(self.current_branch, branch_metadata)
        print(f"Tag '{tag_name}' added to commit: {last_commit}")

    def list_tags(self):
        """Lists all the tags in the repository"""
        with open(self.metadata_file, "r") as f:
            metadata = json.load(f)
        print("Tags:")
        for tag, version in metadata["tags"].items():
            print(f"Tag: {tag}, Version: {version}")

    def lock_repo(self, remote_dir):
        """Locks the repository to prevent concurrent operations"""
        lock_file = os.path.join(remote_dir, "repo.lock")
        while os.path.exists(lock_file):
            print("Repository is locked, waiting...")
            time.sleep(1)
        
        with open(lock_file, "w") as f:
            f.write("locked")

    def unlock_repo(self, remote_dir):
        """Unlocks the repository after the operation is complete"""
        lock_file = os.path.join(remote_dir, "repo.lock")
        if os.path.exists(lock_file):
            os.remove(lock_file)

    def push(self, remote_dir):
        """Pushes the current branch to a remote repository"""
        remote_metadata_file = os.path.join(remote_dir, f"{self.current_branch}_metadata.json")
        current_metadata = self.load_branch_metadata(self.current_branch)
        
        with open(remote_metadata_file, "w") as f:
            json.dump(current_metadata, f, indent=4)
        print(f"Pushed branch '{self.current_branch}' to remote '{remote_dir}'")

    def pull(self, remote_dir):
        """Pulls updates from a remote repository"""
        remote_metadata_file = os.path.join(remote_dir, f"{self.current_branch}_metadata.json")
        if not os.path.exists(remote_metadata_file):
            print(f"Error: Remote branch '{self.current_branch}' does not exist")
            return

        with open(remote_metadata_file, "r") as f:
            remote_metadata = json.load(f)

        current_metadata = self.load_branch_metadata(self.current_branch)
        # Merge logic for metadata here
        current_metadata["files"].update(remote_metadata["files"])
        current_metadata["commits"].extend(remote_metadata["commits"])
        self.save_branch_metadata(self.current_branch, current_metadata)
        print(f"Pulled updates for branch '{self.current_branch}' from remote '{remote_dir}'")

class FileVersion:
    def __init__(self, file_name, version, versions_dir):
        self.file_name = file_name
        self.version = version
        self.zip_name = os.path.join(versions_dir, f"{file_name}_{version}.zip")
    
    def zip_file(self, file_path):
        """Zips a file and stores it as a version"""
        with zipfile.ZipFile(self.zip_name, 'w') as zipf:
            zipf.write(file_path, arcname=self.file_name)
    
    def unzip_file(self, output_dir="."):
        """Unzips the versioned file to the current directory"""
        with zipfile.ZipFile(self.zip_name, 'r') as zipf:
            zipf.extract(self.file_name, output_dir)
    
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
    
    def add_commit(self, file_name, version):
        """Adds a new commit entry to the metadata file"""
        with open(self.metadata_file, "r+") as f:
            metadata = json.load(f)
            metadata["commits"].append({"file": file_name, "version": version})
            f.seek(0)
            json.dump(metadata, f, indent=4)
    
    def get_commits(self):
        """Fetches all commits from the metadata"""
        with open(self.metadata_file, "r") as f:
            return json.load(f)["commits"]


class VCSInterface(cmd.Cmd):
    def __init__(self, repo):
        super().__init__()
        self.repo = repo
        self.prompt = f"(vcs) {repo.user}@{repo.repo_dir}> "
        self.intro = "Welcome to your version control system!"
        readline.set_history_length(100)
        self.intro = """
\033[4m\033[1mVCS commands\033[0m
    \033[1minit\033[0m create an empty zipfile repository
    \033[1mcommit <file_path> <version>\033[0m save a file to the zipfile repository at version <version>
    \033[1mlog <file_path>\033[0m displays the version history of a file in the zipfile repository
    \033[1mcheckout <file_path> <version>\033[0m recovers a file from the zipfile repository at version <version>
    \033[1mcreate_branch <branch_name>\033[0m creates a new branch
    \033[1mswitch_branch <branch_name>\033[0m switches to the specified branch
    \033[1mmerge_branch <source_branch>\033[0m merges changes from the source branch into the current branch.
    \033[1madd_tag <tag_name> <version>\033[0m creates a tag that points to a specific version
    \033[1mlist_tags\033[0m lists all tags associated with specific commits
    \033[1mpush <remote_dir>\033[0m pushes the current branch to a remote directory
    \033[1mpull <remote_dir>\033[0m pulls the latest changes from a remote directory
    \033[1mset_user <user_name>\033[0m sets the current user who will be associated with commits
    \033[1mdiff <file_name> <version1> <version2>\033[0m list the differences in the committed file at version <version1> and <version2>
    \033[1mmetrics <file_name> <version1> <version2>033[0m display metrics for the committed file
    \033[1mexit or quit\033[0m

"""
    def do_commit(self, args):
        """Commit a file. Usage: commit <file_path> <version>"""
        try:
            file_path, version = args.split()
            self.repo.commit_file(file_path, version)
        except ValueError:
            print("Invalid arguments! Use: commit <file_path> <version>")

    def do_log(self, args):
        """Show the commit log"""
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

    def complete_switch_branch(self, text, line, begidx, endidx):
        """Auto-complete branch names for the switch_branch command"""
        with open(self.repo.metadata_file, "r") as f:
            metadata = json.load(f)
        branches = metadata["branches"].keys()
        return [branch for branch in branches if branch.startswith(text)]

    def do_create_branch(self, branch_name):
        """Create a new branch. Usage: create_branch <branch_name>"""
        self.repo.create_branch(branch_name)

    def do_list_branches(self, args):
        """Lists all available branches. Usage: list_branches"""
        branches = self.repo.list_branches()
        print("Available branches:")
        for branch in branches:
            print(f"  - {branch}")

    def do_switch_branch(self, branch_name):
        """Switch to a branch. Usage: switch_branch <branch_name>"""
        self.repo.switch_branch(branch_name)

    def do_merge_branch(self, source_branch):
        """Merge a branch into the current branch. Usage: merge_branch <source_branch>"""
        self.repo.merge_branch(source_branch)

    def do_add_tag(self, args):
        """Add a tag to a version. Usage: add_tag <tag_name> <version>"""
        try:
            tag_name, version = args.split()
            self.repo.add_tag(tag_name, version)
        except ValueError:
            print("Invalid arguments! Use: add_tag <tag_name> <version>")

    def do_list_tags(self, args):
        """List all tags in the repository"""
        self.repo.list_tags()

    def do_push(self, remote_dir):
        """Push changes to a remote repository. Usage: push <remote_directory>"""
        self.repo.push(remote_dir)

    def do_pull(self, remote_dir):
        """Pull changes from a remote repository. Usage: pull <remote_directory>"""
        self.repo.pull(remote_dir)

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
