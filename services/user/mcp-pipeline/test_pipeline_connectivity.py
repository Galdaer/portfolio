#!/usr/bin/env python3
"""
Test MCP Pipeline to Healthcare API connectivity.

This tests the actual connectivity between the MCP Pipeline and Healthcare API
to identify where the "All connection attempts failed" error is coming from.
"""

import asyncio

import aiohttp


async def test_connectivity():
    """Test connectivity from MCP Pipeline perspective"""
    print("🔍 Testing MCP Pipeline → Healthcare API connectivity")
    print("-" * 55)

    # This should match what the MCP Pipeline is doing
    base_url = "http://healthcare-api:8000"

    try:
        async with aiohttp.ClientSession() as session:
            # Test 1: Health check
            print("1️⃣ Testing health endpoint...")
            try:
                async with session.get(f"{base_url}/health") as response:
                    print(f"   ✅ Health check: {response.status}")
                    if response.status == 200:
                        health_data = await response.json()
                        print(f"   📊 Health data: {health_data}")
            except Exception as e:
                print(f"   ❌ Health check failed: {e}")

            # Test 2: Process endpoint
            print("\n2️⃣ Testing /process endpoint...")
            try:
                test_data = {
                    "message": "Hello, test message",
                    "user_id": "test_user",
                    "session_id": "test_session",
                }

                print(f"   📤 Sending: {test_data}")

                async with session.post(f"{base_url}/process", json=test_data) as response:
                    print(f"   📊 Status: {response.status}")

                    if response.status == 200:
                        result = await response.json()
                        print(f"   ✅ Success: {result}")
                    else:
                        error_text = await response.text()
                        print(f"   ❌ Error: {error_text}")

            except Exception as e:
                print(f"   ❌ Process endpoint failed: {e}")
                import traceback

                traceback.print_exc()

    except Exception as e:
        print(f"❌ Overall connection failed: {e}")
        import traceback

        traceback.print_exc()


def main():
    """Run connectivity test"""
    print("🏥 MCP Pipeline Connectivity Test")
    print("=" * 35)

    try:
        asyncio.run(test_connectivity())
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test crashed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
