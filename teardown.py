#!/usr/bin/env python3
"""
Infrastructure Teardown Script

Simple script that destroys terraform infrastructure for both test and sandbox account environments.
Delegates to existing agent environment classes to remove all AWS resources and associated costs.
"""

import sys
from dotenv import load_dotenv
from agent_environment.aws_fargate_agent_environment import AWSFargateAgentEnvironment
from logger.log_wrapper import get_logger

load_dotenv(override=True)

logger = get_logger("teardown", __name__)


class Teardown:
    """
    Infrastructure Teardown class for removing AWS resources.
    """
    
    def teardown(self) -> bool:
        """
        Destroy infrastructure for both test and sandbox account environments.
        
        Returns:
            bool: True if all environments destroyed successfully, False otherwise
        """
        logger.info("Starting infrastructure teardown for both account environments")
        
        account_environments = [
            ("sandbox", False),  # (account_environment, is_integration_test)
            ("test", True)
        ]
        
        success_count = 0
        total_count = len(account_environments)
        
        for account_env, is_integration_test in account_environments:
            try:
                logger.info(f"Destroying infrastructure for account_environment: {account_env}")
                
                # Initialize agent environment
                aws_fargate = AWSFargateAgentEnvironment(is_integration_test=is_integration_test)
                
                # First, clean up running services and images to reduce terraform dependency issues
                try:
                    logger.info(f"Cleaning up running services for account_environment: {account_env}")
                    aws_fargate.reset()  # Clean all app environments
                    logger.info(f"Service cleanup completed for account_environment: {account_env}")
                except Exception as e:
                    logger.warning(f"Service cleanup failed for account_environment: {account_env}: {str(e)}")
                    # Continue with terraform destroy even if cleanup fails
                
                # Destroy terraform infrastructure
                success = aws_fargate.destroy_terraform()
                
                if success:
                    logger.info(f"Successfully destroyed infrastructure for account_environment: {account_env}")
                    success_count += 1
                else:
                    logger.error(f"Failed to destroy infrastructure for account_environment: {account_env}")
                    
            except Exception as e:
                logger.error(f"Error destroying infrastructure for account_environment: {account_env}: {str(e)}")
        
        if success_count == total_count:
            logger.info(f"All {total_count} account environments destroyed successfully!")
            return True
        else:
            logger.error(f"Only {success_count} out of {total_count} account environments destroyed successfully")
            return False


def main():
    """Main entry point for the teardown script."""
    try:
        teardown = Teardown()
        success = teardown.teardown()
        
        if success:
            logger.info("Infrastructure teardown completed successfully!")
            sys.exit(0)
        else:
            logger.error("Infrastructure teardown failed!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Teardown script failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 