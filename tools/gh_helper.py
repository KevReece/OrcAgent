import subprocess
import os
from typing import List, Optional


def run_gh_command(command: List[str], cwd: Optional[str] = None) -> str:
    """
    Helper function to run a GitHub CLI command and return the output.
    
    Args:
        command (List[str]): The gh command and arguments to run.
        cwd (Optional[str]): The working directory to run the command in.
        
    Returns:
        str: The command output or error message.
    """
    try:
        # Pass the GITHUB_TOKEN to the environment of the subprocess
        env = os.environ.copy()
        env["GITHUB_TOKEN"] = os.getenv("GITHUB_TOKEN", "")
        
        process = subprocess.run(
            ["gh"] + command,
            capture_output=True,
            text=True,
            check=True,
            env=env,
            cwd=cwd,
        )
        return process.stdout.strip()
    except FileNotFoundError:
        return "Error: 'gh' command not found. Please ensure the GitHub CLI is installed and in your PATH."
    except subprocess.CalledProcessError as e:
        return f"Error executing gh command: {e}\nStderr: {e.stderr.strip()}"
    except Exception as e:
        return f"An unexpected error occurred: {e}" 