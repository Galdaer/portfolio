#!/usr/bin/env python3
"""
Test script for Medical Transcription Action
Tests user ID detection and basic functionality for justin and jeff users.
"""

import asyncio
import sys

# Import the action
try:
    from medical_transcription_action import Action
except ImportError:
    print("❌ Failed to import medical_transcription_action.py")
    sys.exit(1)


class MockEventEmitter:
    """Mock event emitter for testing"""

    def __init__(self):
        self.events = []

    async def __call__(self, event):
        self.events.append(event)
        print(f"📡 Event: {event['type']} - {event.get('data', {}).get('message', '')}")

        if event.get("data", {}).get("transcription_chunk"):
            print(f"   📝 Transcription: {event['data']['transcription_chunk']}")


async def test_user_detection():
    """Test user ID detection with different scenarios"""

    print("🧪 Testing User ID Detection")
    print("=" * 50)

    action = Action()

    # Test scenarios
    test_cases = [
        {
            "name": "Justin as dict user",
            "__user__": {"id": "justin", "username": "justin", "email": "justin@example.com"},
            "body": {},
            "expected": "justin",
        },
        {
            "name": "Jeff as dict user",
            "__user__": {"id": "jeff", "username": "jeff", "email": "jeff@example.com"},
            "body": {},
            "expected": "jeff",
        },
        {
            "name": "User in body",
            "__user__": None,
            "body": {"user": {"username": "justin", "id": "123"}},
            "expected": "justin",
        },
        {
            "name": "No user info (should default to justin)",
            "__user__": None,
            "body": {},
            "expected": "justin",  # Developer default
        },
        {
            "name": "Unknown user (should default to justin)",
            "__user__": {"id": "unknown"},
            "body": {},
            "expected": "justin",
        },
    ]

    for test_case in test_cases:
        print(f"\n🔍 Test: {test_case['name']}")

        # Extract user ID
        user_id = action.extract_user_id(test_case["__user__"], test_case["body"])

        # Handle developer mode
        if action.valves.DEVELOPER_MODE:
            user_id = action.handle_developer_mode(user_id)

        # Check result
        if user_id == test_case["expected"]:
            print(f"✅ PASS: Detected user '{user_id}'")
        else:
            print(f"❌ FAIL: Expected '{test_case['expected']}', got '{user_id}'")


async def test_mock_transcription():
    """Test mock transcription functionality"""

    print("\n🧪 Testing Mock Transcription")
    print("=" * 50)

    action = Action()
    action.valves.MOCK_TRANSCRIPTION = True  # Enable mock mode

    mock_emitter = MockEventEmitter()

    # Test with Justin
    print("\n👨‍⚕️ Testing with Justin user")

    body = {"user": {"username": "justin"}}
    __user__ = {"id": "justin", "username": "justin"}

    result = await action.action(body, __user__, mock_emitter)

    if result["success"]:
        print("✅ PASS: Mock transcription completed successfully")
        print(f"   📋 Session ID: {result['data']['session_id']}")
        print(f"   📝 Transcription Length: {len(result['data']['transcription'])} chars")
        print(f"   📄 SOAP Note Generated: {'Yes' if result['data']['soap_note'] else 'No'}")
    else:
        print(f"❌ FAIL: {result['message']}")

    # Test with Jeff
    print("\n👨‍⚕️ Testing with Jeff user")

    body = {"user": {"username": "jeff"}}
    __user__ = {"id": "jeff", "username": "jeff"}

    result = await action.action(body, __user__, mock_emitter)

    if result["success"]:
        print("✅ PASS: Mock transcription completed successfully")
        print(f"   📋 Session ID: {result['data']['session_id']}")
        print(f"   👤 User ID: {result['data']['user_id']}")
    else:
        print(f"❌ FAIL: {result['message']}")


async def test_configuration():
    """Test action configuration and metadata"""

    print("\n🧪 Testing Configuration")
    print("=" * 50)

    action = Action()

    # Check basic properties
    print(f"📍 Action ID: {action.id}")
    print(f"🏷️  Action Name: {action.name}")
    print(f"📝 Description: {action.description}")
    print(f"🧑‍💻 Developer Mode: {action.valves.DEVELOPER_MODE}")
    print(f"👥 Developer Users: {action.valves.DEVELOPER_USERS}")
    print(f"🔗 Healthcare API: {action.valves.HEALTHCARE_API_URL}")

    # Test metadata
    metadata = action.get_action_metadata()
    print("\n📊 Metadata:")
    for key, value in metadata.items():
        print(f"   {key}: {value}")


async def test_websocket_connection():
    """Test WebSocket connection (will fail if healthcare-api not running)"""

    print("\n🧪 Testing WebSocket Connection")
    print("=" * 50)

    action = Action()
    action.valves.MOCK_TRANSCRIPTION = False  # Try real connection

    mock_emitter = MockEventEmitter()

    body = {"user": {"username": "justin"}}
    __user__ = {"id": "justin", "username": "justin"}

    print("🔗 Attempting connection to healthcare-api...")
    print(f"   URL: {action.valves.HEALTHCARE_API_URL}/ws/transcription/dr_justin")

    result = await action.action(body, __user__, mock_emitter)

    if result["success"]:
        print("✅ PASS: Real WebSocket connection successful!")
        print(f"   📋 Session ID: {result['data']['session_id']}")
    else:
        print("⚠️  WebSocket connection failed (expected if healthcare-api not running)")
        print(f"   Error: {result['message']}")
        print("   This is normal if the healthcare-api server is not started")


async def main():
    """Run all tests"""

    print("🏥 Medical Transcription Action Test Suite")
    print("=" * 80)

    try:
        # Run tests
        await test_configuration()
        await test_user_detection()
        await test_mock_transcription()
        await test_websocket_connection()

        print("\n" + "=" * 80)
        print("🎉 Test Suite Complete!")
        print("\n📋 Next Steps:")
        print("1. Install this action in Open WebUI")
        print("2. Start the healthcare-api server: python main.py")
        print("3. Test with real users: justin and jeff")
        print("4. Click the '🎙️ Medical Transcription' button in chat")

    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
