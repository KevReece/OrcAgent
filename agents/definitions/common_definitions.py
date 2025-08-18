#!/usr/bin/env python3
"""
Common Definitions Module

This module contains shared technical notes and definitions used across all agent types.
"""

from typing import List, Dict
from agents.entities import Associate

def get_universal_instructions() -> str:
    """
    Get universal instructions for all agents.
    """
    return """\n
Important general instructions:
- All delivery expectations are synchronous, so always complete delivery, or delegate, immediately and verify completion immediately. 
- Implementation is critical and everyone is responsible to ensure that real results are delivered with high velocity. 
- If your prompt implies a need for delivery, you must deliver and give rock solid evidence of delivery, such as a test completion report, either by yourself or by delegating to the appropriate worker, a plan to deliver or a unsupported claim of delivery is not sufficient.
- For those with engineering tools, a basic dev/test/prod web environment is available, with a source github repo, and a both a direct deploy mechanism and an skeleton github actions pipeline.
- You will need to manage your time effectively, and give time constraints in your delegations.
- The evaluation of success will primarily be based on the production website's match to requirements. So ensure that at a minimum something is deployed to production in the alloted time. Using the existing working deploy from local and deploy from CI/CD mechanisms as a base is therefore important for success.
    """

def get_tool_notes(tool_group_names: List[str]) -> str:
    """
    Get tool-specific technical notes based on the available tool groups.
    
    Args:
        tool_group_names: List of tool group names available to the agent
        
    Returns:
        Formatted technical notes relevant to the available tools
    """
    if not tool_group_names:
        return ""
    
    notes = ["Tool notes:"]
    notes.append("- Use the tools to carry out all of your actions as you have restricted command line access.")
    notes.append("- Production applications must be hosted on the production aws fargate instance.")
    notes.append("- You don't have a calendar tool, so don't attempt to arrange meetings, instead use delegation.")
    notes.append("- Verification is required (e.g. filesystem, branch, PR existence) before success can be claimed.")
    
    # Local GitHub repo note for file or git tools
    if any(tool in tool_group_names for tool in ["file_tools", "git_tools"]):
        notes.append("- The project Github repo is cloned ready for use in the working directory root.")
    
    # AWS Fargate and Docker notes for infrastructure-related tools
    if any(tool in tool_group_names for tool in ["aws_cli_tools", "docker_tools", "github_pr_tools", "github_actions_tools"]):
        notes.extend([
            "- The AWS Fargate infrastructure expects web services on port 8080.",
            "- The docker container must therefore expose and listen on port 8080.",
            "- The Dockerfile must be compatible with the target platform of AWS Fargate.",
            "- The docker build will be for linux/amd64 for Fargate compatibility.",
            "- The dev AWS Fargate instance is available for you to iterate on.",
            "- Deployments must use unique, immutable image tags to avoid stale tasks.",
            "- ECS expects containers to respond to /health checks for service stability monitoring. "
            "- CloudWatch integration requires output to stdout/stderr."
            "- Must listen on port 8080 to match infrastructure load balancer configuration. "
            "- The test/prod AWS Fargate instances are available for your Github Actions pipeline to deploy to."
            "- Deployments to production can use gh actions tools via the test environment."
            "- Only the production environment is usable for live and publicly accessible services."
            "- The dev, test, and prod AWS Fargate instances are available for deployment via docker tools.",
            "- All app environments (dev, test, prod) can be deployed to using the docker tools.",
            "- Only the production environment is usable for live and publicly accessible services.",
            "- ECR repo names are in the format of 'sandbox-ecr'.",
            "- Cluster names are in the format of 'sandbox-<dev|test|prod>'.",
            "- Service names are in the format of 'sandbox-<dev|test|prod>-service'.",
            "- Container names are 'sandbox-app'.",
            "- Github actions are already configured with the secrets: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, AWS_ACCOUNT_ID.",
            "- ECS services require task definition updates, not just service force-deployment.",
            "- ECS services will be scaled to 0 tasks initially, requiring explicit scaling steps in deployment.",
            "- The state of the AWS Fargate instances can be checked using the aws cli tools.",
            "- Ensure that the /health endpoint is responding after all deployments.",
            "- The repo is seeded with a dockerfile, nginx.conf, and a github deploy.yaml workflow.",
            "- Whenever you create a PR, you must delegate to an engineer to review your PR, and then merge it. Never leave the PR unmerged.",
            "- Don't try to approve PRs, just merge them once reviewed (approval won't work, and isn't required).",
            "- Before delegating or completing a response, all changes must be committed to main branch or a PR that is being reviewed."
        ])
    
    # Notion-specific notes
    if "notion_tools" in tool_group_names:
        notes.append("- You have a notion root page ready for all notes, planning, documentation, and delivery artifacts.")
    
    # AWS-specific notes
    if "aws_cli_tools" in tool_group_names:
        notes.append("- You have access to AWS CLI tools for infrastructure management.")
    
    # Docker-specific notes
    if "docker_tools" in tool_group_names:
        notes.append("- You have access to Docker tools for containerization.")
    
    # GitHub-specific notes
    if any(tool in tool_group_names for tool in ["git_tools", "github_pr_tools", "github_actions_tools"]):
        notes.append("- You have access to Git and GitHub tools for version control and CI/CD.")
    
    # Playwright-specific notes
    if "playwright_tools" in tool_group_names:
        notes.append("- You have access to Playwright tools for web automation and testing.")
    
    # Web-specific notes
    if "web_tools" in tool_group_names:
        notes.append("- Web tools include a web request for validation and testing.")
    
    # Delegation-specific notes
    if "delegation_tools" in tool_group_names:
        notes.append("- You can delegate tasks to other agents using delegation tools.")
        notes.append("- Ensure delegation description is extremely comprehensive in both the task and the gravity of the responsibility to complete the task.")
        notes.append("- All task delegation prompts must have an explicit expectation of high velocity synchronous completion, including comprehensive evidence of completion. ")
        notes.append("- When receiving a response, if any aspect of the task is not supported by iron clad evidence of comprehensive completion validation, you must re-delegate to the worker to rectify the task, again with all the sufficient context to fully complete the task.")
        notes.append("- In general, trust the implementation details to those with the tools as they have the context.")
    
    # Agent orchestration-specific notes
    if "agents_orchestration_tools" in tool_group_names:
        notes.append("- You have access to agent orchestration tools for team management.")
    
    # Memory-specific notes
    if "memory_tools" in tool_group_names:
        notes.append("- You have access to memory tools for maintaining context across conversations.")
        notes.append("- Before completing any response or delegating, you must store all valuable context in memory for future reference.")
    
    # File-specific notes
    if "file_tools" in tool_group_names:
        notes.append("- You have access to file manipulation tools.")
    
    return "\n".join(notes)


def assign_team_associates(worker_name: str, teams: Dict[str, List[str]], relationship_descriptions: Dict[str, str] | None = None) -> List[Associate]:
    """
    Assign associates for a worker based on team membership.
    
    Args:
        worker_name: Name of the worker to assign associates for
        teams: Dictionary mapping team names to lists of worker names in that team
        relationship_descriptions: Optional dictionary mapping team names to relationship descriptions
        
    Returns:
        List of Associate objects for the worker
    """
    associates: List[Associate] = []
    
    # Find which team this worker belongs to
    worker_team = None
    for team_name, team_members in teams.items():
        if worker_name in team_members:
            worker_team = team_name
            break
    
    if worker_team is None:
        return associates
    
    # Add all other team members as associates
    team_members = teams[worker_team]
    for member_name in team_members:
        if member_name != worker_name:  # Don't associate with self
            relationship = relationship_descriptions.get(worker_team, f"Team member in {worker_team}") if relationship_descriptions else f"Team member in {worker_team}"
            associates.append(Associate(name=member_name, relationship=relationship))
    
    return associates 