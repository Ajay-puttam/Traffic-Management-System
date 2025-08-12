#!/usr/bin/env python3
"""
Test script for AI Traffic Management System
Tests components without requiring SUMO installation
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_imports():
    """Test if all modules can be imported."""
    print("Testing module imports...")

    try:
        from density_analyzer import DensityAnalyzer

        print("✓ DensityAnalyzer imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import DensityAnalyzer: {e}")
        return False

    try:
        from traffic_optimizer import TrafficOptimizer

        print("✓ TrafficOptimizer imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import TrafficOptimizer: {e}")
        return False

    try:
        from traffic_simulator import TrafficSimulator

        print("✓ TrafficSimulator imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import TrafficSimulator: {e}")
        return False

    try:
        from visualizer import TrafficVisualizer

        print("✓ TrafficVisualizer imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import TrafficVisualizer: {e}")
        return False

    return True


# In test_system.py


def test_density_analyzer():
    """Test DensityAnalyzer functionality."""
    print("\nTesting DensityAnalyzer...")

    try:
        from density_analyzer import DensityAnalyzer

        analyzer = DensityAnalyzer()

        # Test basic functionality
        # --- CORRECTED THIS LINE ---
        assert analyzer.approaches == [
            "north2center",
            "south2center",
            "east2center",
            "west2center",
        ]
        assert len(analyzer.density_history) == 4

        # Test density calculation (mock)
        # --- CORRECTED THIS LINE ---
        density = analyzer.calculate_density("north2center")
        assert isinstance(density, float)

        # Test congestion level
        # --- CORRECTED THIS LINE ---
        level = analyzer.get_congestion_level("north2center")
        assert level in ["Low", "Medium", "High", "Critical"]

        print("✓ DensityAnalyzer tests passed")
        return True

    except Exception as e:
        print(f"✗ DensityAnalyzer tests failed: {e}")
        return False


def test_traffic_optimizer():
    """Test TrafficOptimizer functionality."""
    print("\nTesting TrafficOptimizer...")

    try:
        from traffic_optimizer import TrafficOptimizer

        optimizer = TrafficOptimizer()

        # Test basic functionality
        assert optimizer.traffic_light_id == "center"
        assert optimizer.min_phase_duration == 15
        assert optimizer.max_phase_duration == 60

        # Test phase duration calculation
        recommendations = {
            "densities": {"north_in": 0.2, "south_in": 0.1},
            "priorities": {"north_in": 30, "south_in": 15},
        }

        duration = optimizer.calculate_optimal_duration(0, recommendations)
        assert isinstance(duration, int)
        assert 15 <= duration <= 60

        print("✓ TrafficOptimizer tests passed")
        return True

    except Exception as e:
        print(f"✗ TrafficOptimizer tests failed: {e}")
        return False


def test_config_files():
    """Test if configuration files exist."""
    print("\nTesting configuration files...")

    config_files = [
        "config/intersection.net.xml",
        "config/routes.rou.xml",
        "config/sumo.sumocfg",
    ]

    all_exist = True
    for file_path in config_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path} exists")
        else:
            print(f"✗ {file_path} missing")
            all_exist = False

    return all_exist


def test_dependencies():
    """Test if required dependencies are available."""
    print("\nTesting dependencies...")

    dependencies = ["numpy", "pygame"]
    missing = []

    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✓ {dep} available")
        except ImportError:
            print(f"✗ {dep} missing")
            missing.append(dep)

    if missing:
        print(f"\nMissing dependencies: {', '.join(missing)}")
        print("Install using: pip install -r requirements.txt")
        return False

    return True


def main():
    """Run all tests."""
    print("=== AI Traffic Management System - Test Suite ===\n")

    tests = [
        ("Dependencies", test_dependencies),
        ("Configuration Files", test_config_files),
        ("Module Imports", test_imports),
        ("Density Analyzer", test_density_analyzer),
        ("Traffic Optimizer", test_traffic_optimizer),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"Running {test_name} test...")
        if test_func():
            passed += 1
        print()

    print(f"=== Test Results ===")
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed! The system is ready to run.")
        print("\nTo run the system:")
        print("1. Install SUMO: https://sumo.dlr.de/docs/Downloads.php")
        print("2. Add SUMO to your PATH")
        print("3. Run: python src/main.py")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
