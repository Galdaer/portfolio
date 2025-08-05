#!/usr/bin/env python3
"""
Healthcare Integration Test Runner
Runs integration tests for MCP-Agent bridge without external dependencies
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import httpx

    from core.security.phi_safe_testing import HealthcareTestValidator, PHISafeTestingFramework
except ImportError as e:
    print(f"❌ Required dependency not found: {e}")
    print("Install with: pip install httpx")
    sys.exit(1)


class HealthcareIntegrationRunner:
    """Standalone integration test runner"""

    def __init__(self) -> None:
        self.framework = PHISafeTestingFramework()
        self.validator = HealthcareTestValidator()
        self.mcp_url = "http://localhost:3000/mcp"
        self.fastapi_url = "http://localhost:8000"
        self.timeout = 10.0
        self.test_results: list[dict[str, Any]] = []

    def generate_synthetic_patient(self) -> dict[str, Any]:
        """Generate synthetic patient data for testing"""
        patient = self.framework.generate_synthetic_patient()
        self.framework.validate_test_data(patient)
        return patient

    async def test_connectivity(self) -> dict[str, Any]:
        """Test basic connectivity to MCP and FastAPI servers"""
        print("🔌 Testing server connectivity...")

        results: dict[str, Any] = {
            "test_name": "connectivity",
            "mcp_server": {"available": False, "error": None},
            "fastapi_server": {"available": False, "error": None},
        }

        # Test MCP server
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:3000/health")
                if response.status_code == 200:
                    results["mcp_server"]["available"] = True
                    print("  ✅ MCP server responding")
                else:
                    results["mcp_server"]["error"] = f"HTTP {response.status_code}"
                    print(f"  ⚠️  MCP server returned {response.status_code}")
        except Exception as e:
            results["mcp_server"]["error"] = str(e)
            print(f"  ❌ MCP server unreachable: {e}")

        # Test FastAPI server
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:8000/health")
                if response.status_code == 200:
                    results["fastapi_server"]["available"] = True
                    print("  ✅ FastAPI server responding")
                else:
                    results["fastapi_server"]["error"] = f"HTTP {response.status_code}"
                    print(f"  ⚠️  FastAPI server returned {response.status_code}")
        except Exception as e:
            results["fastapi_server"]["error"] = str(e)
            print(f"  ❌ FastAPI server unreachable: {e}")

        results["success"] = (
            results["mcp_server"]["available"] and results["fastapi_server"]["available"]
        )
        return results

    async def test_mcp_tools_list(self) -> dict[str, Any]:
        """Test MCP server tools/list endpoint"""
        print("📋 Testing MCP tools list...")

        request_data = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.mcp_url, json=request_data, headers={"Content-Type": "application/json"}
                )

                if response.status_code != 200:
                    return {
                        "test_name": "mcp_tools_list",
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}",
                    }

                result = response.json()

                # Check for agent bridge tools
                tools = result.get("result", {}).get("tools", [])
                agent_tools = [
                    tool
                    for tool in tools
                    if tool.get("name")
                    in ["clinical_intake", "transcribe_audio", "research_medical_literature"]
                ]

                success = len(agent_tools) > 0
                print(
                    f"  {'✅' if success else '❌'} Found {len(agent_tools)}/3 agent bridge tools"
                )

                return {
                    "test_name": "mcp_tools_list",
                    "success": success,
                    "total_tools": len(tools),
                    "agent_tools_found": len(agent_tools),
                    "agent_tools": [tool.get("name") for tool in agent_tools],
                }

        except Exception as e:
            print(f"  ❌ Tools list test failed: {e}")
            return {"test_name": "mcp_tools_list", "success": False, "error": str(e)}

    async def test_clinical_intake_bridge(self) -> dict[str, Any]:
        """Test MCP → Clinical Intake Agent bridge"""
        print("🏥 Testing clinical intake bridge...")

        synthetic_patient = self.generate_synthetic_patient()

        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "clinical_intake",
                "arguments": {
                    "patient_data": synthetic_patient,
                    "intake_type": "new_patient",
                    "session_id": "test_session_001",
                },
            },
            "id": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.mcp_url, json=request_data, headers={"Content-Type": "application/json"}
                )

                if response.status_code != 200:
                    print(f"  ❌ HTTP {response.status_code}: {response.text}")
                    return {
                        "test_name": "clinical_intake_bridge",
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                    }

                result = response.json()

                # Basic validation
                has_result = "result" in result
                has_error = "error" in result

                # PHI safety validation
                phi_safe = True
                phi_error = None
                try:
                    self.validator.validate_phi_protection(result)
                except Exception as e:
                    phi_safe = False
                    phi_error = str(e)

                success = has_result and not has_error and phi_safe
                print(
                    f"  {'✅' if success else '❌'} Clinical intake bridge {'working' if success else 'failed'}"
                )

                if phi_error:
                    print(f"  ⚠️  PHI safety concern: {phi_error}")

                return {
                    "test_name": "clinical_intake_bridge",
                    "success": success,
                    "has_result": has_result,
                    "has_error": has_error,
                    "phi_safe": phi_safe,
                    "phi_error": phi_error,
                    "response_keys": list(result.keys()),
                }

        except Exception as e:
            print(f"  ❌ Clinical intake test failed: {e}")
            return {"test_name": "clinical_intake_bridge", "success": False, "error": str(e)}

    async def test_research_literature_bridge(self) -> dict[str, Any]:
        """Test MCP → Research Literature Agent bridge"""
        print("📚 Testing research literature bridge...")

        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "research_medical_literature",
                "arguments": {"query": "hypertension guidelines 2024", "max_results": 3},
            },
            "id": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.mcp_url, json=request_data, headers={"Content-Type": "application/json"}
                )

                if response.status_code != 200:
                    print(f"  ❌ HTTP {response.status_code}: {response.text}")
                    return {
                        "test_name": "research_literature_bridge",
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                    }

                result = response.json()

                has_result = "result" in result
                has_error = "error" in result
                has_medical_disclaimer = "medical_disclaimer" in result.get("result", {})

                success = has_result and not has_error
                print(
                    f"  {'✅' if success else '❌'} Research literature bridge {'working' if success else 'failed'}"
                )

                if has_medical_disclaimer:
                    print("  ✅ Medical disclaimer present")

                return {
                    "test_name": "research_literature_bridge",
                    "success": success,
                    "has_result": has_result,
                    "has_error": has_error,
                    "has_medical_disclaimer": has_medical_disclaimer,
                    "response_keys": list(result.keys()),
                }

        except Exception as e:
            print(f"  ❌ Research literature test failed: {e}")
            return {"test_name": "research_literature_bridge", "success": False, "error": str(e)}

    async def test_transcription_bridge(self) -> dict[str, Any]:
        """Test MCP → Transcription Agent bridge"""
        print("🎤 Testing transcription bridge...")

        synthetic_audio = self.framework.generate_synthetic_audio_data()

        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "transcribe_audio",
                "arguments": {
                    "audio_data": synthetic_audio,
                    "session_id": "test_session_001",
                    "doctor_id": "TEST_PROV_001",
                },
            },
            "id": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.mcp_url, json=request_data, headers={"Content-Type": "application/json"}
                )

                if response.status_code != 200:
                    print(f"  ❌ HTTP {response.status_code}: {response.text}")
                    return {
                        "test_name": "transcription_bridge",
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                    }

                result = response.json()

                has_result = "result" in result
                has_error = "error" in result

                success = has_result and not has_error
                print(
                    f"  {'✅' if success else '❌'} Transcription bridge {'working' if success else 'failed'}"
                )

                return {
                    "test_name": "transcription_bridge",
                    "success": success,
                    "has_result": has_result,
                    "has_error": has_error,
                    "response_keys": list(result.keys()),
                }

        except Exception as e:
            print(f"  ❌ Transcription test failed: {e}")
            return {"test_name": "transcription_bridge", "success": False, "error": str(e)}

    async def test_phi_safety_validation(self) -> dict[str, Any]:
        """Test PHI safety validation"""
        print("🔒 Testing PHI safety validation...")

        # Test with synthetic data (should pass)
        safe_patient = self.generate_synthetic_patient()
        safe_test_passed = True

        try:
            self.framework.validate_test_data(safe_patient)
            print("  ✅ Synthetic data validation passed")
        except Exception as e:
            safe_test_passed = False
            print(f"  ❌ Synthetic data validation failed: {e}")

        # Test with potentially unsafe data (should fail)
        unsafe_data = {
            "patient_id": "REAL_PATIENT_123",  # Missing TEST_ prefix
            "ssn": "123-45-6789",  # SSN pattern
            "phone": "555-123-4567",
        }

        unsafe_test_passed = False
        try:
            self.framework.validate_test_data(unsafe_data)
            print("  ❌ Unsafe data validation should have failed but passed")
        except ValueError:
            unsafe_test_passed = True
            print("  ✅ Unsafe data validation properly rejected")

        overall_success = safe_test_passed and unsafe_test_passed

        return {
            "test_name": "phi_safety_validation",
            "success": overall_success,
            "safe_data_test": safe_test_passed,
            "unsafe_data_rejection": unsafe_test_passed,
        }

    async def run_all_tests(self) -> dict[str, Any]:
        """Run all integration tests"""
        print("🏥 Healthcare AI Integration Test Suite")
        print("=" * 50)

        start_time = time.time()

        # Run tests
        test_functions = [
            self.test_connectivity,
            self.test_mcp_tools_list,
            self.test_clinical_intake_bridge,
            self.test_research_literature_bridge,
            self.test_transcription_bridge,
            self.test_phi_safety_validation,
        ]

        for test_func in test_functions:
            try:
                result = await test_func()
                self.test_results.append(result)
            except Exception as e:
                self.test_results.append(
                    {
                        "test_name": test_func.__name__.replace("test_", ""),
                        "success": False,
                        "error": f"Test execution failed: {e}",
                    }
                )

        # Calculate summary
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r.get("success", False)])
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0

        duration = time.time() - start_time

        # Print summary
        print("\n" + "=" * 50)
        print("TEST SUMMARY")
        print("=" * 50)

        for result in self.test_results:
            status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
            test_name = result.get("test_name", "unknown")
            print(f"{status} {test_name}")

            if "error" in result:
                print(f"    Error: {result['error']}")

        print(f"\nResults: {successful_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
        print(f"Duration: {duration:.2f} seconds")

        if successful_tests == total_tests:
            print("🎉 All tests passed! Healthcare AI integration is working correctly.")
            return_code = 0
        else:
            print("⚠️  Some tests failed. Check the errors above.")
            return_code = 1

        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": f"{success_rate:.1f}%",
            "duration_seconds": duration,
            "all_passed": successful_tests == total_tests,
            "return_code": return_code,
            "detailed_results": self.test_results,
        }


async def main() -> None:
    """Main test runner"""
    try:
        runner = HealthcareIntegrationRunner()
        results = await runner.run_all_tests()
        exit_code = results["return_code"]
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        exit(130)
    except Exception as e:
        print(f"\n❌ Test runner failed: {e}")
        exit(1)


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
