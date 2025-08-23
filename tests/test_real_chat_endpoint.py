#!/usr/bin/env python3
"""
Test the ACTUAL /chat endpoint that Open WebUI uses with LangChain
"""

import asyncio
import json
import sys
import httpx


async def test_chat_endpoint():
    """Test the /chat endpoint that actually gets used"""
    print("🧪 Testing REAL /chat Endpoint (LangChain Integration)")
    print("=" * 60)

    base_url = "http://localhost:8000"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print("1. Testing health endpoint...")
            health_response = await client.get(f"{base_url}/health")
            print(f"   Status: {health_response.status_code}")
            if health_response.status_code == 200:
                health_data = health_response.json()
                print(f"   Agents: {health_data.get('agents', [])}")

            print("\n2. Testing /chat endpoint with medical query...")

            # This is the actual ChatRequest format used by LangChain
            chat_request = {
                "message": "Find recent research on cardiovascular health",
                "model": "healthcare",  # This might be required
            }

            print(f"   Request: {json.dumps(chat_request, indent=2)}")

            response = await client.post(
                f"{base_url}/chat", json=chat_request, headers={"Content-Type": "application/json"}
            )

            print(f"   Response status: {response.status_code}")
            print(f"   Response headers: {dict(response.headers)}")

            if response.status_code == 200:
                result = response.json()
                print("   ✅ Request successful!")

                # Print the structure to understand what we're getting
                print("\n   📊 Response structure:")
                print(f"   - Type: {type(result)}")
                print(
                    f"   - Keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}"
                )

                # Look for the actual content
                if isinstance(result, dict):
                    if "choices" in result:
                        # OpenAI format
                        content = result["choices"][0]["message"]["content"]
                        print("\n   📝 OpenAI Format Content (first 500 chars):")
                        print(f"   {content[:500]}...")

                        # Check if it's formatted or raw JSON
                        if content.startswith("{") or content.startswith("["):
                            print("   ❌ PROBLEM: Content is raw JSON!")
                            try:
                                parsed = json.loads(content)
                                print(
                                    f"   🔍 JSON structure: {list(parsed.keys()) if isinstance(parsed, dict) else type(parsed)}"
                                )
                            except json.JSONDecodeError:
                                print("   🔍 Not valid JSON, but starts with bracket")
                        else:
                            print("   ✅ Content appears to be formatted!")

                    elif "response" in result:
                        # Direct response format
                        content = result["response"]
                        print("\n   📝 Direct Response Content:")
                        print(f"   {content}")

                        print("\n   📝 Full result:")
                        print(f"   {json.dumps(result, indent=2)}")

                    else:
                        print("\n   📝 Full Response (first 1000 chars):")
                        print(f"   {str(result)[:1000]}...")

            else:
                print(f"   ❌ Request failed: {response.status_code}")
                print(f"   Error: {response.text}")

        except Exception as e:
            print(f"   💥 Error: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_chat_endpoint())
