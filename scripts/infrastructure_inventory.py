#!/usr/bin/env python3
"""
Infrastructure Inventory Script
Captures current state of AWS resources across TEST and SANDBOX accounts
for comparison before/after setup/teardown operations.
"""

import json
import boto3  # type: ignore
from datetime import datetime
from typing import Dict, List, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_aws_session(account_type: str) -> boto3.Session:
    """Get AWS session for specified account type."""
    if account_type == 'test':
        return boto3.Session(
            aws_access_key_id=os.getenv('TEST_AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('TEST_AWS_SECRET_ACCESS_KEY'),
            region_name='eu-central-1'
        )
    elif account_type == 'sandbox':
        return boto3.Session(
            aws_access_key_id=os.getenv('SANDBOX_AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('SANDBOX_AWS_SECRET_ACCESS_KEY'),
            region_name='eu-central-1'
        )
    else:
        raise ValueError(f"Unknown account type: {account_type}")

def inventory_ecr_repositories(session: boto3.Session) -> List[Dict[str, Any]]:
    """Inventory ECR repositories."""
    ecr_client = session.client('ecr')
    repositories = []
    
    try:
        response = ecr_client.describe_repositories()
        for repo in response['repositories']:
            repositories.append({
                'name': repo['repositoryName'],
                'arn': repo['repositoryArn'],
                'uri': repo['repositoryUri'],
                'created_at': repo['createdAt'].isoformat(),
                'registry_id': repo['registryId']
            })
    except Exception as e:
        print(f"Error inventorying ECR repositories: {e}")
    
    return repositories

def inventory_ecs_clusters(session: boto3.Session) -> List[Dict[str, Any]]:
    """Inventory ECS clusters."""
    ecs_client = session.client('ecs')
    clusters = []
    
    try:
        response = ecs_client.list_clusters()
        if response['clusterArns']:
            cluster_details = ecs_client.describe_clusters(clusters=response['clusterArns'])
            for cluster in cluster_details['clusters']:
                clusters.append({
                    'name': cluster['clusterName'],
                    'arn': cluster['clusterArn'],
                    'status': cluster['status'],
                    'running_tasks': cluster['runningTasksCount'],
                    'pending_tasks': cluster['pendingTasksCount'],
                    'active_services': cluster['activeServicesCount']
                })
    except Exception as e:
        print(f"Error inventorying ECS clusters: {e}")
    
    return clusters

def inventory_ecs_services(session: boto3.Session, clusters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Inventory ECS services."""
    ecs_client = session.client('ecs')
    services = []
    
    for cluster in clusters:
        try:
            response = ecs_client.list_services(cluster=cluster['arn'])
            if response['serviceArns']:
                service_details = ecs_client.describe_services(
                    cluster=cluster['arn'],
                    services=response['serviceArns']
                )
                for service in service_details['services']:
                    services.append({
                        'name': service['serviceName'],
                        'arn': service['serviceArn'],
                        'cluster_name': cluster['name'],
                        'status': service['status'],
                        'running_count': service['runningCount'],
                        'pending_count': service['pendingCount'],
                        'desired_count': service['desiredCount'],
                        'task_definition': service['taskDefinition']
                    })
        except Exception as e:
            print(f"Error inventorying ECS services for cluster {cluster['name']}: {e}")
    
    return services

def inventory_iam_roles(session: boto3.Session, prefix_filters: List[str]) -> List[Dict[str, Any]]:
    """Inventory IAM roles with specific prefixes."""
    iam_client = session.client('iam')
    roles = []
    
    try:
        response = iam_client.list_roles()
        for role in response['Roles']:
            role_name = role['RoleName']
            if any(role_name.startswith(prefix) for prefix in prefix_filters):
                roles.append({
                    'name': role_name,
                    'arn': role['Arn'],
                    'path': role['Path'],
                    'created_date': role['CreateDate'].isoformat(),
                    'assume_role_policy': role['AssumeRolePolicyDocument']
                })
    except Exception as e:
        print(f"Error inventorying IAM roles: {e}")
    
    return roles

def inventory_vpcs(session: boto3.Session, name_filters: List[str]) -> List[Dict[str, Any]]:
    """Inventory VPCs with specific name tags."""
    ec2_client = session.client('ec2')
    vpcs = []
    
    try:
        response = ec2_client.describe_vpcs()
        for vpc in response['Vpcs']:
            vpc_name = None
            if 'Tags' in vpc:
                for tag in vpc['Tags']:
                    if tag['Key'] == 'Name':
                        vpc_name = tag['Value']
                        break
            
            if vpc_name and any(name_filter in vpc_name for name_filter in name_filters):
                vpcs.append({
                    'id': vpc['VpcId'],
                    'name': vpc_name,
                    'cidr_block': vpc['CidrBlock'],
                    'state': vpc['State'],
                    'is_default': vpc['IsDefault']
                })
    except Exception as e:
        print(f"Error inventorying VPCs: {e}")
    
    return vpcs

def inventory_cloudwatch_logs(session: boto3.Session, prefix_filters: List[str]) -> List[Dict[str, Any]]:
    """Inventory CloudWatch log groups with specific prefixes."""
    logs_client = session.client('logs')
    log_groups = []
    
    for prefix in prefix_filters:
        try:
            response = logs_client.describe_log_groups(logGroupNamePrefix=prefix)
            for log_group in response['logGroups']:
                log_groups.append({
                    'name': log_group['logGroupName'],
                    'arn': log_group['arn'],
                    'creation_time': datetime.fromtimestamp(log_group['creationTime'] / 1000).isoformat(),
                    'retention_days': log_group.get('retentionInDays', 'Never expire'),
                    'stored_bytes': log_group.get('storedBytes', 0)
                })
        except Exception as e:
            print(f"Error inventorying CloudWatch logs with prefix {prefix}: {e}")
    
    return log_groups

def inventory_load_balancers(session: boto3.Session, name_filters: List[str]) -> List[Dict[str, Any]]:
    """Inventory Application Load Balancers with specific name patterns."""
    elbv2_client = session.client('elbv2')
    load_balancers = []
    
    try:
        response = elbv2_client.describe_load_balancers()
        for lb in response['LoadBalancers']:
            lb_name = lb['LoadBalancerName']
            if any(name_filter in lb_name for name_filter in name_filters):
                load_balancers.append({
                    'name': lb_name,
                    'arn': lb['LoadBalancerArn'],
                    'dns_name': lb['DNSName'],
                    'scheme': lb['Scheme'],
                    'state': lb['State']['Code'],
                    'type': lb['Type'],
                    'vpc_id': lb['VpcId']
                })
    except Exception as e:
        print(f"Error inventorying Load Balancers: {e}")
    
    return load_balancers

def inventory_account(account_type: str) -> Dict[str, Any]:
    """Inventory all resources for a specific account."""
    print(f"Inventorying {account_type.upper()} account...")
    
    session = get_aws_session(account_type)
    
    # Define filters based on account type
    role_prefixes = [f'{account_type}-ecs', f'{account_type}-task', f'{account_type}-execution']
    vpc_name_filters = [account_type]
    log_prefixes = [f'/ecs/{account_type}-']
    lb_name_filters = [account_type]
    
    inventory = {
        'account_type': account_type,
        'region': 'eu-central-1',
        'timestamp': datetime.now().isoformat(),
        'ecr_repositories': inventory_ecr_repositories(session),
        'ecs_clusters': inventory_ecs_clusters(session),
        'iam_roles': inventory_iam_roles(session, role_prefixes),
        'vpcs': inventory_vpcs(session, vpc_name_filters),
        'cloudwatch_logs': inventory_cloudwatch_logs(session, log_prefixes),
        'load_balancers': inventory_load_balancers(session, lb_name_filters)
    }
    
    # Add ECS services after we have clusters
    ecs_clusters = inventory['ecs_clusters']
    inventory['ecs_services'] = inventory_ecs_services(session, ecs_clusters)  # type: ignore
    
    return inventory

def main():
    """Main function to inventory both accounts and write to file."""
    print("Starting infrastructure inventory...")
    
    full_inventory = {
        'inventory_timestamp': datetime.now().isoformat(),
        'accounts': {}
    }
    
    # Inventory both accounts
    for account_type in ['test', 'sandbox']:
        try:
            full_inventory['accounts'][account_type] = inventory_account(account_type)
        except Exception as e:
            print(f"Error inventorying {account_type} account: {e}")
            full_inventory['accounts'][account_type] = {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    # Write to file
    output_file = 'temp/infrastructure_inventory.json'
    with open(output_file, 'w') as f:
        json.dump(full_inventory, f, indent=2, default=str)
    
    print(f"Infrastructure inventory written to {output_file}")
    
    # Print summary
    print("\n=== INVENTORY SUMMARY ===")
    for account_type, account_data in full_inventory['accounts'].items():
        if 'error' in account_data:
            print(f"{account_type.upper()} Account: ERROR - {account_data['error']}")
        else:
            print(f"{account_type.upper()} Account:")
            print(f"  ECR Repositories: {len(account_data['ecr_repositories'])}")
            print(f"  ECS Clusters: {len(account_data['ecs_clusters'])}")
            print(f"  ECS Services: {len(account_data['ecs_services'])}")
            print(f"  IAM Roles: {len(account_data['iam_roles'])}")
            print(f"  VPCs: {len(account_data['vpcs'])}")
            print(f"  CloudWatch Log Groups: {len(account_data['cloudwatch_logs'])}")
            print(f"  Load Balancers: {len(account_data['load_balancers'])}")

if __name__ == '__main__':
    main() 