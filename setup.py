#!/usr/bin/env python3
"""
Infrastructure Setup Script

Simple script that deploys terraform infrastructure for both test and sandbox account environments.
Delegates to existing agent environment classes to create all AWS resources.
"""

import sys
from dotenv import load_dotenv
from agent_environment.aws_fargate_agent_environment import AWSFargateAgentEnvironment
from logger.log_wrapper import get_logger

load_dotenv(override=True)

logger = get_logger("setup", __name__)


class Setup:
    """
    Infrastructure Setup class for creating AWS resources.
    """
    
    def setup(self) -> bool:
        """
        Deploy infrastructure for both test and sandbox account environments.
        
        Returns:
            bool: True if all environments deployed successfully, False otherwise
        """
        logger.info("Starting infrastructure deployment for both account environments")
        
        account_environments = [
            ("sandbox", False),  # (account_environment, is_integration_test)
            ("test", True)
        ]
        
        success_count = 0
        total_count = len(account_environments)
        
        for account_env, is_integration_test in account_environments:
            try:
                logger.info(f"Deploying infrastructure for account_environment: {account_env}")
                
                # Initialize agent environment
                aws_fargate = AWSFargateAgentEnvironment(is_integration_test=is_integration_test)
                
                # Apply terraform infrastructure
                success = aws_fargate.apply_terraform()
                
                if success:
                    logger.info(f"Successfully deployed infrastructure for account_environment: {account_env}")
                    success_count += 1
                else:
                    logger.error(f"Failed to deploy infrastructure for account_environment: {account_env}")
                    
            except Exception as e:
                logger.error(f"Error deploying infrastructure for account_environment: {account_env}: {str(e)}")
        
        if success_count == total_count:
            logger.info(f"All {total_count} account environments deployed successfully!")
            return True
        else:
            logger.error(f"Only {success_count} out of {total_count} account environments deployed successfully")
            return False


def main():
    """Main entry point for the setup script."""
    try:
        setup = Setup()
        success = setup.setup()
        
        if success:
            logger.info("Infrastructure setup completed successfully!")
            sys.exit(0)
        else:
            logger.error("Infrastructure setup failed!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Setup script failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 