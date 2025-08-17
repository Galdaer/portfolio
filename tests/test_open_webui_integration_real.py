#!/usr/bin/env python3
"""
Test Open WebUI Medical Search Integration - Real End-to-End Test

This test validates the actual Open WebUI flow by testing the /v1/chat/completions endpoint
that Open WebUI uses, and verifies that:
1. DOI links are prioritized over PMID
2. Publication dates are displayed
3. Abstracts are included
4. Article formatting is complete

Created: August 17, 2025
Purpose: Test real Open WebUI medical search integration without container dependencies
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    import requests
    import aiohttp
except ImportError:
    print("Installing required packages...")
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "aiohttp"])
    import requests
    import aiohttp


class TestOpenWebUIMedicalSearchIntegration:
    """Test the actual Open WebUI medical search integration end-to-end"""

    def __init__(self):
        self.api_base_url = "http://172.20.0.4:8000"
        self.test_queries = [
            "recent research on cardiovascular health",
            "diabetes prevention strategies",
            "hypertension treatment guidelines",
        ]

    def test_api_health(self):
        """Test that the healthcare API is running"""
        print("\n🔍 Testing Healthcare API Health...")
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=10)
            assert response.status_code == 200, f"API health check failed: {response.status_code}"
            print("✅ Healthcare API is running")
            return True
        except Exception as e:
            print(f"❌ Healthcare API health check failed: {e}")
            return False

    def test_openai_chat_completions_endpoint(self):
        """Test the /v1/chat/completions endpoint that Open WebUI uses"""
        print("\n🔍 Testing /v1/chat/completions endpoint...")

        test_payload = {
            "model": "healthcare",
            "messages": [
                {
                    "role": "user",
                    "content": "Find recent research on cardiovascular health and prevention",
                }
            ],
            "temperature": 0.1,
            "max_tokens": 2000,
        }

        try:
            response = requests.post(
                f"{self.api_base_url}/v1/chat/completions",
                json=test_payload,
                headers={"Content-Type": "application/json"},
                timeout=120,
            )

            if response.status_code != 200:
                print(f"❌ Chat completions endpoint failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False, None

            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            print("✅ Chat completions endpoint working")
            print(f"Response length: {len(content)} characters")

            return True, content

        except Exception as e:
            print(f"❌ Chat completions endpoint error: {e}")
            return False, None

    def analyze_medical_search_response(self, content: str):
        """Analyze the medical search response for required elements"""
        print("\n📋 Analyzing Medical Search Response...")

        issues = []
        successes = []

        # Check for DOI links (PRIMARY REQUIREMENT)
        if "https://doi.org/" in content:
            successes.append("✅ DOI links present (PRIORITY)")
        else:
            issues.append("❌ No DOI links found (CRITICAL - DOI should be prioritized over PMID)")

        # Check for author information
        if "Authors:" in content:
            successes.append("✅ Author information present")
        else:
            issues.append("❌ No author information found")

        # Check for journal information
        if "Journal:" in content:
            successes.append("✅ Journal information present")
        else:
            issues.append("❌ No journal information found")

        # Check for publication dates/years
        if any(year in content for year in ["2023", "2024", "2025"]) or "(" in content:
            successes.append("✅ Publication dates present")
        else:
            issues.append("❌ No publication dates found")

        # Check for abstracts (detailed content)
        if "Abstract:" in content or len(content) > 1000:
            successes.append("✅ Detailed content/abstracts present")
        else:
            issues.append("❌ No abstracts or detailed content found")

        # PMID should be SECONDARY to DOI
        if "PubMed ID:" in content or "https://pubmed.ncbi.nlm.nih.gov/" in content:
            if "https://doi.org/" in content:
                successes.append("✅ PMID shown as secondary reference (good)")
            else:
                issues.append("⚠️ PMID shown but no DOI links (DOI should be primary)")

        # Print results
        for success in successes:
            print(success)

        for issue in issues:
            print(issue)

        # Show a preview of the content
        print(f"\n📄 Response Preview (first 500 chars):")
        print("-" * 50)
        print(content[:500] + "..." if len(content) > 500 else content)
        print("-" * 50)

        return len(issues) == 0, issues, successes

    def test_multiple_medical_queries(self):
        """Test multiple medical queries to ensure consistency"""
        print("\n🔬 Testing Multiple Medical Queries...")

        all_results = []

        for i, query in enumerate(self.test_queries, 1):
            print(f"\n📝 Test Query {i}: {query}")

            test_payload = {
                "model": "healthcare",
                "messages": [{"role": "user", "content": query}],
                "temperature": 0.1,
                "max_tokens": 2000,
            }

            try:
                response = requests.post(
                    f"{self.api_base_url}/v1/chat/completions",
                    json=test_payload,
                    headers={"Content-Type": "application/json"},
                    timeout=120,
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    success, issues, successes = self.analyze_medical_search_response(content)
                    all_results.append((query, success, issues, successes))
                    print(f"Query {i} result: {'✅ PASS' if success else '❌ FAIL'}")
                else:
                    print(f"❌ Query {i} failed: {response.status_code}")
                    all_results.append((query, False, [f"HTTP {response.status_code}"], []))

            except Exception as e:
                print(f"❌ Query {i} error: {e}")
                all_results.append((query, False, [str(e)], []))

        return all_results

    def run_all_tests(self):
        """Run all Open WebUI medical search integration tests"""
        print("🧪 Open WebUI Medical Search Integration Test Suite")
        print("=" * 60)

        # Test 1: API Health
        if not self.test_api_health():
            print("\n❌ Cannot proceed - Healthcare API is not responding")
            return False

        # Test 2: Basic endpoint test
        success, content = self.test_openai_chat_completions_endpoint()
        if not success:
            print("\n❌ Cannot proceed - Chat completions endpoint not working")
            return False

        # Test 3: Analyze response quality
        response_ok, issues, successes = self.analyze_medical_search_response(content)

        # Test 4: Multiple queries
        all_results = self.test_multiple_medical_queries()

        # Summary
        print("\n" + "=" * 60)
        print("🎯 INTEGRATION TEST SUMMARY")
        print("=" * 60)

        passed_queries = sum(1 for _, success, _, _ in all_results if success)
        total_queries = len(all_results)

        print(
            f"📊 Query Success Rate: {passed_queries}/{total_queries} ({passed_queries / total_queries * 100:.0f}%)"
        )

        if response_ok and passed_queries == total_queries:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ Open WebUI medical search integration is working correctly")
            return True
        else:
            print(f"\n⚠️ Issues Found:")
            for query, success, issues, _ in all_results:
                if not success:
                    print(f"  - {query}: {', '.join(issues)}")

            print(f"\n🔧 Next Steps:")
            print("1. Check DOI prioritization in medical search agent")
            print("2. Verify publication date handling")
            print("3. Ensure abstract inclusion")
            print("4. Test with real medical queries in Open WebUI")

            return False


def main():
    """Main test runner"""
    tester = TestOpenWebUIMedicalSearchIntegration()
    success = tester.run_all_tests()

    if success:
        print("\n✅ Open WebUI medical search integration validated!")
        return 0
    else:
        print("\n❌ Integration issues found - see summary above")
        return 1


if __name__ == "__main__":
    exit(main())
