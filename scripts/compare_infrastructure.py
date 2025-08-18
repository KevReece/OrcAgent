#!/usr/bin/env python3
"""
Infrastructure Comparison Script
Compares infrastructure inventories to show what changed during setup/teardown operations.
"""

import json
import sys
from typing import Dict, List, Any, Set
from datetime import datetime

def load_inventory(filename: str) -> Dict[str, Any]:
    """Load inventory from JSON file."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File {filename} not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filename}: {e}")
        sys.exit(1)

def extract_resource_ids(resources: List[Dict[str, Any]], id_key: str) -> Set[str]:
    """Extract resource IDs from a list of resources."""
    return {resource[id_key] for resource in resources if id_key in resource}

def compare_account_resources(before: Dict[str, Any], after: Dict[str, Any], account_type: str) -> None:
    """Compare resources for a specific account."""
    print(f"\n{'='*60}")
    print(f"CHANGES IN {account_type.upper()} ACCOUNT")
    print(f"{'='*60}")
    
    if 'error' in before or 'error' in after:
        print(f"❌ Error in inventory data for {account_type} account")
        return
    
    # Define resource types and their ID keys
    resource_types = {
        'ecr_repositories': 'name',
        'ecs_clusters': 'name', 
        'ecs_services': 'name',
        'iam_roles': 'name',
        'vpcs': 'id',
        'cloudwatch_logs': 'name',
        'load_balancers': 'name'
    }
    
    total_changes = 0
    
    for resource_type, id_key in resource_types.items():
        before_ids = extract_resource_ids(before.get(resource_type, []), id_key)
        after_ids = extract_resource_ids(after.get(resource_type, []), id_key)
        
        added = after_ids - before_ids
        removed = before_ids - after_ids
        unchanged = before_ids & after_ids
        
        if added or removed:
            total_changes += len(added) + len(removed)
            print(f"\n📋 {resource_type.replace('_', ' ').title()}:")
            
            if added:
                print(f"  ✅ Added ({len(added)}):")
                for resource_id in sorted(added):
                    print(f"    + {resource_id}")
            
            if removed:
                print(f"  ❌ Removed ({len(removed)}):")
                for resource_id in sorted(removed):
                    print(f"    - {resource_id}")
            
            if unchanged:
                print(f"  ⚪ Unchanged ({len(unchanged)})")
        else:
            print(f"⚪ {resource_type.replace('_', ' ').title()}: No changes ({len(unchanged)} resources)")
    
    if total_changes == 0:
        print(f"\n✅ No changes detected in {account_type.upper()} account")
    else:
        print(f"\n📊 Total changes in {account_type.upper()} account: {total_changes}")

def main():
    """Main function to compare two infrastructure inventories."""
    if len(sys.argv) != 3:
        print("Usage: python compare_infrastructure.py <before_inventory.json> <after_inventory.json>")
        sys.exit(1)
    
    before_file = sys.argv[1]
    after_file = sys.argv[2]
    
    print("🔍 Infrastructure Comparison Report")
    print("=" * 60)
    
    before_inventory = load_inventory(before_file)
    after_inventory = load_inventory(after_file)
    
    print(f"📅 Before: {before_inventory.get('inventory_timestamp', 'Unknown')}")
    print(f"📅 After:  {after_inventory.get('inventory_timestamp', 'Unknown')}")
    
    # Compare each account
    for account_type in ['test', 'sandbox']:
        before_account = before_inventory.get('accounts', {}).get(account_type, {})
        after_account = after_inventory.get('accounts', {}).get(account_type, {})
        
        if before_account and after_account:
            compare_account_resources(before_account, after_account, account_type)
    
    print(f"\n{'='*60}")
    print("✅ Comparison complete!")

if __name__ == '__main__':
    main() 