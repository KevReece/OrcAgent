#!/usr/bin/env python3
"""
Load Balancer URL Retrieval Script

Gets load balancer URLs for all environments across test and sandbox accounts.
Retrieves URLs for dev, test, and production app environments in both accounts.
"""

import os
import sys
from typing import Dict, List, Tuple
from dotenv import load_dotenv

# Add the project root to the path to import tools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.aws_cli_tools import get_tools
from tools.context import ToolsContext
from logger.log_wrapper import get_logger

# Load environment variables
load_dotenv()

# Define the environments to check
ENVIRONMENTS = [
    ('test', 'dev'),
    ('test', 'test'), 
    ('test', 'prod'),
    ('sandbox', 'dev'),
    ('sandbox', 'test'),
    ('sandbox', 'prod')
]

def create_tools_context(account_environment: str, is_integration_test: bool = False) -> ToolsContext:
    """Create a tools context for the specified account environment."""
    return ToolsContext(
        role_repository=None,
        self_worker_name=None,
        agent_work_dir=os.getcwd(),
        is_integration_test=is_integration_test
    )

def get_load_balancer_urls_for_environment(account_environment: str, app_environment: str) -> str:
    """
    Get load balancer URL for a specific account and app environment.
    
    Args:
        account_environment: Account environment ('test' or 'sandbox')
        app_environment: App environment ('dev', 'test', or 'prod')
    
    Returns:
        Load balancer URL information or error message
    """
    logger = get_logger("script:lb-urls", __name__)
    
    # Determine if this is an integration test environment
    is_integration_test = account_environment == 'test'
    
    # Create tools context
    tools_context = create_tools_context(account_environment, is_integration_test)
    
    # Get the AWS tools
    aws_tools = get_tools(tools_context)
    
    # Find the load balancer URL function
    lb_function = None
    for tool in aws_tools:
        if tool.__name__ == 'aws_get_load_balancer_url':
            lb_function = tool
            break
    
    if not lb_function:
        return f"❌ Load balancer URL function not found in AWS tools"
    
    # Call the function with the app environment
    try:
        result = lb_function(app_environment)
        logger.info(f"Retrieved load balancer URL for {account_environment}-{app_environment}")
        return result
    except Exception as e:
        error_msg = f"❌ Error getting load balancer URL for {account_environment}-{app_environment}: {str(e)}"
        logger.error(error_msg)
        return error_msg

def main() -> None:
    """Main function to get load balancer URLs for all environments."""
    logger = get_logger("script:lb-urls", __name__)
    
    logger.info("Starting load balancer URL retrieval for all environments")
    
    results: Dict[str, str] = {}
    
    # Get URLs for all environments
    for account_env, app_env in ENVIRONMENTS:
        logger.info(f"Getting load balancer URL for {account_env}-{app_env}")
        result = get_load_balancer_urls_for_environment(account_env, app_env)
        results[f"{account_env}-{app_env}"] = result
    
    # Display results
    print("\n" + "="*80)
    print("LOAD BALANCER URLS FOR ALL ENVIRONMENTS")
    print("="*80)
    
    for environment, result in results.items():
        print(f"\n{environment.upper()}:")
        print("-" * len(environment))
        print(result)
    
    print("\n" + "="*80)
    logger.info("Load balancer URL retrieval completed")

if __name__ == "__main__":
    main() 