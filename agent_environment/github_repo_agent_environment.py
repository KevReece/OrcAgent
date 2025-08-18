"""
GitHub Repository Management Module

This module provides functionality to clean and reset a GitHub repository
by removing files, clearing action run history, and deleting pull requests.
"""

import os
import base64
import subprocess
from typing import Tuple
import json
from logger.log_wrapper import get_logger


class GitHubRepoAgentEnvironment:
    """GitHub repository management class with cleaning capabilities."""
    
    def __init__(self, is_integration_test: bool = False):
        """
        Initialize GitHub repository manager.
        
        Args:
            is_integration_test: Whether to use test repository configuration
        """
        repo_owner, repo_name, token = self._get_repo_config(is_integration_test)
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.token = token
        self.repo_full_name = f"{repo_owner}/{repo_name}"
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.logger = get_logger("env:github", __name__)
    
    def reset(self) -> None:
        """
        Clean the repository. Actions include:
          - Remove all files on the default branch by creating an orphan commit to the empty tree
          - Close all open pull requests (cannot be permanently deleted on GitHub)
          - Delete all remote branches except the default branch
          - Attempt to reset action runs (limited by GitHub API; only cancellation of in-progress runs)

        Raises:
            Exception: If any cleaning operation fails
        """
        self.logger.info(f"Starting cleanup of repository: {self.repo_full_name}")
        
        # Clean files using GitHub API
        if not self._remove_all_files():
            raise Exception("Failed to remove all files")
        
        # Close all open PRs
        if not self._close_all_open_prs():
            raise Exception("Failed to close all open pull requests")

        # Delete all non-default remote branches
        if not self._delete_non_default_branches():
            raise Exception("Failed to delete non-default branches")
        
        # Reset action runs (note: GitHub doesn't allow deleting run history directly)
        if not self._reset_action_runs():
            self.logger.warning("Cannot reset action run history (GitHub API limitation)")
        
        self.logger.info(f"Repository {self.repo_full_name} cleaned successfully!")

        # Seed repository with Docker, Nginx, index.html and CI workflow
        if not self._seed_repo_files():
            raise Exception("Failed to seed repository files")
        self.logger.info(
            f"Repository {self.repo_full_name} seeded with Dockerfile, nginx.conf, index.html, and deploy workflow"
        )
    
    def _remove_all_files(self) -> bool:
        """
        Remove all files from the repository using GitHub API.
        Creates an empty Git tree and orphan commit, then points the default branch to it.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get default branch
            result = subprocess.run([
                "gh", "repo", "view", self.repo_full_name, "--json", "defaultBranchRef"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                branch_info = json.loads(result.stdout)
                default_branch = branch_info.get("defaultBranchRef", {}).get("name", "main")
            else:
                default_branch = "main"
            
            self.logger.info(f"Creating empty tree for branch: {default_branch}")
            
            # Step 1: Use the known SHA for an empty Git tree
            # In Git, the SHA for an empty tree is always the same
            tree_sha = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
            
            # Step 2: Create an orphan commit pointing to the empty tree
            commit_data = {
                "tree": tree_sha,
                "message": "Clean repository: Remove all files",
                "parents": []
            }
            commit_result = subprocess.run([
                "gh", "api", f"repos/{self.repo_full_name}/git/commits",
                "--method", "POST",
                "--input", "-"
            ], input=json.dumps(commit_data), capture_output=True, text=True)
            
            if commit_result.returncode != 0:
                self.logger.error(f"Failed to create orphan commit: {commit_result.stderr}")
                return False
            
            commit_info = json.loads(commit_result.stdout)
            commit_sha = commit_info["sha"]
            
            # Step 3: Point the default branch to the orphan commit
            update_ref_result = subprocess.run([
                "gh", "api", f"repos/{self.repo_full_name}/git/refs/heads/{default_branch}",
                "--method", "PATCH",
                "--field", f"sha={commit_sha}",
                "--field", "force=true"
            ], capture_output=True, text=True)
            
            if update_ref_result.returncode != 0:
                self.logger.error(f"Failed to update branch reference: {update_ref_result.stderr}")
                return False
            
            self.logger.info(f"Successfully updated {default_branch} branch to point to empty commit")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error removing files: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error removing files: {str(e)}")
            return False
    
    def _close_all_open_prs(self) -> bool:
        """
        Close all open pull requests in the repository.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get all open pull requests using gh CLI
            result = subprocess.run([
                "gh", "pr", "list", "--repo", self.repo_full_name, 
                "--state", "open", "--json", "number,title"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Failed to get open pull requests: {result.stderr}")
                return False
            
            open_prs = json.loads(result.stdout) if result.stdout else []
            
            # Close all open PRs (GitHub doesn't allow deleting PRs, only closing them)
            closed_count = 0
            for pr in open_prs:
                pr_number = pr["number"]
                close_result = subprocess.run([
                    "gh", "pr", "close", str(pr_number), "--repo", self.repo_full_name
                ], capture_output=True, text=True)
                
                if close_result.returncode == 0:
                    closed_count += 1
                    self.logger.info(f"Closed PR #{pr_number}: {pr['title']}")
                else:
                    self.logger.error(f"Failed to close PR #{pr_number}: {close_result.stderr}")
            
            if not open_prs:
                self.logger.info("No open pull requests found")
            else:
                self.logger.info(f"Closed {closed_count} open pull requests - Note: Closed PRs remain in history (GitHub doesn't allow deletion)")
                
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error managing pull requests: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error managing pull requests: {str(e)}")
            return False

    def _delete_non_default_branches(self) -> bool:
        """
        Delete all remote branches except the repository's default branch.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Determine default branch
            result = subprocess.run([
                "gh", "repo", "view", self.repo_full_name, "--json", "defaultBranchRef"
            ], capture_output=True, text=True)

            if result.returncode != 0:
                self.logger.error(f"Failed to get default branch: {result.stderr}")
                return False

            branch_info = json.loads(result.stdout) if result.stdout else {}
            default_branch = branch_info.get("defaultBranchRef", {}).get("name", "main")

            # List all branches via git refs API (more reliable across repo states)
            list_result = subprocess.run([
                "gh", "api", f"repos/{self.repo_full_name}/git/refs/heads"
            ], capture_output=True, text=True)
            if list_result.returncode != 0:
                self.logger.error(f"Failed to list branches: {list_result.stderr}")
                return False
            data = json.loads(list_result.stdout) if list_result.stdout else []
            # When only one ref exists, GitHub may return an object instead of a list
            if isinstance(data, dict) and data.get("ref"):
                data = [data]
            branches = []
            for ref in data:
                ref_name = ref.get("ref", "")
                if ref_name.startswith("refs/heads/"):
                    branches.append(ref_name.split("refs/heads/", 1)[1])

            if not branches:
                self.logger.info("No branches found to delete")
                return True

            # Delete each non-default branch via Git refs API
            deleted_count = 0
            skipped: list[str] = []
            for branch in branches:
                if branch == default_branch:
                    skipped.append(branch)
                    continue
                delete_result = subprocess.run([
                    "gh", "api", f"repos/{self.repo_full_name}/git/refs/heads/{branch}",
                    "--method", "DELETE"
                ], capture_output=True, text=True)
                if delete_result.returncode == 0:
                    deleted_count += 1
                    self.logger.info(f"Deleted remote branch: {branch}")
                else:
                    # Likely protected branch or insufficient permissions
                    self.logger.warning(f"Failed to delete branch '{branch}': {delete_result.stderr}")

            self.logger.info(
                f"Deleted {deleted_count} non-default branches; skipped default branch '{default_branch}'"
            )
            return True
        
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error deleting branches: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error deleting branches: {str(e)}")
            return False
    
    def _reset_action_runs(self) -> bool:
        """
        Reset GitHub Actions runs (limited by GitHub API).
        
        Note: GitHub API doesn't allow deleting workflow run history directly.
        This function will cancel any running workflows and provide information.
        
        Returns:
            bool: True if operations completed, False if errors occurred
        """
        try:
            # Get workflow runs using gh CLI
            result = subprocess.run([
                "gh", "run", "list", "--repo", self.repo_full_name,
                "--json", "databaseId,status,conclusion"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Failed to get workflow runs: {result.stderr}")
                return False
            
            runs = json.loads(result.stdout) if result.stdout else []
            
            if not runs:
                self.logger.info("No workflow runs found")
                return True
            
            # Cancel any in-progress runs
            cancelled_count = 0
            for run in runs:
                if run["status"] in ["in_progress", "queued"]:
                    run_id = run["databaseId"]
                    cancel_result = subprocess.run([
                        "gh", "run", "cancel", str(run_id), "--repo", self.repo_full_name
                    ], capture_output=True, text=True)
                    
                    if cancel_result.returncode == 0:
                        cancelled_count += 1
                        self.logger.info(f"Cancelled workflow run #{run_id}")
            
            self.logger.info(f"Found {len(runs)} total workflow runs - Cancelled {cancelled_count} in-progress runs - Note: GitHub doesn't allow deleting completed workflow run history")
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error managing workflow runs: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error managing workflow runs: {str(e)}")
            return False

    def _seed_repo_files(self) -> bool:
        """
        Seed the repository with Dockerfile, nginx.conf, index.html and a CI/CD workflow
        that builds, pushes to ECR, deploys to test, then to prod.

        Returns:
            bool: True when all files created/updated successfully
        """
        try:
            # Dockerfile
            self._put_file(
                "Dockerfile",
                """# Base image for the Nginx server
FROM nginx:alpine

# Set the working directory
WORKDIR /usr/share/nginx/html

# Copy static HTML files to the Nginx root directory
COPY index.html /usr/share/nginx/html/

# Copy custom nginx configuration file to the correct location
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port 8080 for the application
EXPOSE 8080

# HEALTHCHECK to ensure application is healthy
HEALTHCHECK CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

# Start Nginx server
CMD ["nginx", "-g", "daemon off;"]
""",
                "Seed Dockerfile",
            )

            # nginx.conf
            self._put_file(
                "nginx.conf",
                """events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    access_log /dev/stdout;
    error_log /dev/stderr warn;
    
    server {
        listen 8080;
        root /usr/share/nginx/html;
        index index.html;
        
        location / {
            try_files $uri $uri/ /index.html;
        }
        
        location /health {
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}
""",
                "Seed nginx.conf",
            )

            # Minimal index.html so the container serves something
            self._put_file(
                "index.html",
                """<!doctype html>
<html>
<head><meta charset=\"utf-8\"><title>Seeded App</title></head>
<body><h1>Seeded App</h1><p>Deployed via GitHub Actions to AWS Fargate.</p></body>
</html>
""",
                "Add minimal index.html",
            )

            # CI/CD workflow
            self._put_file(
                ".github/workflows/deploy.yml",
                self._render_deploy_workflow(),
                "Add deploy workflow",
            )

            return True
        except Exception as e:
            self.logger.error(f"Seeding files failed: {e}")
            return False

    def _render_deploy_workflow(self) -> str:
        """
        Render a GitHub Actions workflow that:
          - builds and pushes Docker image to ECR in the sandbox account
          - deploys to ECS service for app environment 'test'
          - upon success, deploys to 'prod'
        Secrets required on the repo: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
        """
        return """name: deploy

on:
  push:
    branches: [ "main" ]

env:
  AWS_REGION: ${{ secrets.AWS_DEFAULT_REGION }}
  ACCOUNT_ENV: sandbox
  ECR_REPO_NAME: sandbox-ecr

jobs:
  build_and_push:
    runs-on: ubuntu-latest
    outputs:
      image_uri: ${{ steps.meta.outputs.image_uri }}
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Resolve ECR repository URI (fail if missing)
        id: ecr
        shell: bash
        run: |
          set -euo pipefail
          URI=$(aws ecr describe-repositories \
            --repository-names "$ECR_REPO_NAME" \
            --query 'repositories[0].repositoryUri' --output text 2>/dev/null || true)
          if [[ -z "$URI" || "$URI" == "None" || "$URI" == "null" ]]; then
            echo "ECR repository '$ECR_REPO_NAME' not found. Run terraform apply for the sandbox workspace."
            exit 1
          fi
          echo "uri=$URI" >> "$GITHUB_OUTPUT"

      - name: Login to ECR
        shell: bash
        run: |
          set -euo pipefail
          aws ecr get-login-password --region "$AWS_REGION" \
            | docker login --username AWS --password-stdin "$(echo "${{ steps.ecr.outputs.uri }}" | cut -d/ -f1)"

      - name: Build Docker image
        shell: bash
        run: |
          set -euo pipefail
          IMAGE_URI="${{ steps.ecr.outputs.uri }}"
          TAG="${GITHUB_SHA::7}"
          docker build --platform linux/amd64 -t "$IMAGE_URI:$TAG" .

      - name: Push Docker image
        shell: bash
        run: |
          set -euo pipefail
          IMAGE_URI="${{ steps.ecr.outputs.uri }}"
          TAG="${GITHUB_SHA::7}"
          docker push "$IMAGE_URI:$TAG"

      - name: Set image URI output
        id: meta
        shell: bash
        run: |
          set -euo pipefail
          echo "image_uri=${{ steps.ecr.outputs.uri }}:${GITHUB_SHA::7}" >> "$GITHUB_OUTPUT"

  deploy_test:
    runs-on: ubuntu-latest
    needs: build_and_push
    env:
      CLUSTER: sandbox-test
      SERVICE: sandbox-test-service
      IMAGE_URI: ${{ needs.build_and_push.outputs.image_uri }}
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Ensure jq
        shell: bash
        run: |
          set -euo pipefail
          if ! command -v jq >/dev/null 2>&1; then
            sudo apt-get update -y
            sudo apt-get install -y jq
          fi

      - name: Resolve IMAGE_URI if missing
        shell: bash
        run: |
          set -euo pipefail
          if [[ -z "${IMAGE_URI:-}" ]]; then
            URI=$(aws ecr describe-repositories --repository-names "$ECR_REPO_NAME" --query 'repositories[0].repositoryUri' --output text)
            TAG="${GITHUB_SHA::7}"
            IMAGE_URI="$URI:$TAG"
            echo "IMAGE_URI=$IMAGE_URI" >> "$GITHUB_ENV"
          fi

      - name: Update ECS service to new image (test)
        shell: bash
        run: |
          set -euo pipefail
          if [[ -z "${IMAGE_URI:-}" ]]; then
            echo "IMAGE_URI is empty. Check the build_and_push job outputs."
            exit 1
          fi
          TD_ARN=$(aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" --query 'services[0].taskDefinition' --output text)
          if [[ -z "$TD_ARN" || "$TD_ARN" == "None" ]]; then
            echo "Unable to resolve current task definition ARN for $SERVICE in $CLUSTER"
            exit 1
          fi
          CURRENT=$(aws ecs describe-task-definition --task-definition "$TD_ARN" --query 'taskDefinition' --output json)
          NEW_DEF=$(echo "$CURRENT" | jq --arg IMG "$IMAGE_URI" '
            .containerDefinitions[0].image = $IMG
            | {family, taskRoleArn, executionRoleArn, networkMode, containerDefinitions, volumes, placementConstraints, requiresCompatibilities, cpu, memory, tags, pidMode, ipcMode, proxyConfiguration, inferenceAccelerators, ephemeralStorage, runtimePlatform}
            | with_entries(select(.value != null))
          ')
          ARN=$(aws ecs register-task-definition --cli-input-json "$NEW_DEF" --query 'taskDefinition.taskDefinitionArn' --output text)
          aws ecs update-service --cluster "$CLUSTER" --service "$SERVICE" --task-definition "$ARN" --desired-count 1
          aws ecs wait services-stable --cluster "$CLUSTER" --services "$SERVICE"

  deploy_prod:
    runs-on: ubuntu-latest
    needs: deploy_test
    env:
      CLUSTER: sandbox-prod
      SERVICE: sandbox-prod-service
      IMAGE_URI: ${{ needs.build_and_push.outputs.image_uri }}
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Ensure jq
        shell: bash
        run: |
          set -euo pipefail
          if ! command -v jq >/dev/null 2>&1; then
            sudo apt-get update -y
            sudo apt-get install -y jq
          fi

      - name: Resolve IMAGE_URI if missing
        shell: bash
        run: |
          set -euo pipefail
          if [[ -z "${IMAGE_URI:-}" ]]; then
            URI=$(aws ecr describe-repositories --repository-names "$ECR_REPO_NAME" --query 'repositories[0].repositoryUri' --output text)
            TAG="${GITHUB_SHA::7}"
            IMAGE_URI="$URI:$TAG"
            echo "IMAGE_URI=$IMAGE_URI" >> "$GITHUB_ENV"
          fi

      - name: Update ECS service to new image (prod)
        shell: bash
        run: |
          set -euo pipefail
          if [[ -z "${IMAGE_URI:-}" ]]; then
            echo "IMAGE_URI is empty. Check the build_and_push job outputs."
            exit 1
          fi
          TD_ARN=$(aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" --query 'services[0].taskDefinition' --output text)
          if [[ -z "$TD_ARN" || "$TD_ARN" == "None" ]]; then
            echo "Unable to resolve current task definition ARN for $SERVICE in $CLUSTER"
            exit 1
          fi
          CURRENT=$(aws ecs describe-task-definition --task-definition "$TD_ARN" --query 'taskDefinition' --output json)
          NEW_DEF=$(echo "$CURRENT" | jq --arg IMG "$IMAGE_URI" '
            .containerDefinitions[0].image = $IMG
            | {family, taskRoleArn, executionRoleArn, networkMode, containerDefinitions, volumes, placementConstraints, requiresCompatibilities, cpu, memory, tags, pidMode, ipcMode, proxyConfiguration, inferenceAccelerators, ephemeralStorage, runtimePlatform}
            | with_entries(select(.value != null))
          ')
          ARN=$(aws ecs register-task-definition --cli-input-json "$NEW_DEF" --query 'taskDefinition.taskDefinitionArn' --output text)
          aws ecs update-service --cluster "$CLUSTER" --service "$SERVICE" --task-definition "$ARN" --desired-count 1
          aws ecs wait services-stable --cluster "$CLUSTER" --services "$SERVICE"
"""

    def _get_file_sha(self, path: str) -> str | None:
        try:
            res = subprocess.run(
                ["gh", "api", f"repos/{self.repo_full_name}/contents/{path}"],
                capture_output=True,
                text=True,
            )
            if res.returncode != 0:
                return None
            data = json.loads(res.stdout)
            return data.get("sha")
        except Exception:
            return None

    def _put_file(self, path: str, content: str, message: str) -> None:
        payload = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        }
        sha = self._get_file_sha(path)
        if sha:
            payload["sha"] = sha

        res = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{self.repo_full_name}/contents/{path}",
                "--method",
                "PUT",
                "--input",
                "-",
            ],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            raise RuntimeError(f"Failed to put {path}: {res.stderr}")

    def _get_repo_config(self, is_integration_test: bool = False) -> Tuple[str, str, str]:
        """
        Get repository configuration from environment variables.
        
        Args:
            is_integration_test: Whether to use test repository configuration
        
        Returns:
            tuple: (repo_owner, repo_name, token)
            
        Raises:
            ValueError: If required environment variables are not set
        """
        repo_owner = os.getenv("GITHUB_REPO_OWNER")
        
        if is_integration_test:
            repo_name = os.getenv("GITHUB_TEST_REPO_NAME")
        else:
            repo_name = os.getenv("GITHUB_REPO_NAME")
        
        token = os.getenv("GITHUB_TOKEN")
        
        if not repo_owner:
            raise ValueError("GITHUB_REPO_OWNER environment variable is required")
        if not repo_name:
            if is_integration_test:
                raise ValueError("GITHUB_TEST_REPO_NAME environment variable is required for integration tests")
            else:
                raise ValueError("GITHUB_REPO_NAME environment variable is required")
        if not token:
            raise ValueError("GITHUB_TOKEN environment variable is required")
        
        return repo_owner, repo_name, token


if __name__ == "__main__":
    # This allows the module to be run standalone for testing
    repo = GitHubRepoAgentEnvironment()
    repo.reset() 