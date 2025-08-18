import subprocess
from typing import List, Optional, Callable
from logger.log_wrapper import get_logger
from tools.context import ToolsContext


def _run_git_command(command: List[str], cwd: Optional[str] = None) -> str:
    """Helper function to run a git command and return the output."""
    try:
        process = subprocess.run(
            ["git"] + command,
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd,
        )
        return process.stdout.strip()
    except FileNotFoundError:
        return "Error: 'git' command not found. Please ensure Git is installed and in your PATH."
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr.strip() else e.stdout.strip()
        return f"Error executing git command: {e}\nOutput: {error_msg}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"


def get_tools(tools_context: ToolsContext):
    """Git Operations Tools"""
    
    def init(self, work_dir: str):
        self.work_dir = work_dir
        self.logger = get_logger("tool:git", __name__)
    
    self = type("Self", (), {})()
    init(self, tools_context.agent_work_dir)

    def git_status() -> str:
        """
        Shows the working tree status.
        """
        return _run_git_command(["status"], cwd=self.work_dir)

    def git_add(files: str = ".") -> str:
        """
        Add file contents to the index (staging area).
        """
        result = _run_git_command(["add", files], cwd=self.work_dir)
        if "Error" not in result:
            return f"Successfully added '{files}' to staging area."
        return result

    def git_commit(message: str, amend: bool = False) -> str:
        """
        Record changes to the repository.
        """
        cmd = ["commit", "-m", message]
        if amend:
            cmd.append("--amend")
        
        result = _run_git_command(cmd, cwd=self.work_dir)
        if "Error" not in result:
            return f"Successfully committed with message: '{message}'"
        return result

    def git_push(remote: str = "origin", branch: str = "", force: bool = False) -> str:
        """
        Update remote refs along with associated objects.
        """
        cmd = ["push", remote]
        if branch:
            cmd.append(branch)
        if force:
            cmd.append("--force")
        
        result = _run_git_command(cmd, cwd=self.work_dir)
        if "Error" not in result:
            return f"Successfully pushed to {remote}" + (f"/{branch}" if branch else "")
        return result

    def git_pull(remote: str = "origin", branch: str = "") -> str:
        """
        Fetch from and integrate with another repository or a local branch.
        """
        cmd = ["pull", remote]
        if branch:
            cmd.append(branch)
        
        result = _run_git_command(cmd, cwd=self.work_dir)
        if "Error" not in result or "Already up to date" in result:
            return f"Successfully pulled from {remote}" + (f"/{branch}" if branch else "")
        return result

    def git_fetch(remote: str = "origin") -> str:
        """
        Download objects and refs from another repository.
        """
        result = _run_git_command(["fetch", remote], cwd=self.work_dir)
        if "Error" not in result:
            return f"Successfully fetched from {remote}"
        return result

    def git_branch_list( all_branches: bool = False) -> str:
        """
        List, create, or delete branches.
        """
        cmd = ["branch"]
        if all_branches:
            cmd.append("-a")
        
        return _run_git_command(cmd, cwd=self.work_dir)

    def git_branch_create( branch_name: str, checkout: bool = True) -> str:
        """
        Create a new branch.
        """
        if checkout:
            result = _run_git_command(["checkout", "-b", branch_name], cwd=self.work_dir)
            if "Error" not in result:
                return f"Successfully created and switched to branch '{branch_name}'"
        else:
            result = _run_git_command(["branch", branch_name], cwd=self.work_dir)
            if "Error" not in result:
                return f"Successfully created branch '{branch_name}'"
        
        return result

    def git_checkout( branch_name: str) -> str:
        """
        Switch branches or restore working tree files.
        """
        result = _run_git_command(["checkout", branch_name], cwd=self.work_dir)
        if "Error" not in result:
            return f"Successfully switched to branch '{branch_name}'"
        return result

    def git_merge( branch_name: str, no_ff: bool = False) -> str:
        """
        Join two or more development histories together.
        """
        cmd = ["merge", branch_name]
        if no_ff:
            cmd.append("--no-ff")
        
        result = _run_git_command(cmd, cwd=self.work_dir)
        if "Error" not in result:
            return f"Successfully merged branch '{branch_name}'"
        return result

    def git_stash( message: str = "", pop: bool = False, list_stashes: bool = False) -> str:
        """
        Stash changes in a dirty working directory away.
        """
        if list_stashes:
            return _run_git_command(["stash", "list"], cwd=self.work_dir)
        elif pop:
            result = _run_git_command(["stash", "pop"], cwd=self.work_dir)
            if "Error" not in result:
                return "Successfully popped stash"
            return result
        else:
            cmd = ["stash"]
            if message:
                cmd.extend(["push", "-m", message])
            
            result = _run_git_command(cmd, cwd=self.work_dir)
            if "Error" not in result:
                return f"Successfully stashed changes" + (f" with message: '{message}'" if message else "")
            return result

    def git_log( oneline: bool = True, max_count: int = 10) -> str:
        """
        Show commit logs.
        """
        cmd = ["log", f"--max-count={max_count}"]
        if oneline:
            cmd.append("--oneline")
        
        return _run_git_command(cmd, cwd=self.work_dir)

    def git_diff( cached: bool = False, file_path: str = "") -> str:
        """
        Show changes between commits, commit and working tree, etc.
        """
        cmd = ["diff"]
        if cached:
            cmd.append("--cached")
        if file_path:
            cmd.append(file_path)
        
        return _run_git_command(cmd, cwd=self.work_dir)

    def git_reset( mode: str = "mixed", commit: str = "HEAD") -> str:
        """
        Reset current HEAD to the specified state.
        """
        valid_modes = ["soft", "mixed", "hard"]
        if mode not in valid_modes:
            return f"Error: Invalid reset mode '{mode}'. Valid modes are: {', '.join(valid_modes)}"
        
        cmd = ["reset", f"--{mode}", commit]
        result = _run_git_command(cmd, cwd=self.work_dir)
        if "Error" not in result:
            return f"Successfully reset to {commit} with mode '{mode}'"
        return result

    def git_remote_list( verbose: bool = True) -> str:
        """
        List remote repositories.
        """
        cmd = ["remote"]
        if verbose:
            cmd.append("-v")
        
        return _run_git_command(cmd, cwd=self.work_dir)

    def git_remote_add( name: str, url: str) -> str:
        """
        Add a remote repository.
        """
        result = _run_git_command(["remote", "add", name, url], cwd=self.work_dir)
        if "Error" not in result:
            return f"Successfully added remote '{name}' with URL '{url}'"
        return result

    def git_tag_list() -> str:
        """
        List existing tags.
        """
        return _run_git_command(["tag"], cwd=self.work_dir)

    def git_tag_create( tag_name: str, message: str = "", annotated: bool = True) -> str:
        """
        Create a new tag.
        """
        if annotated and message:
            cmd = ["tag", "-a", tag_name, "-m", message]
        elif annotated:
            cmd = ["tag", "-a", tag_name]
        else:
            cmd = ["tag", tag_name]
        
        result = _run_git_command(cmd, cwd=self.work_dir)
        if "Error" not in result:
            tag_type = "annotated" if annotated else "lightweight"
            return f"Successfully created {tag_type} tag '{tag_name}'"
        return result

    def git_branch( branch_name: str = "") -> str:
        """
        Create a new branch or list branches.
        If branch_name is provided, creates a new branch.
        If no branch_name, lists branches.
        """
        if branch_name:
            return git_branch_create(branch_name, checkout=False)
        else:
            return git_branch_list()

    def git_remote() -> str:
        """
        List remote repositories.
        """
        return git_remote_list()

    def git_clone( url: str, directory: str = "") -> str:
        """
        Clone a repository into a new directory.
        """
        cmd = ["clone", url]
        if directory:
            cmd.append(directory)
        
        result = _run_git_command(cmd, cwd=self.work_dir)
        if "Error" not in result:
            target = directory if directory else url.split('/')[-1].replace('.git', '')
            return f"Successfully cloned repository to '{target}'"
        return result

    def git_clean( force: bool = True, directories: bool = False) -> str:
        """
        Remove untracked files from the working tree.
        """
        cmd = ["clean"]
        if force:
            cmd.append("-f")
        if directories:
            cmd.append("-d")
        
        result = _run_git_command(cmd, cwd=self.work_dir)
        if "Error" not in result:
            return "Successfully cleaned working directory"
        return result

    def git_show( ref: str = "HEAD") -> str:
        """
        Show various types of objects.
        """
        return _run_git_command(["show", ref], cwd=self.work_dir)

    def git_stash_pop() -> str:
        """
        Apply and remove the latest stash.
        """
        result = _run_git_command(["stash", "pop"], cwd=self.work_dir)
        if "Error" not in result:
            return "Successfully popped stash"
        return result
    
    # Return list of tools
    return [
        git_status,
        git_add,
        git_commit,
        git_push,
        git_pull,
        git_fetch,
        git_branch_list,
        git_branch_create,
        git_checkout,
        git_merge,
        git_stash,
        git_log,
        git_diff,
        git_reset,
        git_remote_list,
        git_remote_add,
        git_tag_list,
        git_tag_create,
        git_clean,
        git_show,
        git_stash_pop,
        git_branch,
        git_remote,
    ] 