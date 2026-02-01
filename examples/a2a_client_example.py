#!/usr/bin/env python3
"""
Example A2A client using the official A2A Python SDK
"""

import json
import asyncio
from pathlib import Path
import sys

# Add current directory to Python path
sys.path.append(str(Path(__file__).parent))

async def test_orchestrator_client():
    """Test the orchestrator using A2A client"""
    try:
        # Try to import A2A client
        from a2a.client import A2AClient
        
        print("🤖 Testing Orchestrator with A2A Client...")
        
        # Connect to the orchestrator
        client = A2AClient("http://localhost:8002")
        
        # Get agent info
        print("📋 Getting agent information...")
        agent_info = await client.get_agent_card()
        print(f"✅ Connected to: {agent_info.name}")
        print(f"   Description: {agent_info.description}")
        print(f"   Skills: {len(agent_info.skills)} available")
        
        # Create a test bug report
        bug_report = {
            "title": "A2A Test Bug",
            "description": "Testing orchestrator via A2A client",
            "steps_to_reproduce": ["Open app", "Click button", "Error occurs"],
            "expected_behavior": "Should work normally",
            "actual_behavior": "Shows error message",
            "error_message": "NullPointerException at line 42",
            "stack_trace": "at com.example.App.main(App.java:42)",
            "environment": {"java_version": "11", "os": "Windows"},
            "severity": "high",
            "reporter": "a2a_test_client"
        }
        
        # Send analysis request
        print("\n🔍 Sending analysis request...")
        result = await client.invoke_skill(
            skill_id="orchestrator_agent-root_cause_orchestration",
            input_data={
                "bug_report_json": json.dumps(bug_report),
                "max_iterations": 3
            }
        )
        
        print("✅ Analysis request completed!")
        print(f"   Result type: {type(result)}")
        if isinstance(result, dict):
            print(f"   Result keys: {list(result.keys())}")
        
        return True
        
    except ImportError:
        print("❌ A2A client not available. Install with: pip install a2a-python")
        return False
    except Exception as e:
        print(f"❌ A2A client test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def simple_requests_test():
    """Simple test using requests library"""
    import requests
    
    print("🌐 Testing with simple HTTP requests...")
    
    try:
        # Test agent card
        response = requests.get("http://localhost:8002/.well-known/agent-card.json")
        if response.status_code == 200:
            agent_card = response.json()
            print("✅ Agent card accessible")
            print(f"   Agent: {agent_card.get('name')}")
            print(f"   Skills: {len(agent_card.get('skills', []))}")
            
            # List available skills
            print("\n📋 Available Skills:")
            for skill in agent_card.get('skills', []):
                if isinstance(skill, dict):
                    print(f"   - {skill.get('name', 'Unknown')}: {skill.get('description', 'No description')}")
                else:
                    print(f"   - {skill}")
            
            return True
        else:
            print(f"❌ Cannot access agent card: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Simple test failed: {e}")
        return False

async def main():
    """Run tests"""
    print("🧪 A2A Orchestrator Client Tests")
    print("=" * 50)
    
    # Test 1: Simple HTTP test
    print("Test 1: Basi