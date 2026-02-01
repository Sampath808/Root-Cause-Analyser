#!/usr/bin/env python3
"""
Simple A2A test for the orchestrator
"""

import requests
import json


def test_agent_card():
    """Test the agent card endpoint"""
    print("🔍 Testing Agent Card...")
    try:
        response = requests.get("http://localhost:8002/.well-known/agent-card.json")
        if response.status_code == 200:
            card = response.json()
            print("✅ Agent Card Retrieved!")
            print(f"   Name: {card.get('name')}")
            print(f"   Version: {card.get('version')}")
            print(f"   Description: {card.get('description', '')[:100]}...")

            skills = card.get("skills", [])
            print(f"\n📋 Available Skills ({len(skills)}):")
            for i, skill in enumerate(skills, 1):
                if isinstance(skill, dict):
                    print(f"   {i}. {skill.get('name', 'Unknown')}")
                    print(f"      ID: {skill.get('id', 'No ID')}")
                    print(
                        f"      Description: {skill.get('description', 'No description')}"
                    )
                else:
                    print(f"   {i}. {skill}")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("🧪 Simple A2A Orchestrator Test")
    print("=" * 40)
    print("Server should be running on http://localhost:8002")
    print("=" * 40)

    if test_agent_card():
        print("\n🎉 Success! Your A2A orchestrator is working!")
        print("\n📋 What you can do now:")
        print("1. Visit http://localhost:8002/.well-known/agent-card.json in browser")
        print("2. Use A2A clients to communicate with the orchestrator")
        print("3. Build multi-agent systems using this orchestrator")
        print("4. Integrate with other A2A-compatible agents")
    else:
        print("\n⚠️  Test failed. Check if server is running.")


if __name__ == "__main__":
    main()
