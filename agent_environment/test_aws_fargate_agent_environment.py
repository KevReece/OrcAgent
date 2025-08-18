"""
Unit tests for AWS Fargate Management Module

This module tests the AWS Fargate deployment and cleaning functionality,
including integration tests for deploy, clean, and verification operations.
Uses is_integration_test parameter for test configuration.
"""

import unittest
from typing import Dict, List, Any
from .aws_fargate_agent_environment import AWSFargateAgentEnvironment


class TestAWSFargateResourceVerification(unittest.TestCase):
    """
    Integration test cases for AWS resource verification.
    
    CRITICAL: These tests MUST NOT create, modify, or destroy AWS resources.
    They should ONLY verify the current state of existing infrastructure.
    Use setup.py to create resources and teardown.py to destroy them.
    """

    def setUp(self):
        """Set up test fixtures."""
        # Try to initialize the agent environment to verify credentials are available
        try:
            self.aws_fargate = AWSFargateAgentEnvironment(is_integration_test=True)
        except ValueError as e:
            self.fail(f"Test AWS credentials not configured: {e}")

        # Verify we're in test mode
        if self.aws_fargate.account_environment != 'test':
            self.fail("Integration tests can only run in test environment")

    def test_comprehensive_aws_infrastructure_verification(self):
        """
        Comprehensive test: Verify all expected AWS resources are in place.
        This test checks for all infrastructure components that should exist after setup.py.
        """
        print("\n🔍 Comprehensive AWS Infrastructure Verification")
        print("=" * 60)
        
        # Expected resource counts based on terraform configuration
        expected_resources = {
            'ecr_repositories': 1,
            'ecs_clusters': 3,  # dev, test, prod
            'ecs_services': 3,  # one per cluster
            'iam_roles': 2,     # task execution + task role
            'vpcs': 1,
            'cloudwatch_logs': 3,  # one per environment
            'load_balancers': 3    # one per environment
        }
        
        missing_resources = []
        resource_details = {}
        
        try:
            # Check ECR repositories
            print("📦 Checking ECR repositories...")
            ecr_repos = self._check_ecr_repositories()
            resource_details['ecr_repositories'] = ecr_repos
            if len(ecr_repos) != expected_resources['ecr_repositories']:
                missing_resources.append(f"ECR repositories: expected {expected_resources['ecr_repositories']}, found {len(ecr_repos)}")
            else:
                print(f"   ✅ Found {len(ecr_repos)} ECR repository")
            
            # Check ECS clusters
            print("🏗️ Checking ECS clusters...")
            ecs_clusters = self._check_ecs_clusters()
            resource_details['ecs_clusters'] = ecs_clusters
            if len(ecs_clusters) != expected_resources['ecs_clusters']:
                missing_resources.append(f"ECS clusters: expected {expected_resources['ecs_clusters']}, found {len(ecs_clusters)}")
            else:
                print(f"   ✅ Found {len(ecs_clusters)} ECS clusters")
                for cluster in ecs_clusters:
                    print(f"      - {cluster['name']} ({cluster['status']})")
            
            # Check ECS services
            print("⚙️ Checking ECS services...")
            ecs_services = self._check_ecs_services(ecs_clusters)
            resource_details['ecs_services'] = ecs_services
            if len(ecs_services) != expected_resources['ecs_services']:
                missing_resources.append(f"ECS services: expected {expected_resources['ecs_services']}, found {len(ecs_services)}")
            else:
                print(f"   ✅ Found {len(ecs_services)} ECS services")
                for service in ecs_services:
                    print(f"      - {service['name']} ({service['status']}, desired: {service['desired_count']})")
            
            # Check IAM roles
            print("🔐 Checking IAM roles...")
            iam_roles = self._check_iam_roles()
            resource_details['iam_roles'] = iam_roles
            if len(iam_roles) != expected_resources['iam_roles']:
                missing_resources.append(f"IAM roles: expected {expected_resources['iam_roles']}, found {len(iam_roles)}")
            else:
                print(f"   ✅ Found {len(iam_roles)} IAM roles")
                for role in iam_roles:
                    print(f"      - {role['name']}")
            
            # Check VPCs
            print("🌐 Checking VPCs...")
            vpcs = self._check_vpcs()
            resource_details['vpcs'] = vpcs
            if len(vpcs) != expected_resources['vpcs']:
                missing_resources.append(f"VPCs: expected {expected_resources['vpcs']}, found {len(vpcs)}")
            else:
                print(f"   ✅ Found {len(vpcs)} VPC")
                for vpc in vpcs:
                    print(f"      - {vpc['name']} ({vpc['id']}, {vpc['cidr_block']})")
            
            # Check CloudWatch log groups
            print("📊 Checking CloudWatch log groups...")
            log_groups = self._check_cloudwatch_logs()
            resource_details['cloudwatch_logs'] = log_groups
            if len(log_groups) != expected_resources['cloudwatch_logs']:
                missing_resources.append(f"CloudWatch log groups: expected {expected_resources['cloudwatch_logs']}, found {len(log_groups)}")
            else:
                print(f"   ✅ Found {len(log_groups)} CloudWatch log groups")
                for log_group in log_groups:
                    print(f"      - {log_group['name']}")
            
            # Check Load Balancers
            print("⚖️ Checking Load Balancers...")
            load_balancers = self._check_load_balancers()
            resource_details['load_balancers'] = load_balancers
            if len(load_balancers) != expected_resources['load_balancers']:
                missing_resources.append(f"Load Balancers: expected {expected_resources['load_balancers']}, found {len(load_balancers)}")
            else:
                print(f"   ✅ Found {len(load_balancers)} Load Balancers")
                for lb in load_balancers:
                    print(f"      - {lb['name']} ({lb['state']})")
            
            # Generate comprehensive failure message if resources are missing
            if missing_resources:
                total_expected = sum(expected_resources.values())
                total_found = sum(len(resource_details[key]) for key in resource_details)
                
                failure_message = (
                    f"\n❌ AWS Infrastructure Verification Failed\n"
                    f"Expected {total_expected} total resources, found {total_found}\n\n"
                    f"Missing or incorrect resource counts:\n"
                )
                
                for missing in missing_resources:
                    failure_message += f"  • {missing}\n"
                
                failure_message += (
                    f"\nDetailed breakdown:\n"
                    f"  📦 ECR repositories: {len(resource_details['ecr_repositories'])}/{expected_resources['ecr_repositories']}\n"
                    f"  🏗️ ECS clusters: {len(resource_details['ecs_clusters'])}/{expected_resources['ecs_clusters']}\n"
                    f"  ⚙️ ECS services: {len(resource_details['ecs_services'])}/{expected_resources['ecs_services']}\n"
                    f"  🔐 IAM roles: {len(resource_details['iam_roles'])}/{expected_resources['iam_roles']}\n"
                    f"  🌐 VPCs: {len(resource_details['vpcs'])}/{expected_resources['vpcs']}\n"
                    f"  📊 CloudWatch logs: {len(resource_details['cloudwatch_logs'])}/{expected_resources['cloudwatch_logs']}\n"
                    f"  ⚖️ Load Balancers: {len(resource_details['load_balancers'])}/{expected_resources['load_balancers']}\n"
                    f"\n⚠️ This test is expected to fail if 'python setup.py' has not been run yet.\n"
                    f"   Run 'python setup.py' to deploy the required AWS infrastructure.\n"
                    f"   Account: {self.aws_fargate.account_environment}\n"
                    f"   Region: {self.aws_fargate.aws_region}"
                )
                
                self.fail(failure_message)
            
            print("\n✅ All AWS infrastructure components verified successfully!")
            print(f"   Total resources found: {sum(len(resource_details[key]) for key in resource_details)}")
            print("   Infrastructure is ready for agent operations.")
            
        except Exception as e:
            self.fail(f"Infrastructure verification failed with error: {str(e)}\n\n"
                     f"⚠️ This test is expected to fail if 'python setup.py' has not been run yet.\n"
                     f"   Run 'python setup.py' to deploy the required AWS infrastructure.\n"
                     f"   Account: {self.aws_fargate.account_environment}\n"
                     f"   Region: {self.aws_fargate.aws_region}")

    def _check_ecr_repositories(self) -> List[Dict[str, Any]]:
        """Check ECR repositories."""
        repositories = []
        try:
            response = self.aws_fargate.ecr_client.describe_repositories()
            for repo in response['repositories']:
                if repo['repositoryName'].startswith(self.aws_fargate.account_environment):
                    repositories.append({
                        'name': repo['repositoryName'],
                        'arn': repo['repositoryArn'],
                        'uri': repo['repositoryUri']
                    })
        except Exception as e:
            print(f"   ⚠️ Error checking ECR repositories: {e}")
        return repositories

    def _check_ecs_clusters(self) -> List[Dict[str, Any]]:
        """Check ECS clusters."""
        clusters = []
        try:
            response = self.aws_fargate.ecs_client.list_clusters()
            if response['clusterArns']:
                cluster_details = self.aws_fargate.ecs_client.describe_clusters(clusters=response['clusterArns'])
                for cluster in cluster_details['clusters']:
                    if cluster['clusterName'].startswith(self.aws_fargate.account_environment):
                        clusters.append({
                            'name': cluster['clusterName'],
                            'arn': cluster['clusterArn'],
                            'status': cluster['status'],
                            'running_tasks': cluster['runningTasksCount'],
                            'pending_tasks': cluster['pendingTasksCount'],
                            'active_services': cluster['activeServicesCount']
                        })
        except Exception as e:
            print(f"   ⚠️ Error checking ECS clusters: {e}")
        return clusters

    def _check_ecs_services(self, clusters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check ECS services."""
        services = []
        for cluster in clusters:
            try:
                response = self.aws_fargate.ecs_client.list_services(cluster=cluster['arn'])
                if response['serviceArns']:
                    service_details = self.aws_fargate.ecs_client.describe_services(
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
                print(f"   ⚠️ Error checking ECS services for cluster {cluster['name']}: {e}")
        return services

    def _check_iam_roles(self) -> List[Dict[str, Any]]:
        """Check IAM roles."""
        roles = []
        role_prefixes = [f'{self.aws_fargate.account_environment}-ecs']
        try:
            iam_client = self.aws_fargate.session.client('iam')
            response = iam_client.list_roles()
            for role in response['Roles']:
                role_name = role['RoleName']
                if any(role_name.startswith(prefix) for prefix in role_prefixes):
                    roles.append({
                        'name': role_name,
                        'arn': role['Arn'],
                        'path': role['Path'],
                        'created_date': role['CreateDate'].isoformat()
                    })
        except Exception as e:
            print(f"   ⚠️ Error checking IAM roles: {e}")
        return roles

    def _check_vpcs(self) -> List[Dict[str, Any]]:
        """Check VPCs."""
        vpcs = []
        try:
            ec2_client = self.aws_fargate.session.client('ec2')
            response = ec2_client.describe_vpcs()
            for vpc in response['Vpcs']:
                vpc_name = None
                if 'Tags' in vpc:
                    for tag in vpc['Tags']:
                        if tag['Key'] == 'Name':
                            vpc_name = tag['Value']
                            break
                
                if vpc_name and self.aws_fargate.account_environment in vpc_name:
                    vpcs.append({
                        'id': vpc['VpcId'],
                        'name': vpc_name,
                        'cidr_block': vpc['CidrBlock'],
                        'state': vpc['State'],
                        'is_default': vpc['IsDefault']
                    })
        except Exception as e:
            print(f"   ⚠️ Error checking VPCs: {e}")
        return vpcs

    def _check_cloudwatch_logs(self) -> List[Dict[str, Any]]:
        """Check CloudWatch log groups."""
        log_groups = []
        log_prefix = f'/ecs/{self.aws_fargate.account_environment}-'
        try:
            response = self.aws_fargate.logs_client.describe_log_groups(logGroupNamePrefix=log_prefix)
            for log_group in response['logGroups']:
                log_groups.append({
                    'name': log_group['logGroupName'],
                    'arn': log_group['arn'],
                    'retention_days': log_group.get('retentionInDays', 'Never expire'),
                    'stored_bytes': log_group.get('storedBytes', 0)
                })
        except Exception as e:
            print(f"   ⚠️ Error checking CloudWatch logs: {e}")
        return log_groups

    def _check_load_balancers(self) -> List[Dict[str, Any]]:
        """Check Application Load Balancers."""
        load_balancers = []
        try:
            response = self.aws_fargate.elbv2_client.describe_load_balancers()
            for lb in response['LoadBalancers']:
                lb_name = lb['LoadBalancerName']
                if self.aws_fargate.account_environment in lb_name:
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
            print(f"   ⚠️ Error checking Load Balancers: {e}")
        return load_balancers


class TestAWSFargateBasicFunctionality(unittest.TestCase):
    """
    Basic functionality tests for AWSFargateAgentEnvironment class.
    
    CRITICAL: These tests MUST NOT create, modify, or destroy AWS resources.
    They should ONLY test configuration validation and status checking.
    Use setup.py to create resources and teardown.py to destroy them.
    """

    def setUp(self):
        """Set up test fixtures."""
        # Try to initialize the agent environment to verify credentials are available
        try:
            self.aws_fargate = AWSFargateAgentEnvironment(is_integration_test=True)
        except ValueError as e:
            self.fail(f"Test AWS credentials not configured: {e}")

    def test_get_deployment_status_success(self):
        """Test deployment status retrieval."""
        # Integration test for deployment status
        status = self.aws_fargate.get_deployment_status('dev')
        
        self.assertIn('dev', status)
        self.assertIn('status', status['dev'])
        
        # Status could vary based on actual infrastructure state
        self.assertIsInstance(status['dev']['status'], str)

    def test_get_deployment_status_service_not_found(self):
        """Test deployment status when service is not found."""
        # Test with a non-existent environment to trigger NOT_FOUND
        status = self.aws_fargate.get_deployment_status('nonexistent')
        
        # The method only returns status for valid environments
        # For invalid environments, it returns empty dict or skips them
        self.assertIsInstance(status, dict)
        
        # 'nonexistent' is not in fargate_environments, so it won't be in the result
        # The result should be empty for non-existent environments
        self.assertEqual(status, {}, "Status should be empty for non-existent environments")

    def test_terraform_configuration_validation(self):
        """Test terraform configuration validation without applying changes."""
        # Integration test for terraform configuration validation
        # This test validates terraform configuration without creating resources
        
        # Verify terraform workspace selection works
        workspace_result = self.aws_fargate.select_workspace('test')
        self.assertTrue(workspace_result, "Should be able to select test workspace")
        
        # Verify terraform variables are properly configured
        tf_vars = self.aws_fargate._get_terraform_vars()
        self.assertIsInstance(tf_vars, dict, "Terraform variables should be a dictionary")
        self.assertIn('aws_region', tf_vars, "Should have aws_region variable")
        self.assertIn('app_environments', tf_vars, "Should have app_environments variable")
        self.assertEqual(tf_vars['app_environments'], ['dev', 'test', 'prod'], "Should have correct app environments")
        
        # Verify AWS credentials and region are properly configured
        self.assertIsNotNone(self.aws_fargate.aws_region, "AWS region should be configured")
        self.assertEqual(self.aws_fargate.account_environment, 'test', "Should be in test account environment")


if __name__ == '__main__':
    unittest.main() 