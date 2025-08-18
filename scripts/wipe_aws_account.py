#!/usr/bin/env python3
"""
AWS Account Wipe Script
Systematically removes all resources from TEST and SANDBOX accounts.
"""

import boto3  # type: ignore
import time
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

def delete_ecs_services(session: boto3.Session, account_type: str) -> None:
    """Delete all ECS services."""
    ecs_client = session.client('ecs')
    
    try:
        # List all clusters
        clusters_response = ecs_client.list_clusters()
        
        for cluster_arn in clusters_response['clusterArns']:
            cluster_name = cluster_arn.split('/')[-1]
            print(f"  Processing cluster: {cluster_name}")
            
            # List services in cluster
            services_response = ecs_client.list_services(cluster=cluster_arn)
            
            for service_arn in services_response['serviceArns']:
                service_name = service_arn.split('/')[-1]
                print(f"    Scaling down service: {service_name}")
                
                # Scale down to 0
                ecs_client.update_service(
                    cluster=cluster_arn,
                    service=service_arn,
                    desiredCount=0
                )
                
                # Wait briefly for scale down
                time.sleep(5)
                
                # Delete service
                print(f"    Deleting service: {service_name}")
                ecs_client.delete_service(
                    cluster=cluster_arn,
                    service=service_arn
                )
                
    except Exception as e:
        print(f"  Error deleting ECS services: {e}")

def delete_ecs_clusters(session: boto3.Session, account_type: str) -> None:
    """Delete all ECS clusters."""
    ecs_client = session.client('ecs')
    
    try:
        clusters_response = ecs_client.list_clusters()
        
        for cluster_arn in clusters_response['clusterArns']:
            cluster_name = cluster_arn.split('/')[-1]
            print(f"  Deleting cluster: {cluster_name}")
            
            # Wait for services to be deleted
            time.sleep(10)
            
            ecs_client.delete_cluster(cluster=cluster_arn)
            
    except Exception as e:
        print(f"  Error deleting ECS clusters: {e}")

def delete_load_balancers(session: boto3.Session, account_type: str) -> None:
    """Delete all application load balancers."""
    elbv2_client = session.client('elbv2')
    
    try:
        response = elbv2_client.describe_load_balancers()
        
        for lb in response['LoadBalancers']:
            if account_type in lb['LoadBalancerName']:
                print(f"  Deleting load balancer: {lb['LoadBalancerName']}")
                elbv2_client.delete_load_balancer(LoadBalancerArn=lb['LoadBalancerArn'])
                
    except Exception as e:
        print(f"  Error deleting load balancers: {e}")

def delete_target_groups(session: boto3.Session, account_type: str) -> None:
    """Delete all target groups."""
    elbv2_client = session.client('elbv2')
    
    try:
        response = elbv2_client.describe_target_groups()
        
        for tg in response['TargetGroups']:
            if account_type in tg['TargetGroupName']:
                print(f"  Deleting target group: {tg['TargetGroupName']}")
                elbv2_client.delete_target_group(TargetGroupArn=tg['TargetGroupArn'])
                
    except Exception as e:
        print(f"  Error deleting target groups: {e}")

def delete_security_groups(session: boto3.Session, account_type: str) -> None:
    """Delete all security groups."""
    ec2_client = session.client('ec2')
    
    try:
        response = ec2_client.describe_security_groups()
        
        for sg in response['SecurityGroups']:
            if sg['GroupName'] != 'default' and account_type in sg['GroupName']:
                print(f"  Deleting security group: {sg['GroupName']}")
                try:
                    ec2_client.delete_security_group(GroupId=sg['GroupId'])
                except Exception as e:
                    print(f"    Error deleting security group {sg['GroupName']}: {e}")
                
    except Exception as e:
        print(f"  Error deleting security groups: {e}")

def delete_subnets(session: boto3.Session, account_type: str) -> None:
    """Delete all subnets."""
    ec2_client = session.client('ec2')
    
    try:
        response = ec2_client.describe_subnets()
        
        for subnet in response['Subnets']:
            # Check if subnet belongs to our VPCs
            vpc_response = ec2_client.describe_vpcs(VpcIds=[subnet['VpcId']])
            for vpc in vpc_response['Vpcs']:
                vpc_name = None
                if 'Tags' in vpc:
                    for tag in vpc['Tags']:
                        if tag['Key'] == 'Name':
                            vpc_name = tag['Value']
                            break
                
                if vpc_name and account_type in vpc_name:
                    print(f"  Deleting subnet: {subnet['SubnetId']}")
                    try:
                        ec2_client.delete_subnet(SubnetId=subnet['SubnetId'])
                    except Exception as e:
                        print(f"    Error deleting subnet {subnet['SubnetId']}: {e}")
                
    except Exception as e:
        print(f"  Error deleting subnets: {e}")

def delete_internet_gateways(session: boto3.Session, account_type: str) -> None:
    """Delete all internet gateways."""
    ec2_client = session.client('ec2')
    
    try:
        response = ec2_client.describe_internet_gateways()
        
        for igw in response['InternetGateways']:
            # Check if attached to our VPCs
            for attachment in igw['Attachments']:
                vpc_response = ec2_client.describe_vpcs(VpcIds=[attachment['VpcId']])
                for vpc in vpc_response['Vpcs']:
                    vpc_name = None
                    if 'Tags' in vpc:
                        for tag in vpc['Tags']:
                            if tag['Key'] == 'Name':
                                vpc_name = tag['Value']
                                break
                    
                    if vpc_name and account_type in vpc_name:
                        print(f"  Detaching and deleting internet gateway: {igw['InternetGatewayId']}")
                        try:
                            ec2_client.detach_internet_gateway(
                                InternetGatewayId=igw['InternetGatewayId'],
                                VpcId=attachment['VpcId']
                            )
                            ec2_client.delete_internet_gateway(InternetGatewayId=igw['InternetGatewayId'])
                        except Exception as e:
                            print(f"    Error deleting internet gateway {igw['InternetGatewayId']}: {e}")
                
    except Exception as e:
        print(f"  Error deleting internet gateways: {e}")

def delete_route_tables(session: boto3.Session, account_type: str) -> None:
    """Delete all route tables."""
    ec2_client = session.client('ec2')
    
    try:
        response = ec2_client.describe_route_tables()
        
        for rt in response['RouteTables']:
            # Check if belongs to our VPCs
            vpc_response = ec2_client.describe_vpcs(VpcIds=[rt['VpcId']])
            for vpc in vpc_response['Vpcs']:
                vpc_name = None
                if 'Tags' in vpc:
                    for tag in vpc['Tags']:
                        if tag['Key'] == 'Name':
                            vpc_name = tag['Value']
                            break
                
                if vpc_name and account_type in vpc_name:
                    # Don't delete main route table
                    is_main = any(assoc.get('Main', False) for assoc in rt['Associations'])
                    if not is_main:
                        print(f"  Deleting route table: {rt['RouteTableId']}")
                        try:
                            ec2_client.delete_route_table(RouteTableId=rt['RouteTableId'])
                        except Exception as e:
                            print(f"    Error deleting route table {rt['RouteTableId']}: {e}")
                
    except Exception as e:
        print(f"  Error deleting route tables: {e}")

def delete_vpcs(session: boto3.Session, account_type: str) -> None:
    """Delete all VPCs."""
    ec2_client = session.client('ec2')
    
    try:
        response = ec2_client.describe_vpcs()
        
        for vpc in response['Vpcs']:
            if not vpc['IsDefault']:
                vpc_name = None
                if 'Tags' in vpc:
                    for tag in vpc['Tags']:
                        if tag['Key'] == 'Name':
                            vpc_name = tag['Value']
                            break
                
                if vpc_name and account_type in vpc_name:
                    print(f"  Deleting VPC: {vpc_name} ({vpc['VpcId']})")
                    try:
                        ec2_client.delete_vpc(VpcId=vpc['VpcId'])
                    except Exception as e:
                        print(f"    Error deleting VPC {vpc['VpcId']}: {e}")
                
    except Exception as e:
        print(f"  Error deleting VPCs: {e}")

def delete_iam_roles(session: boto3.Session, account_type: str) -> None:
    """Delete all IAM roles."""
    iam_client = session.client('iam')
    
    try:
        response = iam_client.list_roles()
        
        for role in response['Roles']:
            if role['RoleName'].startswith(f'{account_type}-'):
                print(f"  Deleting IAM role: {role['RoleName']}")
                
                # Detach managed policies
                attached_policies = iam_client.list_attached_role_policies(RoleName=role['RoleName'])
                for policy in attached_policies['AttachedPolicies']:
                    iam_client.detach_role_policy(
                        RoleName=role['RoleName'],
                        PolicyArn=policy['PolicyArn']
                    )
                
                # Delete inline policies
                inline_policies = iam_client.list_role_policies(RoleName=role['RoleName'])
                for policy_name in inline_policies['PolicyNames']:
                    iam_client.delete_role_policy(
                        RoleName=role['RoleName'],
                        PolicyName=policy_name
                    )
                
                # Delete role
                iam_client.delete_role(RoleName=role['RoleName'])
                
    except Exception as e:
        print(f"  Error deleting IAM roles: {e}")

def delete_ecr_repositories(session: boto3.Session, account_type: str) -> None:
    """Delete all ECR repositories."""
    ecr_client = session.client('ecr')
    
    try:
        response = ecr_client.describe_repositories()
        
        for repo in response['repositories']:
            if repo['repositoryName'].startswith(f'{account_type}-'):
                print(f"  Deleting ECR repository: {repo['repositoryName']}")
                ecr_client.delete_repository(
                    repositoryName=repo['repositoryName'],
                    force=True
                )
                
    except Exception as e:
        print(f"  Error deleting ECR repositories: {e}")

def delete_cloudwatch_logs(session: boto3.Session, account_type: str) -> None:
    """Delete all CloudWatch log groups."""
    logs_client = session.client('logs')
    
    try:
        response = logs_client.describe_log_groups(logGroupNamePrefix=f'/ecs/{account_type}-')
        
        for log_group in response['logGroups']:
            print(f"  Deleting log group: {log_group['logGroupName']}")
            logs_client.delete_log_group(logGroupName=log_group['logGroupName'])
            
    except Exception as e:
        print(f"  Error deleting CloudWatch logs: {e}")

def wipe_account(account_type: str) -> None:
    """Wipe all resources from an account."""
    print(f"\n🗑️  WIPING {account_type.upper()} ACCOUNT")
    print("=" * 50)
    
    session = get_aws_session(account_type)
    
    # Delete in dependency order
    print("1. Deleting ECS services...")
    delete_ecs_services(session, account_type)
    
    print("2. Deleting ECS clusters...")
    delete_ecs_clusters(session, account_type)
    
    print("3. Deleting load balancers...")
    delete_load_balancers(session, account_type)
    
    print("4. Deleting target groups...")
    delete_target_groups(session, account_type)
    
    print("5. Deleting security groups...")
    delete_security_groups(session, account_type)
    
    print("6. Deleting subnets...")
    delete_subnets(session, account_type)
    
    print("7. Deleting internet gateways...")
    delete_internet_gateways(session, account_type)
    
    print("8. Deleting route tables...")
    delete_route_tables(session, account_type)
    
    print("9. Deleting VPCs...")
    delete_vpcs(session, account_type)
    
    print("10. Deleting IAM roles...")
    delete_iam_roles(session, account_type)
    
    print("11. Deleting ECR repositories...")
    delete_ecr_repositories(session, account_type)
    
    print("12. Deleting CloudWatch logs...")
    delete_cloudwatch_logs(session, account_type)
    
    print(f"✅ {account_type.upper()} account wipe complete!")

def main():
    """Main function to wipe both accounts."""
    print("🚨 AWS ACCOUNT WIPE SCRIPT")
    print("=" * 50)
    print("This will DELETE ALL RESOURCES from both TEST and SANDBOX accounts!")
    
    confirm = input("Are you sure you want to continue? (type 'YES' to confirm): ")
    if confirm != 'YES':
        print("❌ Aborted.")
        return
    
    # Wipe both accounts
    wipe_account('test')
    wipe_account('sandbox')
    
    print("\n🎉 All accounts wiped successfully!")
    print("You can now run inventory to confirm everything is clean.")

if __name__ == '__main__':
    main() 