import time
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict
from tools.gh_helper import run_gh_command
from logger.log_wrapper import get_logger
from tools.context import ToolsContext


def get_tools(tools_context: ToolsContext):
    """GitHub Actions Tools"""
    
    def init(self, work_dir: str, is_integration_test: bool = False):
        """
        Initialize GitHub Actions Tools.
        
        Args:
            work_dir: Working directory for git operations
            is_integration_test: Whether this is running in integration test mode
        """
        self.work_dir = work_dir
        self.logger = get_logger("tool:github_actions", __name__)
    
    self = type("Self", (), {})()
    init(self, tools_context.agent_work_dir, tools_context.is_integration_test)

    def gh_actions_list() -> str:
        """
        List all GitHub Actions workflows in the repository.
        
        Returns:
            str: The list of workflows or error message.
        """
        result = run_gh_command(["workflow", "list"], cwd=self.work_dir)
        if "Error" in result:
            return result
        return f"GitHub Actions workflows:\n{result}"

    def gh_actions_status( workflow_name: Optional[str] = None) -> str:
        """
        Get the status of GitHub Actions workflow runs limited to the last 15 minutes.
        
        Args:
            workflow_name (Optional[str]): The name of the workflow to check. If None, shows all workflows.
            
        Returns:
            str: The status of workflow runs or error message.
        """
        # Request JSON so we can filter by time window
        fields = [
            "databaseId",
            "workflowName",
            "displayTitle",
            "status",
            "conclusion",
            "createdAt",
            "updatedAt",
            "headBranch",
            "event",
        ]

        cmd = ["run", "list", "--limit", "50", "--json", ",".join(fields)]
        if workflow_name:
            cmd.extend(["--workflow", workflow_name])

        result = run_gh_command(cmd, cwd=self.work_dir)
        if "Error" in result:
            return result

        # Parse JSON and filter to last 15 minutes
        try:
            runs = json.loads(result)
        except Exception as e:
            return f"Error parsing GitHub Actions runs JSON: {e}"

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)

        def parse_iso8601(s: Optional[str]) -> Optional[datetime]:
            if not s:
                return None
            try:
                # gh returns Zulu time; ensure timezone-aware
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            except Exception:
                return None

        filtered = []
        for run in runs if isinstance(runs, list) else []:
            created_at = parse_iso8601(run.get("createdAt"))
            if created_at and created_at >= cutoff:
                filtered.append(run)

        if not filtered:
            return "GitHub Actions workflow run status:\nNo runs in the last 15 minutes"

        # Build a concise, readable summary similar to gh default list
        lines = []
        for run in filtered:
            status = run.get("status") or ""
            conclusion = run.get("conclusion") or ""
            workflow_name_val = run.get("workflowName") or ""
            title = run.get("displayTitle") or ""
            branch = run.get("headBranch") or ""
            created = run.get("createdAt") or ""
            run_id = str(run.get("databaseId") or "")
            summary = f"{status}/{conclusion} | {workflow_name_val} | {branch} | {created} | {title} | id:{run_id}"
            lines.append(summary)

        return "GitHub Actions workflow run status:\n" + "\n".join(lines)

    def gh_actions_view( run_id: str) -> str:
        """
        View details of a specific GitHub Actions workflow run.
        
        Args:
            run_id (str): The ID of the workflow run to view.
            
        Returns:
            str: The details of the workflow run or error message.
        """
        if not run_id:
            return "Error: run_id is required"
        
        result = run_gh_command(["run", "view", run_id], cwd=self.work_dir)
        if "Error" in result:
            return result
        return f"GitHub Actions workflow run details:\n{result}"

    def gh_actions_logs( run_id: str) -> str:
        """
        Get logs for a specific GitHub Actions workflow run.
        
        Args:
            run_id (str): The ID of the workflow run to get logs for.
            
        Returns:
            str: The logs of the workflow run or error message.
        """
        if not run_id:
            return "Error: run_id is required"
        
        result = run_gh_command(["run", "view", run_id, "--log"], cwd=self.work_dir)
        if "Error" in result:
            return result
        return f"GitHub Actions workflow run logs:\n{result}"

    def gh_actions_rerun( run_id: str) -> str:
        """
        Re-run a GitHub Actions workflow run.
        
        Args:
            run_id (str): The ID of the workflow run to re-run.
            
        Returns:
            str: Success message or error message.
        """
        if not run_id:
            return "Error: run_id is required"
        
        result = run_gh_command(["run", "rerun", run_id], cwd=self.work_dir)
        if "Error" in result:
            return result
        return f"Successfully re-ran GitHub Actions workflow run {run_id}"

    def gh_actions_cancel( run_id: str) -> str:
        """
        Cancel a GitHub Actions workflow run.
        
        Args:
            run_id (str): The ID of the workflow run to cancel.
            
        Returns:
            str: Success message or error message.
        """
        if not run_id:
            return "Error: run_id is required"
        
        result = run_gh_command(["run", "cancel", run_id], cwd=self.work_dir)
        if "Error" in result:
            return result
        return f"Successfully cancelled GitHub Actions workflow run {run_id}"

    def gh_actions_dispatch( workflow_name: str, ref: str = "main", inputs: Optional[Dict[str, str]] = None) -> str:
        """
        Trigger a GitHub Actions workflow dispatch event.
        
        Args:
            workflow_name (str): The name of the workflow to trigger.
            ref (str): The git reference to trigger the workflow on. Defaults to "main".
            inputs (Optional[Dict[str, str]]): Input parameters for the workflow.
            
        Returns:
            str: Success message or error message.
        """
        if not workflow_name:
            return "Error: workflow_name is required"
        
        cmd = ["workflow", "run", workflow_name, "--ref", ref]
        
        if inputs:
            for key, value in inputs.items():
                cmd.extend(["-f", f"{key}={value}"])
        
        result = run_gh_command(cmd, cwd=self.work_dir)
        if "Error" in result:
            return result
        return f"Successfully triggered workflow '{workflow_name}' on ref '{ref}'"

    def gh_actions_download_artifact( run_id: str, artifact_name: Optional[str] = None, destination: str = ".") -> str:
        """
        Download artifacts from a GitHub Actions workflow run.
        
        Args:
            run_id (str): The ID of the workflow run to download artifacts from.
            artifact_name (Optional[str]): The name of the specific artifact to download. If None, downloads all artifacts.
            destination (str): The destination directory to download to. Defaults to current directory.
            
        Returns:
            str: Success message or error message.
        """
        if not run_id:
            return "Error: run_id is required"
        
        cmd = ["run", "download", run_id, "--dir", destination]
        if artifact_name:
            cmd.extend(["--name", artifact_name])
        
        result = run_gh_command(cmd, cwd=self.work_dir)
        if "Error" in result:
            return result
        
        if artifact_name:
            return f"Successfully downloaded artifact '{artifact_name}' from run {run_id} to {destination}"
        else:
            return f"Successfully downloaded all artifacts from run {run_id} to {destination}"

    def gh_actions_enable_workflow( workflow_name: str) -> str:
        """
        Enable a GitHub Actions workflow.
        
        Args:
            workflow_name (str): The name of the workflow to enable.
            
        Returns:
            str: Success message or error message.
        """
        if not workflow_name:
            return "Error: workflow_name is required"
        
        result = run_gh_command(["workflow", "enable", workflow_name], cwd=self.work_dir)
        if "Error" in result:
            return result
        return f"Successfully enabled workflow '{workflow_name}'"

    def gh_actions_disable_workflow( workflow_name: str) -> str:
        """
        Disable a GitHub Actions workflow.
        
        Args:
            workflow_name (str): The name of the workflow to disable.
            
        Returns:
            str: Success message or error message.
        """
        if not workflow_name:
            return "Error: workflow_name is required"
        
        result = run_gh_command(["workflow", "disable", workflow_name], cwd=self.work_dir)
        if "Error" in result:
            return result
        return f"Successfully disabled workflow '{workflow_name}'"

    def gh_actions_wait_for_workflows(timeout_seconds: int = 900, poll_interval_seconds: int = 10) -> str:
        """
        Wait for all active GitHub Actions workflow runs in the current repository to complete.

        Polls for in-progress or queued runs and blocks until there are none or the timeout is reached.

        Args:
            timeout_seconds: Maximum time to wait before giving up.
            poll_interval_seconds: Delay between checks.

        Returns:
            str: Summary message indicating completion, timeout, or error details.
        """
        if timeout_seconds <= 0:
            return "Error: timeout_seconds must be positive"
        if poll_interval_seconds <= 0:
            return "Error: poll_interval_seconds must be positive"

        deadline = time.time() + timeout_seconds
        # Quick detection of repository context errors up front
        list_result = run_gh_command(["run", "list", "--limit", "50"], cwd=self.work_dir)
        if "Error" in list_result:
            return list_result

        def has_active_runs(output: str) -> bool:
            lower = output.lower()
            # Consider typical active indicators; keep text parsing robust
            indicators = ["in_progress", "in progress", "queued", "waiting"]
            return any(ind in lower for ind in indicators)

        # If none active, return immediately
        if not has_active_runs(list_result):
            return "No active GitHub Actions workflow runs found"

        # Poll until none active or timeout
        while time.time() < deadline:
            time.sleep(poll_interval_seconds)
            result = run_gh_command(["run", "list", "--limit", "50"], cwd=self.work_dir)
            if "Error" in result:
                return result
            if not has_active_runs(result):
                return "All GitHub Actions workflow runs have completed"
            self.logger.info(f"GitHub Actions workflow runs in progress: {result}")

        return "Timeout waiting for GitHub Actions workflows to complete"

    def gh_actions_list_jobs( run_id: str) -> str:
        """
        List jobs for a GitHub Actions workflow run.
        
        Args:
            run_id (str): The ID of the workflow run to list jobs for.
            
        Returns:
            str: The list of jobs or error message.
        """
        if not run_id:
            return "Error: run_id is required"
        # Use JSON output to reliably list jobs without requiring a specific --job argument
        result = run_gh_command(["run", "view", run_id, "--json", "jobs"], cwd=self.work_dir)
        if "Error" in result:
            return result
        try:
            data = json.loads(result)
            jobs = data.get("jobs", []) if isinstance(data, dict) else []
            if not jobs:
                return "GitHub Actions workflow run jobs:\n(no jobs found)"
            lines = []
            for job in jobs:
                job_id = str(job.get("id", ""))
                name = job.get("name", "")
                status = job.get("status", "")
                conclusion = job.get("conclusion", "")
                lines.append(f"{job_id} | {name} | {status}/{conclusion}")
            return "GitHub Actions workflow run jobs:\n" + "\n".join(lines)
        except Exception as e:
            # Fallback to raw output if parsing fails
            return f"GitHub Actions workflow run jobs (raw):\n{result}\n(Note: failed to parse jobs JSON: {e})"

    def gh_actions_job_logs( run_id: str, job_id: str) -> str:
        """
        Get logs for a specific job in a GitHub Actions workflow run.
        
        Args:
            run_id (str): The ID of the workflow run.
            job_id (str): The ID of the job to get logs for.
            
        Returns:
            str: The logs of the job or error message.
        """
        if not run_id:
            return "Error: run_id is required"
        if not job_id:
            return "Error: job_id is required"
        
        result = run_gh_command(["run", "view", run_id, "--job", job_id, "--log"], cwd=self.work_dir)
        if "Error" in result:
            return result
        return f"GitHub Actions job logs:\n{result}"
    
    # Return list of tools
    return [
        gh_actions_list,
        gh_actions_status,
        gh_actions_view,
        gh_actions_logs,
        gh_actions_rerun,
        gh_actions_cancel,
        gh_actions_dispatch,
        gh_actions_download_artifact,
        gh_actions_enable_workflow,
        gh_actions_disable_workflow,
        gh_actions_wait_for_workflows,
        gh_actions_list_jobs,
        gh_actions_job_logs,
    ] 