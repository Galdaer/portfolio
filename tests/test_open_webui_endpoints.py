#!/usr/bin/env python3
"""
Test Open WebUI compatible endpoints in healthcare-api
"""

import asyncio

import aiohttp


class TestOpenWebUIEndpoints:
    """Test suite for Open WebUI compatible endpoints"""

    def __init__(self):
        self.base_url = "http://localhost:8000"

    async def test_health_endpoint(self):
        """Test basic health endpoint"""
        print("🔍 Testing /health endpoint...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"   ✅ Health check passed: {data}")
                        return True
                    print(f"   ❌ Health check failed: {response.status}")
                    return False
        except Exception as e:
            print(f"   ❌ Health check error: {e}")
            return False

    async def test_pipelines_endpoint(self):
        """Test /pipelines endpoint for Open WebUI"""
        print("🔍 Testing /pipelines endpoint...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/pipelines") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"   ✅ Pipelines endpoint: {data}")
                        return True
                    text = await response.text()
                    print(f"   ❌ Pipelines endpoint failed: {response.status} - {text}")
                    return False
        except Exception as e:
            print(f"   ❌ Pipelines endpoint error: {e}")
            return False

    async def test_models_endpoint(self):
        """Test /models endpoint for Open WebUI"""
        print("🔍 Testing /models endpoint...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/models") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"   ✅ Models endpoint: {data}")
                        return True
                    text = await response.text()
                    print(f"   ❌ Models endpoint failed: {response.status} - {text}")
                    return False
        except Exception as e:
            print(f"   ❌ Models endpoint error: {e}")
            return False

    async def test_tools_endpoint(self):
        """Test /tools endpoint"""
        print("🔍 Testing /tools endpoint...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/tools") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"   ✅ Tools endpoint: {data}")
                        return True
                    text = await response.text()
                    print(f"   ❌ Tools endpoint failed: {response.status} - {text}")
                    return False
        except Exception as e:
            print(f"   ❌ Tools endpoint error: {e}")
            return False

    async def test_chat_completions_endpoint(self):
        """Test /v1/chat/completions endpoint - the key missing piece"""
        print("🔍 Testing /v1/chat/completions endpoint...")
        try:
            test_request = {
                "model": "healthcare",
                "messages": [{"role": "user", "content": "What are the symptoms of diabetes?"}],
                "temperature": 0.7,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=test_request,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print("   ✅ Chat completions endpoint working!")
                        print(
                            f"   📋 Response preview: {data.get('choices', [{}])[0].get('message', {}).get('content', '')[:200]}...",
                        )
                        return True
                    text = await response.text()
                    print(f"   ❌ Chat completions failed: {response.status} - {text}")
                    return False
        except Exception as e:
            print(f"   ❌ Chat completions error: {e}")
            return False

    async def test_alternative_chat_completions(self):
        """Test /chat/completions endpoint (without /v1 prefix)"""
        print("🔍 Testing /chat/completions endpoint (no v1 prefix)...")
        try:
            test_request = {
                "model": "healthcare",
                "messages": [{"role": "user", "content": "Test medical query"}],
                "temperature": 0.7,
            }

            async with aiohttp.ClientSession() as session, session.post(
                f"{self.base_url}/chat/completions",
                json=test_request,
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status == 200:
                    await response.json()  # Consume response
                    print("   ✅ Alternative chat completions endpoint working!")
                    return True
                text = await response.text()
                print(
                    f"   ❌ Alternative chat completions failed: {response.status} - {text}",
                )
                return False
        except Exception as e:
            print(f"   ❌ Alternative chat completions error: {e}")
            return False

    async def run_all_tests(self):
        """Run all endpoint tests"""
        print("🏥 Testing Open WebUI Compatible Endpoints")
        print("=" * 50)

        tests = [
            ("Health Check", self.test_health_endpoint),
            ("Pipelines Endpoint", self.test_pipelines_endpoint),
            ("Models Endpoint", self.test_models_endpoint),
            ("Tools Endpoint", self.test_tools_endpoint),
            ("Chat Completions (/v1)", self.test_chat_completions_endpoint),
            ("Chat Completions (no /v1)", self.test_alternative_chat_completions),
        ]

        results = {}
        for test_name, test_func in tests:
            print(f"\n🧪 {test_name}")
            try:
                results[test_name] = await test_func()
            except Exception as e:
                print(f"   💥 Test crashed: {e}")
                results[test_name] = False

        print("\n📊 Test Results Summary:")
        print("-" * 30)
        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} {test_name}")

        total_tests = len(results)
        passed_tests = sum(results.values())
        print(f"\n🎯 Overall: {passed_tests}/{total_tests} tests passed")

        if passed_tests == total_tests:
            print("🎉 All Open WebUI endpoints are working!")
        else:
            print("⚠️  Some endpoints need attention")

        return results


async def main():
    """Run the Open WebUI endpoint tests"""
    tester = TestOpenWebUIEndpoints()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
