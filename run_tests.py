#!/usr/bin/env python3
"""Test runner for IBKR integration tests."""
import asyncio
import sys
import argparse


async def run_unit_tests():
    """Run unit tests."""
    import pytest
    return pytest.main(["-v", "tests/brokers/test_ibkr_client.py", "-m", "not integration"])


async def run_integration_tests():
    """Run integration tests (requires TWS/IB Gateway)."""
    import pytest
    return pytest.main(["-v", "tests/brokers/test_ibkr_integration.py", "-m", "integration"])


async def run_error_tests():
    """Run error handling tests."""
    import pytest
    return pytest.main(["-v", "tests/brokers/test_ibkr_errors.py"])


async def run_all_tests():
    """Run all tests."""
    import pytest
    return pytest.main(["-v", "tests/"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run IBKR tests")
    parser.add_argument(
        "--type",
        choices=["unit", "integration", "error", "all"],
        default="unit",
        help="Type of tests to run"
    )
    
    args = parser.parse_args()
    
    if args.type == "unit":
        result = asyncio.run(run_unit_tests())
    elif args.type == "integration":
        result = asyncio.run(run_integration_tests())
    elif args.type == "error":
        result = asyncio.run(run_error_tests())
    else:
        result = asyncio.run(run_all_tests())
    
    sys.exit(result)
