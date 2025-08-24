#!/usr/bin/env python3
"""
Test runner for temporal-cli-mcp.
Manages test execution, dependency checking, and reporting.
Adapted from kubectl-mcp-server test patterns.
"""

import os
import sys
import argparse
import subprocess
import logging
import time
from pathlib import Path
from typing import List, Optional, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TemporalMCPTestRunner:
    """Test runner for temporal-cli-mcp tests."""
    
    def __init__(self, 
                 test_env: str = "staging",
                 mock_mode: bool = False,
                 verbose: bool = False):
        """
        Initialize the test runner.
        
        Args:
            test_env: Temporal environment to test against
            mock_mode: Run in mock mode (no actual Temporal CLI calls)
            verbose: Enable verbose logging
        """
        self.test_env = test_env
        self.mock_mode = mock_mode
        self.verbose = verbose
        
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Set environment variables for tests
        os.environ["TEMPORAL_TEST_ENV"] = test_env
        if mock_mode:
            os.environ["TEMPORAL_MCP_TEST_MOCK_MODE"] = "1"
        
        self.tests_dir = Path(__file__).parent
        self.project_root = self.tests_dir.parent
        
        logger.info(f"Temporal MCP Test Runner initialized")
        logger.info(f"Test environment: {test_env}")
        logger.info(f"Mock mode: {mock_mode}")
        logger.info(f"Tests directory: {self.tests_dir}")
    
    def check_dependencies(self) -> bool:
        """
        Check if all required dependencies are available.
        
        Returns:
            True if all dependencies are available
        """
        logger.info("Checking test dependencies...")
        
        dependencies = {
            "python": ["python", "--version"],
            "pytest": ["python", "-m", "pytest", "--version"]
        }
        
        if not self.mock_mode:
            dependencies["temporal"] = ["temporal", "--version"]
        
        missing_deps = []
        
        for dep_name, cmd in dependencies.items():
            try:
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                if result.returncode == 0:
                    logger.info(f"✓ {dep_name}: Available")
                    if self.verbose:
                        logger.debug(f"  {result.stdout.strip()}")
                else:
                    logger.error(f"✗ {dep_name}: Failed to run")
                    missing_deps.append(dep_name)
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
                logger.error(f"✗ {dep_name}: Not available ({e})")
                missing_deps.append(dep_name)
        
        if missing_deps:
            logger.error(f"Missing dependencies: {missing_deps}")
            return False
        
        logger.info("✓ All dependencies are available")
        return True
    
    def check_temporal_environment(self) -> bool:
        """
        Check if Temporal environment is accessible.
        
        Returns:
            True if environment is accessible
        """
        if self.mock_mode:
            logger.info("Skipping Temporal environment check (mock mode)")
            return True
        
        logger.info(f"Checking Temporal environment: {self.test_env}")
        
        try:
            result = subprocess.run(
                ["temporal", "--env", self.test_env, "workflow", "list", "--limit", "1"],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                logger.info(f"✓ Temporal environment '{self.test_env}' is accessible")
                return True
            else:
                logger.error(f"✗ Temporal environment '{self.test_env}' failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"✗ Timeout connecting to Temporal environment '{self.test_env}'")
            return False
        except Exception as e:
            logger.error(f"✗ Error checking Temporal environment: {e}")
            return False
    
    def install_test_dependencies(self) -> bool:
        """
        Install required test dependencies.
        
        Returns:
            True if installation successful
        """
        logger.info("Installing test dependencies...")
        
        try:
            # Install pytest if not available
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "pytest", "pytest-asyncio"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info("✓ Test dependencies installed successfully")
                return True
            else:
                logger.error(f"✗ Failed to install dependencies: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"✗ Error installing dependencies: {e}")
            return False
    
    def discover_test_modules(self) -> List[Path]:
        """
        Discover test modules in the tests directory.
        
        Returns:
            List of test module paths
        """
        test_files = []
        
        for test_file in self.tests_dir.glob("test_*.py"):
            if test_file.name != "test_utils.py":  # Exclude utilities
                test_files.append(test_file)
        
        logger.info(f"Discovered {len(test_files)} test modules:")
        for test_file in test_files:
            logger.info(f"  - {test_file.name}")
        
        return test_files
    
    def run_tests(self, 
                  test_modules: Optional[List[str]] = None,
                  generate_report: bool = False,
                  fail_fast: bool = False) -> bool:
        """
        Run the tests.
        
        Args:
            test_modules: Specific test modules to run (default: all)
            generate_report: Generate HTML test report
            fail_fast: Stop on first failure
            
        Returns:
            True if all tests passed
        """
        logger.info("Starting test execution...")
        
        if not self.check_dependencies():
            logger.error("Dependency check failed")
            return False
        
        if not self.check_temporal_environment():
            logger.error("Temporal environment check failed")
            return False
        
        # Build pytest command
        cmd = [sys.executable, "-m", "pytest"]
        
        if self.verbose:
            cmd.append("-v")
        
        if fail_fast:
            cmd.append("-x")
        
        # Add specific test modules or discover all
        if test_modules:
            for module in test_modules:
                if not module.endswith(".py"):
                    module += ".py"
                cmd.append(str(self.tests_dir / module))
        else:
            test_files = self.discover_test_modules()
            if not test_files:
                logger.warning("No test modules found")
                return True
            cmd.extend([str(f) for f in test_files])
        
        # Add report generation
        if generate_report:
            report_dir = self.project_root / "test_reports"
            report_dir.mkdir(exist_ok=True)
            cmd.extend([
                "--html", str(report_dir / "report.html"),
                "--self-contained-html"
            ])
        
        # Set working directory to project root
        original_cwd = os.getcwd()
        
        try:
            os.chdir(self.project_root)
            
            logger.info(f"Running command: {' '.join(cmd)}")
            start_time = time.time()
            
            result = subprocess.run(cmd, text=True)
            
            duration = time.time() - start_time
            logger.info(f"Test execution completed in {duration:.2f}s")
            
            if result.returncode == 0:
                logger.info("✓ All tests passed!")
                return True
            else:
                logger.error(f"✗ Tests failed with exit code {result.returncode}")
                return False
                
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return False
        finally:
            os.chdir(original_cwd)
    
    def run_single_test(self, test_module: str, test_function: Optional[str] = None) -> bool:
        """
        Run a single test module or function.
        
        Args:
            test_module: Test module name
            test_function: Specific test function (optional)
            
        Returns:
            True if test passed
        """
        test_target = test_module
        if test_function:
            test_target += f"::{test_function}"
        
        logger.info(f"Running single test: {test_target}")
        return self.run_tests([test_target])


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="Test runner for temporal-cli-mcp",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                                    # Run all tests
  python run_tests.py --env prod                         # Run against prod environment
  python run_tests.py --mock                             # Run in mock mode
  python run_tests.py --module test_core                 # Run specific module
  python run_tests.py --report                           # Generate HTML report
  python run_tests.py --install-deps                     # Install test dependencies
        """
    )
    
    parser.add_argument(
        "--env",
        default="staging",
        help="Temporal environment to test against (default: staging)"
    )
    
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock mode (no actual Temporal CLI calls)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--module",
        help="Run specific test module"
    )
    
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate HTML test report"
    )
    
    parser.add_argument(
        "--fail-fast", "-x",
        action="store_true",
        help="Stop on first failure"
    )
    
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install test dependencies and exit"
    )
    
    args = parser.parse_args()
    
    # Handle dependency installation
    if args.install_deps:
        runner = TemporalMCPTestRunner()
        success = runner.install_test_dependencies()
        sys.exit(0 if success else 1)
    
    # Initialize test runner
    runner = TemporalMCPTestRunner(
        test_env=args.env,
        mock_mode=args.mock,
        verbose=args.verbose
    )
    
    # Run tests
    test_modules = [args.module] if args.module else None
    success = runner.run_tests(
        test_modules=test_modules,
        generate_report=args.report,
        fail_fast=args.fail_fast
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()