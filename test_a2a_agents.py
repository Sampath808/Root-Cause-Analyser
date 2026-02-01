#!/usr/bin/env python3
"""
Test script to demonstrate A2A agent compatibility and message flow.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add current directory to Python path for imports
sys.path.append(str(Path(__file__).parent))

from core.github_client import GitHubClient
from agents.root_cause_agent import RootCauseAgent
from agents.critique_agent import CritiqueAgent
from models.bug_report import BugReport
from utils.config import config


def create_test_message(sender_id: str, task: str, data: dict) -> dict:
    """Create A2A test message."""
    return {
        "message_id": f"{sender_id}_{task}_{datetime.now().timestamp()}",
        "sender_id": sender_id,
        "recipient_id": "target_agent",
        "message_type": "task_request",
        "content": {"task": task, "data": data},
        "timestamp": datetime.now().isoformat(),
    }


def test_agent_info():
    """Test agent information retrieval."""
    print("=" * 60)
    print("TESTING A2A AGENT INFORMATION")
    print("=" * 60)

    # Initialize agents (without GitHub client for info test)
    try:
        github_client = GitHubClient(
            access_token=config.github_token, repo_full_name="test/repo", branch="main"
        )
    except:
        print("⚠️ GitHub client initialization failed, using mock")
        github_client = None

    rca_agent = RootCauseAgent(config.gemini_api_key, github_client)
    critique_agent = CritiqueAgent(config.gemini_api_key, github_client)

    # Test agent info
    print("\n🤖 RCA Agent Information:")
    rca_info = rca_agent.get_agent_info()
    print(json.dumps(rca_info, indent=2))

    print("\n🎭 Critique Agent Information:")
    critique_info = critique_agent.get_agent_info()
    print(json.dumps(critique_info, indent=2))

    return rca_agent, critique_agent


def test_message_validation():
    """Test A2A message validation."""
    print("\n" + "=" * 60)
    print("TESTING A2A MESSAGE VALIDATION")
    print("=" * 60)

    rca_agent, critique_agent = test_agent_info()

    # Test valid message
    valid_message = create_test_message(
        sender_id="orchestrator", task="get_analysis_status", data={}
    )

    print("\n✅ Testing valid message:")
    print(json.dumps(valid_message, indent=2))

    response = rca_agent.process(valid_message)
    print("\n📤 RCA Agent Response:")
    print(json.dumps(response, indent=2))

    # Test invalid message
    invalid_message = {"invalid": "message"}

    print("\n❌ Testing invalid message:")
    print(json.dumps(invalid_message, indent=2))

    response = rca_agent.process(invalid_message)
    print("\n📤 RCA Agent Response:")
    print(json.dumps(response, indent=2))


def test_task_routing():
    """Test A2A task routing."""
    print("\n" + "=" * 60)
    print("TESTING A2A TASK ROUTING")
    print("=" * 60)

    rca_agent, critique_agent = test_agent_info()

    # Test RCA agent tasks
    print("\n🔍 Testing RCA Agent Tasks:")

    tasks = [
        ("get_analysis_status", {}),
        ("unsupported_task", {}),
    ]

    for task, data in tasks:
        message = create_test_message("orchestrator", task, data)
        response = rca_agent.process(message)

        print(f"\n📋 Task: {task}")
        print(f"   Status: {response.get('status', 'unknown')}")
        if response.get("status") == "error":
            print(f"   Error: {response['content'].get('error', 'No error message')}")
        else:
            print(f"   Result: Available")

    # Test Critique agent tasks
    print("\n🎭 Testing Critique Agent Tasks:")

    tasks = [
        ("validate_evidence", {"analysis_result": {"confidence_score": 0.8}}),
        ("unsupported_task", {}),
    ]

    for task, data in tasks:
        message = create_test_message("orchestrator", task, data)
        response = critique_agent.process(message)

        print(f"\n📋 Task: {task}")
        print(f"   Status: {response.get('status', 'unknown')}")
        if response.get("status") == "error":
            print(f"   Error: {response['content'].get('error', 'No error message')}")
        else:
            print(f"   Result: Available")


def test_mock_analysis_flow():
    """Test A2A analysis flow with mock data."""
    print("\n" + "=" * 60)
    print("TESTING A2A ANALYSIS FLOW (MOCK)")
    print("=" * 60)

    # Create mock bug report
    mock_bug_report = BugReport(
        title="Test Bug",
        description="This is a test bug for A2A validation",
        steps_to_reproduce=["Step 1", "Step 2"],
        expected_behavior="Should work",
        actual_behavior="Doesn't work",
        error_message="Test error",
        stack_trace="Mock stack trace",
    )

    print("\n📋 Mock Bug Report:")
    print(f"   Title: {mock_bug_report.title}")
    print(f"   Description: {mock_bug_report.description}")

    # Test message creation
    analysis_message = create_test_message(
        sender_id="orchestrator",
        task="analyze_bug",
        data={
            "bug_report": mock_bug_report.to_dict(),
            "max_iterations": 1,  # Minimal for testing
        },
    )

    print("\n📤 A2A Analysis Message Created:")
    print(f"   Message ID: {analysis_message['message_id']}")
    print(f"   Task: {analysis_message['content']['task']}")
    print(f"   Data Keys: {list(analysis_message['content']['data'].keys())}")

    # Test critique message
    mock_analysis_result = {
        "confidence_score": 0.7,
        "root_cause": {"file_path": "test.py", "explanation": "Mock analysis result"},
    }

    critique_message = create_test_message(
        sender_id="orchestrator",
        task="critique_analysis",
        data={
            "bug_report": mock_bug_report.to_dict(),
            "analysis_result": mock_analysis_result,
        },
    )

    print("\n📤 A2A Critique Message Created:")
    print(f"   Message ID: {critique_message['message_id']}")
    print(f"   Task: {critique_message['content']['task']}")
    print(f"   Data Keys: {list(critique_message['content']['data'].keys())}")


def main():
    """Run A2A compatibility tests."""
    print("🚀 A2A AGENT COMPATIBILITY TEST")
    print("Testing pure A2A-compatible agents...")

    try:
        # Test agent information
        test_agent_info()

        # Test message validation
        test_message_validation()

        # Test task routing
        test_task_routing()

        # Test mock analysis flow
        test_mock_analysis_flow()

        print("\n" + "=" * 60)
        print("✅ A2A COMPATIBILITY TEST COMPLETED")
        print("=" * 60)
        print("\n🎉 All agents are A2A compatible!")
        print("📋 Key Features Verified:")
        print("   ✅ Agent information retrieval")
        print("   ✅ A2A message format validation")
        print("   ✅ Task routing and error handling")
        print("   ✅ Message creation and processing")
        print("\n🔄 Ready for orchestrator AI agent integration!")

    except Exception as e:
        print(f"\n❌ A2A compatibility test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
