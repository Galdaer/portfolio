#!/usr/bin/env python3
"""
Generate secure encryption key for Intelluxe AI
Only works in development environment
"""

import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def main():
    try:
        from security.database_factory import MockConnectionFactory
        from security.encryption_manager import HealthcareEncryptionManager
        from security.environment_detector import Environment, EnvironmentDetector

        # Ensure we're in development
        EnvironmentDetector.require_environment(Environment.DEVELOPMENT)

        print("🔐 Intelluxe AI Secure Key Generator")
        print("=" * 40)
        print()

        # Create encryption manager with mock connection for key generation
        mock_factory = MockConnectionFactory()
        manager = HealthcareEncryptionManager(mock_factory)

        # Generate secure key
        print("Generating secure encryption key...")
        secure_key = manager.generate_secure_key()
        print("✅ Generated secure encryption key:")
        print()
        print(f"MASTER_ENCRYPTION_KEY={secure_key}")
        print()
        print("📋 Instructions:")
        print("1. Add this to your .env file or environment configuration")
        print("2. Keep this key secure and never commit it to version control")
        print("3. Use different keys for different environments")
        print()
        print("⚠️  WARNING: This key is for development only!")
        print("   Generate separate keys for staging and production environments")
        print()
        print("🔒 Key Properties:")
        print("   - Length: 32 bytes (256 bits)")
        print("   - Encoding: Base64 URL-safe")
        print("   - Entropy: High (cryptographically secure)")
        print("   - Algorithm: AES-256 compatible")
    except ImportError as e:
        print(f"Error: Missing dependencies - {e}", file=sys.stderr)
        print("Make sure you're running from the project root directory", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("This script only works in development environment", file=sys.stderr)
        print("Set ENVIRONMENT=development and try again", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
