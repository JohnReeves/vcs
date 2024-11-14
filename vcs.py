import os
import json
import difflib
import zipfile
import shutil
import cmd

class Repository:
    def __init__(self, user, repo_dir=".vcs"):
        self.user = user 
        self.repo_dir = repo_dir
        self.versions_dir = os.path.join(repo_dir, "versions")
        self.metadata_file = os.path.join(repo_dir, "metadata.json")
        self.current_branch = "main"  # Default branch is 'main'
        self.init_repo()

    def init_repo(self):
        """Initializes the repository by creating necessary directories and files."""
        os.makedirs(self.versions_dir, exist_ok=True)
        
        # Initialize metadata if it doesn't exist
        if not os.path.exists(self.metadata_file):
            with open(self.metadata_file, "w") as f:
                json.dump({
                    "branches": {"main": {}},  # Initialize with 'main' branch
                    "commits": [],
                    "current_version": {},
                    "tags": {}
                }, f)
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
                "version": version,
                "user": self.user  # Associate commit with user
            })
            f.seek(0)
            json.dump(metadata, f, indent=4)
        
        print(f"Committed {file_name} as version {version} by {self.user}.")

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

    def create_branch(self, branch_name):
        """Creates a new branch based on the current branch state."""
        with open(self.metadata_file, "r+") as f:
            metadata = json.load(f)
            if branch_name in metadata["branches"]:
                print(f"Branch {branch_name} already exists.")
            else:
                # Create the new branch based on the current branch state
                metadata["branches"][branch_name] = metadata["branches"][self.current_branch].copy()
                f.seek(0)
                json.dump(metadata, f, indent=4)
                print(f"Branch {branch_name} created.")

    def switch_branch(self, branch_name):
        """Switches to the specified branch."""
        with open(self.metadata_file, "r") as f:
            metadata = json.load(f)
        
        if branch_name in metadata["branches"]:
            self.current_branch = branch_name
            print(f"Switched to branch {branch_name}.")
        else:
            print(f"Branch {branch_name} does not exist.")  

    def merge_branch(self, source_branch):
        """Merges changes from the source branch into the current branch."""
        with open(self.metadata_file, "r+") as f:
            metadata = json.load(f)
            if source_branch not in metadata["branches"]:
                print(f"Branch {source_branch} does not exist.")
                return
            
            # Merge all files from the source branch into the current branch
            source_files = metadata["branches"][source_branch]
            current_files = metadata["branches"][self.current_branch]

            for file_name, source_version in source_files.items():
                if file_name not in current_files:
                    # No conflict, directly merge
                    current_files[file_name] = source_version
                else:
                    # Handle conflict (just print diff for now, could add user input to resolve)
                    version1 = FileVersion(file_name, current_files[file_name], self.versions_dir)
                    version2 = FileVersion(file_name, source_version, self.versions_dir)
                    print(f"Conflict in {file_name}:")
                    version1.show_diff(version2)
                    # Simple conflict resolution: pick source branch's version
                    current_files[file_name] = source_version
            
            # Update the metadata
            metadata["branches"][self.current_branch] = current_files
            f.seek(0)
            json.dump(metadata, f, indent=4)
        print(f"Merged {source_branch} into {self.current_branch}.")
    
    def add_tag(self, tag_name, version):
        """Adds a tag to a specific version."""
        with open(self.metadata_file, "r+") as f:
            metadata = json.load(f)
            if tag_name in metadata["tags"]:
                print(f"Tag {tag_name} already exists.")
            else:
                metadata["tags"][tag_name] = version
                f.seek(0)
                json.dump(metadata, f, indent=4)
                print(f"Tag {tag_name} added to version {version}.")
    
    def list_tags(self):
        """Lists all the tags in the repository."""
        with open(self.metadata_file, "r") as f:
            metadata = json.load(f)
        print("Tags:")
        for tag, version in metadata["tags"].items():
            print(f"Tag: {tag}, Version: {version}")

    def push(self, remote_dir):
        """Pushes the current branch to the remote repository."""
        if not os.path.exists(remote_dir):
            print(f"Remote directory {remote_dir} does not exist.")
            return

        # Copy current branch's metadata to the remote
        remote_metadata_file = os.path.join(remote_dir, "metadata.json")
        shutil.copy(self.metadata_file, remote_metadata_file)
        shutil.copytree(self.versions_dir, os.path.join(remote_dir, "versions"), dirs_exist_ok=True)
        print(f"Pushed branch {self.current_branch} to remote repository.")

    def pull(self, remote_dir):
        """Pulls the latest changes from the remote repository."""
        if not os.path.exists(remote_dir):
            print(f"Remote directory {remote_dir} does not exist.")
            return

        # Pull metadata and versioned files from remote
        remote_metadata_file = os.path.join(remote_dir, "metadata.json")
        shutil.copy(remote_metadata_file, self.metadata_file)
        shutil.copytree(os.path.join(remote_dir, "versions"), self.versions_dir, dirs_exist_ok=True)
        print(f"Pulled latest changes from remote repository.")


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

        print(f"Changes between {self.file_name} {self.version} and {other_version.version}:")
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
    intro = """
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
    \033[1mcdiff <file_name> <version1> <version2>\033[0m list the differences in the committed file at version <version1> and <version2>
    \033[1mmetrics <file_name> <version1> <version2>033[0m display metrics for the committed file
    \033[1mexit or quit\033[0m

"""
    prompt = "(vcs) $ "

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

    def do_create_branch(self, args):
        """Create a new branch. Usage: create_branch <branch_name>"""
        self.repo.create_branch(args)

    def do_switch_branch(self, args):
        """Switch to a branch. Usage: switch_branch <branch_name>"""
        self.repo.switch_branch(args)

    def do_merge_branch(self, args):
        """Merge a branch into the current branch. Usage: merge_branch <source_branch>"""
        self.repo.merge_branch(args)

    def do_add_tag(self, args):
        """Add a tag to a version. Usage: add_tag <tag_name> <version>"""
        try:
            tag_name, version = args.split()
            self.repo.add_tag(tag_name, version)
        except ValueError:
            print("Invalid arguments! Use: add_tag <tag_name> <version>")

    def do_list_tags(self, args):
        """List all tags in the repository."""
        self.repo.list_tags()

    def do_push(self, args):
        """Push changes to a remote repository. Usage: push <remote_directory>"""
        self.repo.push(args)

    def do_pull(self, args):
        """Pull changes from a remote repository. Usage: pull <remote_directory>"""
        self.repo.pull(args)

    def do_set_user(self, args):
        """Set the user for the repository. Usage: set_user <user_name>"""
        self.repo.user = args
        print(f"User set to {args}.")

    def do_exit(self, args):
        """Exit the VCS interface."""
        print("Exiting...")
        return True
    
    def do_quit(self, args):
        """Exit the VCS interface."""
        print("Exiting...")
        return True


if __name__ == '__main__':
    user_name = input("Enter your username: ")
    repo = Repository(user=user_name)
    interface = VCSInterface(repo)
    interface.cmdloop() 
