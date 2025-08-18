#!/usr/bin/env python3
"""
AWS CLI Utils for Benchmark Evaluations

Provides utilities for AWS CLI operations during benchmark evaluations.
"""

import os
import subprocess
import json
from typing import Optional
from dotenv import load_dotenv
from logger.log_wrapper import get_logger

load_dotenv(override=True)

logger = get_logger("evaluations:aws", __name__)


def _get_aws_env() -> dict:
    """
    Get environment variables for AWS CLI subprocess calls.
    
    Returns:
        dict: Environment variables with proper AWS credentials
    """
    env = os.environ.copy()
    
    # Use production AWS credentials for evaluations
    aws_region = os.getenv("AWS_DEFAULT_REGION")
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    if aws_region:
        env["AWS_DEFAULT_REGION"] = aws_region
    if aws_access_key_id:
        env["AWS_ACCESS_KEY_ID"] = aws_access_key_id
    if aws_secret_access_key:
        env["AWS_SECRET_ACCESS_KEY"] = aws_secret_access_key
        
    return env


def get_prod_load_balancer_url() -> str:
    """
    Get the production load balancer URL using AWS CLI.
    
    Returns:
        String containing the URL or error message
    """
    try:
        aws_region = os.getenv("AWS_DEFAULT_REGION")
        
        if not aws_region:
            return "Error: AWS_DEFAULT_REGION environment variable not set"
        
        logger.info(f"Getting production load balancer URL in region {aws_region}")
        
        # Get load balancer ARN
        cmd = [
            "aws", "elbv2", "describe-load-balancers",
            "--region", aws_region,
            "--query", "LoadBalancers[?contains(LoadBalancerName, 'prod')].LoadBalancerArn",
            "--output", "text"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=_get_aws_env(),
            timeout=30
        )
        
        if result.returncode != 0:
            return f"Error getting load balancer ARN: {result.stderr}"
        
        lb_arn = result.stdout.strip()
        if not lb_arn:
            return "Error: No production load balancer found"
        
        # Get load balancer DNS name
        cmd = [
            "aws", "elbv2", "describe-load-balancers",
            "--region", aws_region,
            "--load-balancer-arns", lb_arn,
            "--query", "LoadBalancers[0].DNSName",
            "--output", "text"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=_get_aws_env(),
            timeout=30
        )
        
        if result.returncode != 0:
            return f"Error getting load balancer DNS: {result.stderr}"
        
        dns_name = result.stdout.strip()
        if not dns_name:
            return "Error: Could not get load balancer DNS name"
        
        # Construct URL
        url = f"http://{dns_name}"
        logger.info(f"Production load balancer URL: {url}")
        return url
        
    except subprocess.TimeoutExpired:
        return "Error: AWS CLI command timed out"
    except Exception as e:
        return f"Error getting production load balancer URL: {e}"


def get_prod_service_health() -> str:
    """
    Get the health status of production services using AWS CLI.
    
    Returns:
        String containing the health status or error message
    """
    try:
        aws_region = os.getenv("AWS_DEFAULT_REGION")
        
        if not aws_region:
            return "Error: AWS_DEFAULT_REGION environment variable not set"
        
        logger.info(f"Getting production service health in region {aws_region}")
        
        # Get ECS service ARN
        cmd = [
            "aws", "ecs", "list-services",
            "--region", aws_region,
            "--cluster", "sandbox-prod",
            "--query", "serviceArns[?contains(@, 'prod')]",
            "--output", "text"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=_get_aws_env(),
            timeout=30
        )
        
        if result.returncode != 0:
            return f"Error getting ECS services: {result.stderr}"
        
        service_arns = result.stdout.strip().split()
        if not service_arns:
            return "Error: No production ECS services found"
        
        # Get service details
        health_info = []
        for service_arn in service_arns[:3]:  # Limit to first 3 services
            cmd = [
                "aws", "ecs", "describe-services",
                "--region", aws_region,
                "--cluster", "sandbox-prod",
                "--services", service_arn,
                "--query", "services[0].{ServiceName:serviceName,RunningCount:runningCount,DesiredCount:desiredCount,Status:status}",
                "--output", "json"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=_get_aws_env(),
                timeout=30
            )
            
            if result.returncode == 0:
                try:
                    service_info = json.loads(result.stdout)
                    health_info.append(service_info)
                except json.JSONDecodeError:
                    continue
        
        if not health_info:
            return "Error: Could not get service health information"
        
        # Format health information
        health_summary = "Production Service Health:\n"
        for service in health_info:
            health_summary += f"- {service['ServiceName']}: {service['RunningCount']}/{service['DesiredCount']} running ({service['Status']})\n"
        
        return health_summary
        
    except subprocess.TimeoutExpired:
        return "Error: AWS CLI command timed out"
    except Exception as e:
        return f"Error getting production service health: {e}" 