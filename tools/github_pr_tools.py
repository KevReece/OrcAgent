from typing import List, Optional, Tuple
import subprocess
from tools.gh_helper import run_gh_command
from logger.log_wrapper import get_logger
from tools.context import ToolsContext


def get_tools(tools_context: ToolsContext):
    """GitHub Pull Request Tools"""
    
    def init(self, work_dir: str, is_integration_test: bool = False):
        """
        Initialize GitHub PR Tools.
        
        Args:
            work_dir: Working directory for git operations
            is_integration_test: Whether this is running in integration test mode
        """
        self.work_dir = work_dir
        self.logger = get_logger("tool:github_pr", __name__)
    
    self = type("Self", (), {})()
    init(self, tools_context.agent_work_dir, tools_context.is_integration_test)

    # --------------------------
    # internal helpers
    # --------------------------
    def _run_git(command: List[str]) -> str:
        try:
            process = subprocess.run(
                ["git"] + command,
                capture_output=True,
                text=True,
                check=True,
                cwd=self.work_dir,
            )
            return process.stdout.strip()
        except FileNotFoundError:
            return "Error: 'git' command not found. Please ensure Git is installed and in your PATH."
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr.strip() else e.stdout.strip()
            return f"Error executing git command: {e}\nOutput: {error_msg}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"

    def _get_repo_name_with_owner() -> Optional[str]:
        result = run_gh_command(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"], cwd=self.work_dir)
        if "Error" in result:
            self.logger.warning(f"Unable to resolve repository nameWithOwner: {result}")
            return None
        return result.strip() if result else None

    def _get_default_branch() -> Optional[str]:
        result = run_gh_command(["repo", "view", "--json", "defaultBranchRef", "-q", ".defaultBranchRef.name"], cwd=self.work_dir)
        if "Error" in result or not result.strip():
            # Fallback to guessing common defaults by checking remote HEAD
            head_ref = _run_git(["symbolic-ref", "refs/remotes/origin/HEAD"])  # returns refs/remotes/origin/main
            if "Error" not in head_ref and head_ref:
                return head_ref.strip().split("/")[-1]
            return None
        return result.strip()

    def _get_current_branch() -> Optional[str]:
        result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])  # returns branch name
        return result.strip() if result and "Error" not in result else None

    def _ensure_branch_exists(branch_name: str) -> Tuple[bool, Optional[str]]:
        # Check if branch exists locally
        check = _run_git(["rev-parse", "--verify", f"refs/heads/{branch_name}"])
        if check and "Error" not in check:
            return True, None
        # Try to create from current HEAD
        create = _run_git(["checkout", "-b", branch_name])
        if "Error" in create:
            return False, create
        return True, None

    def _filter_valid_users(csv_users: str) -> str:
        if not csv_users:
            return ""
        usernames = [u.strip() for u in csv_users.split(",") if u.strip()]
        valid: List[str] = []
        for username in usernames:
            res = run_gh_command(["api", f"users/{username}"] , cwd=self.work_dir)
            if "Error" in res:
                self.logger.info(f"Skipping unknown GitHub user '{username}'")
                continue
            valid.append(username)
        return ",".join(valid)

    def _has_commits_ahead_of_base(head_branch: str, base_branch: str) -> Tuple[bool, Optional[str]]:
        # Ensure we can compare with remote base
        fetch_res = _run_git(["fetch", "origin"])  # ok if already up to date
        if "Error" in fetch_res and "Already up to date" not in (fetch_res or ""):
            return False, fetch_res
        # Count commits in head not in base
        count_res = _run_git(["rev-list", "--count", head_branch, f"^origin/{base_branch}"])
        if "Error" in count_res:
            return False, count_res
        try:
            return int(count_res.strip()) > 0, None
        except ValueError:
            return False, f"Unexpected rev-list output: {count_res}"

    def _has_diff_changes(head_branch: str, base_branch: str) -> Tuple[bool, Optional[str]]:
        """Return True if there are file changes between origin/base and head.

        Uses name-only diff to avoid large outputs and focuses on whether any
        files differ at all. This ensures we only open PRs with actual file
        changes, not just empty or merge commits.
        """
        # Ensure base is up to date
        fetch_res = _run_git(["fetch", "origin"])  # ok if already up to date
        if "Error" in fetch_res and "Already up to date" not in (fetch_res or ""):
            return False, fetch_res
        # Check for any changed file names between base and head
        diff_res = _run_git(["diff", "--name-only", f"origin/{base_branch}..{head_branch}"])
        if "Error" in diff_res:
            return False, diff_res
        return (diff_res.strip() != ""), None

    def gh_pr_create(title: str, body: str = "", base: str = "", head: str = "", 
                     draft: bool = False, assignees: str = "", labels: str = "", 
                     reviewers: str = "", web: bool = False) -> str:
        """
        Create a new pull request.
        
        Args:
            title (str): Title of the pull request.
            body (str): Body/description of the pull request.
            base (str): The base branch (target branch). If empty, uses default.
            head (str): The head branch (source branch). If empty, uses current branch.
            draft (bool): Create as draft PR.
            assignees (str): Comma-separated list of assignees.
            labels (str): Comma-separated list of labels.
            reviewers (str): Comma-separated list of reviewers.
            web (bool): Open PR in web browser after creation.
            
        Returns:
            str: Success message with PR URL or error message.
        """
        # Resolve repo, default branch and current branch
        default_branch = base or _get_default_branch()
        if not default_branch:
            return "Error: Unable to determine base branch for PR creation"

        target_head = head or _get_current_branch()
        if not target_head:
            return "Error: Unable to determine head branch for PR creation"

        # If head explicitly specified and doesn't exist locally, create it
        if head:
            ok, err = _ensure_branch_exists(head)
            if not ok:
                return err or f"Error: failed to create branch '{head}'"

        # Filter reviewers and assignees to only valid GitHub users
        filtered_assignees = _filter_valid_users(assignees)
        filtered_reviewers = _filter_valid_users(reviewers)

        # Prevent PRs without file changes between head and base
        has_changes, err = _has_diff_changes(target_head, default_branch)
        if err:
            return err
        if not has_changes:
            return (
                f"Error: No file changes between '{target_head}' and 'origin/{default_branch}'. "
                "Create changes before opening a PR."
            )

        # Also ensure there is at least one commit ahead of base for robustness
        has_commits, err = _has_commits_ahead_of_base(target_head, default_branch)
        if err:
            return err
        if not has_commits:
            return f"Error: No commits between '{target_head}' and 'origin/{default_branch}'. Create commits before opening a PR."

        cmd = ["pr", "create", "--title", title]
        if body:
            cmd.extend(["--body", body])
        if default_branch:
            cmd.extend(["--base", default_branch])
        if target_head:
            cmd.extend(["--head", target_head])
        if draft:
            cmd.append("--draft")
        if filtered_assignees:
            cmd.extend(["--assignee", filtered_assignees])
        if labels:
            cmd.extend(["--label", labels])
        if filtered_reviewers:
            cmd.extend(["--reviewer", filtered_reviewers])
        if web:
            cmd.append("--web")

        result = run_gh_command(cmd, cwd=self.work_dir)
        if "Error" not in result:
            return f"Successfully created PR: '{title}'\n{result}"
        return result

    def gh_pr_list( state: str = "open", limit: int = 10, 
                   assignee: str = "", author: str = "", base: str = "", 
                   head: str = "", label: str = "") -> str:
        """
        List pull requests.
        
        Args:
            state (str): State of PRs to list (open, closed, merged, all).
            limit (int): Maximum number of PRs to list.
            assignee (str): Filter by assignee.
            author (str): Filter by author.
            base (str): Filter by base branch.
            head (str): Filter by head branch.
            label (str): Filter by label.
            
        Returns:
            str: List of pull requests or error message.
        """
        cmd = ["pr", "list", "--state", state, "--limit", str(limit)]
        
        if assignee:
            cmd.extend(["--assignee", assignee])
        if author:
            cmd.extend(["--author", author])
        if base:
            cmd.extend(["--base", base])
        if head:
            cmd.extend(["--head", head])
        if label:
            cmd.extend(["--label", label])
        
        result = run_gh_command(cmd, cwd=self.work_dir)
        if "Error" not in result:
            return f"Pull Requests ({state}):\n{result}"
        return result

    def gh_pr_view( pr_number: str = "", web: bool = False, 
                   comments: bool = False) -> str:
        """
        View details of a pull request.
        
        Args:
            pr_number (str): PR number to view. If empty, uses current branch's PR.
            web (bool): Open PR in web browser.
            comments (bool): Include comments in output.
            
        Returns:
            str: PR details or error message.
        """
        cmd = ["pr", "view"]
        
        if pr_number:
            cmd.append(pr_number)
        if web:
            cmd.append("--web")
        if comments:
            cmd.append("--comments")
        
        result = run_gh_command(cmd, cwd=self.work_dir)
        return result

    def gh_pr_edit( pr_number: str = "", title: str = "", body: str = "",
                    add_assignees: str = "", remove_assignees: str = "", 
                    add_labels: str = "", remove_labels: str = "",
                    add_reviewers: str = "", remove_reviewers: str = "") -> str:
        """
        Edit an existing pull request.
        
        Args:
            pr_number (str): PR number to edit. If empty, uses current branch's PR.
            title (str): New title.
            body (str): New body/description.
            add_assignees (str): Comma-separated assignees to add.
            remove_assignees (str): Comma-separated assignees to remove.
            add_labels (str): Comma-separated labels to add.
            remove_labels (str): Comma-separated labels to remove.
            add_reviewers (str): Comma-separated reviewers to add.
            remove_reviewers (str): Comma-separated reviewers to remove.
            
        Returns:
            str: Success message or error message.
        """
        cmd = ["pr", "edit"]
        
        if pr_number:
            cmd.append(pr_number)
        if title:
            cmd.extend(["--title", title])
        if body:
            cmd.extend(["--body", body])
        if add_assignees:
            filtered = _filter_valid_users(add_assignees)
            if filtered:
                cmd.extend(["--add-assignee", filtered])
        if remove_assignees:
            cmd.extend(["--remove-assignee", remove_assignees])
        if add_labels:
            cmd.extend(["--add-label", add_labels])
        if remove_labels:
            cmd.extend(["--remove-label", remove_labels])
        if add_reviewers:
            filtered = _filter_valid_users(add_reviewers)
            if filtered:
                cmd.extend(["--add-reviewer", filtered])
        if remove_reviewers:
            cmd.extend(["--remove-reviewer", remove_reviewers])
        
        result = run_gh_command(cmd, cwd=self.work_dir)
        if "Error" not in result:
            return f"Successfully edited PR{' ' + pr_number if pr_number else ''}"
        return result

    def gh_pr_merge( pr_number: str = "", merge_method: str = "merge",
                    title: str = "", body: str = "", delete_branch: bool = True) -> str:
        """
        Merge a pull request.
        
        Args:
            pr_number (str): PR number to merge. If empty, uses current branch's PR.
            merge_method (str): Merge method (merge, squash, rebase).
            title (str): Custom merge commit title.
            body (str): Custom merge commit body.
            delete_branch (bool): Delete head branch after merge.
            
        Returns:
            str: Success message or error message.
        """
        valid_methods = ["merge", "squash", "rebase"]
        if merge_method not in valid_methods:
            return f"Error: Invalid merge method '{merge_method}'. Valid methods: {valid_methods}"
        
        cmd = ["pr", "merge"]
        
        if pr_number:
            cmd.append(pr_number)
        
        if merge_method == "squash":
            cmd.append("--squash")
        elif merge_method == "rebase":
            cmd.append("--rebase")
        else:  # merge
            cmd.append("--merge")
        
        if title:
            cmd.extend(["--subject", title])
        if body:
            cmd.extend(["--body", body])
        if delete_branch:
            cmd.append("--delete-branch")
        
        result = run_gh_command(cmd, cwd=self.work_dir)
        if "Error" not in result:
            return f"Successfully merged PR{' ' + pr_number if pr_number else ''}"
        return result

    def gh_pr_close( pr_number: str = "", comment: str = "") -> str:
        """
        Close a pull request.
        
        Args:
            pr_number (str): PR number to close. If empty, uses current branch's PR.
            comment (str): Comment to add when closing.
            
        Returns:
            str: Success message or error message.
        """
        cmd = ["pr", "close"]
        
        if pr_number:
            cmd.append(pr_number)
        if comment:
            cmd.extend(["--comment", comment])
        
        result = run_gh_command(cmd, cwd=self.work_dir)
        if "Error" not in result:
            return f"Successfully closed PR{' ' + pr_number if pr_number else ''}"
        return result

    def gh_pr_reopen( pr_number: str = "") -> str:
        """
        Reopen a closed pull request.
        
        Args:
            pr_number (str): PR number to reopen. If empty, uses current branch's PR.
            
        Returns:
            str: Success message or error message.
        """
        cmd = ["pr", "reopen"]
        
        if pr_number:
            cmd.append(pr_number)
        
        result = run_gh_command(cmd, cwd=self.work_dir)
        if "Error" not in result:
            return f"Successfully reopened PR{' ' + pr_number if pr_number else ''}"
        return result

    def gh_pr_ready( pr_number: str = "") -> str:
        """
        Mark a draft pull request as ready for review.
        
        Args:
            pr_number (str): PR number to mark as ready. If empty, uses current branch's PR.
            
        Returns:
            str: Success message or error message.
        """
        cmd = ["pr", "ready"]
        
        if pr_number:
            cmd.append(pr_number)
        
        result = run_gh_command(cmd, cwd=self.work_dir)
        if "Error" not in result:
            return f"Successfully marked PR{' ' + pr_number if pr_number else ''} as ready for review"
        return result

    def gh_pr_review( pr_number: str = "", approve: bool = False,
                     request_changes: bool = False, comment: str = "", 
                     body: str = "", file_comments: str = "") -> str:
        """
        Review a pull request.
        Note that approval is not required, just merge.
        
        Args:
            pr_number (str): PR number to review. If empty, uses current branch's PR.
            approve (bool): Approve the PR (not functional, just merge).
            request_changes (bool): Request changes on the PR.
            comment (str): Add a comment without explicit approval/rejection.
            body (str): Review body comment.
            file_comments (str): File-specific comments in JSON format.
            
        Returns:
            str: Success message or error message.
        """
        cmd = ["pr", "review"]
        
        if pr_number:
            cmd.append(pr_number)
        
        if approve:
            cmd.append("--approve")
        elif request_changes:
            cmd.append("--request-changes")
        elif comment:
            cmd.append("--comment")
        
        if body:
            cmd.extend(["--body", body])
        
        result = run_gh_command(cmd, cwd=self.work_dir)
        if "Error" not in result:
            return f"Successfully reviewed PR{' ' + pr_number if pr_number else ''}"
        return result

    def gh_pr_status( pr_number: str = "") -> str:
        """
        Show status of a pull request.
        
        Args:
            pr_number (str): PR number to check status. If empty, uses current branch's PR.
            
        Returns:
            str: PR status or error message.
        """
        cmd = ["pr", "status"]
        
        if pr_number:
            cmd.append(pr_number)
        
        result = run_gh_command(cmd, cwd=self.work_dir)
        return result

    def gh_pr_checks( pr_number: str = "", watch: bool = False) -> str:
        """
        Show CI status/checks for a pull request.
        
        Args:
            pr_number (str): PR number to check. If empty, uses current branch's PR.
            watch (bool): Watch checks and live-update.
            
        Returns:
            str: Check status or error message.
        """
        cmd = ["pr", "checks"]
        
        if pr_number:
            cmd.append(pr_number)
        if watch:
            cmd.append("--watch")
        
        result = run_gh_command(cmd, cwd=self.work_dir)
        return result

    def gh_pr_comment( pr_number: str = "", body: str = "", edit_last: bool = False) -> str:
        """
        Add a comment to a pull request.
        
        Args:
            pr_number (str): PR number to comment on.
            body (str): Comment text.
            edit_last (bool): Edit the last comment instead of creating new one.
            
        Returns:
            str: Success message or error message.
        """
        if not body:
            return "Error: Comment body cannot be empty"
        if not pr_number:
            return "Error: PR number is required"
        
        cmd = ["pr", "comment", pr_number, "--body", body]
        
        if edit_last:
            cmd.append("--edit-last")
        
        result = run_gh_command(cmd, cwd=self.work_dir)
        if "Error" not in result:
            return f"Successfully {'edited last comment' if edit_last else 'added comment'} on PR {pr_number}"
        return result

    def gh_pr_diff( pr_number: str = "", name_only: bool = False) -> str:
        """
        Show diff for a pull request.
        
        Args:
            pr_number (str): PR number to show diff. If empty, uses current branch's PR.
            name_only (bool): Show only names of changed files.
            
        Returns:
            str: Diff output or error message.
        """
        cmd = ["pr", "diff"]
        
        if pr_number:
            cmd.append(pr_number)
        if name_only:
            cmd.append("--name-only")
        
        result = run_gh_command(cmd, cwd=self.work_dir)
        return result

    def gh_pr_checkout( pr_number: str, branch_name: str = "") -> str:
        """
        Checkout a pull request locally.
        
        Args:
            pr_number (str): PR number to checkout.
            branch_name (str): Local branch name. If empty, uses default.
            
        Returns:
            str: Success message or error message.
        """
        if not pr_number:
            return "Error: PR number is required"
        
        cmd = ["pr", "checkout", pr_number]
        
        if branch_name:
            cmd.extend(["--branch", branch_name])
        
        result = run_gh_command(cmd, cwd=self.work_dir)
        if "Error" not in result:
            return f"Successfully checked out PR {pr_number}"
        return result
    
    # Return list of tools
    return [
        gh_pr_create,
        gh_pr_list,
        gh_pr_view,
        gh_pr_edit,
        gh_pr_merge,
        gh_pr_close,
        gh_pr_reopen,
        gh_pr_ready,
        # gh_pr_review,
        gh_pr_status,
        gh_pr_checks,
        gh_pr_comment,
        gh_pr_diff,
        gh_pr_checkout,
    ] 