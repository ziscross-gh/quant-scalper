#!/bin/bash
# Automated test runner for Quant Scalper Trading Bot

set -e  # Exit on error

echo "=========================================="
echo "🧪 Quant Scalper - Test Runner"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
TEST_TYPE=${1:-"all"}
COVERAGE=${2:-"yes"}

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest not found${NC}"
    echo "   Installing test dependencies..."
    pip install -r requirements-test.txt
fi

# Run tests based on type
case $TEST_TYPE in
    "unit")
        echo "Running unit tests only..."
        if [ "$COVERAGE" = "yes" ]; then
            pytest tests/unit/ --cov=bot --cov-report=term-missing --cov-report=html -v
        else
            pytest tests/unit/ -v
        fi
        ;;
    
    "integration")
        echo "Running integration tests only..."
        if [ "$COVERAGE" = "yes" ]; then
            pytest tests/integration/ --cov=bot --cov-report=term-missing --cov-report=html -v
        else
            pytest tests/integration/ -v
        fi
        ;;
    
    "fast")
        echo "Running fast tests only (skipping slow tests)..."
        pytest -m "not slow" -v
        ;;
    
    "all")
        echo "Running all tests..."
        if [ "$COVERAGE" = "yes" ]; then
            pytest --cov=bot --cov-report=term-missing --cov-report=html --cov-report=xml -v
        else
            pytest -v
        fi
        ;;
    
    "parallel")
        echo "Running tests in parallel..."
        pytest -n auto --cov=bot --cov-report=term-missing --cov-report=html -v
        ;;
    
    *)
        echo -e "${RED}❌ Unknown test type: $TEST_TYPE${NC}"
        echo "Usage: $0 [all|unit|integration|fast|parallel] [yes|no]"
        exit 1
        ;;
esac

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo "=========================================="
    
    if [ "$COVERAGE" = "yes" ]; then
        echo ""
        echo "Coverage report generated:"
        echo "  - Terminal: (displayed above)"
        echo "  - HTML: htmlcov/index.html"
        echo "  - XML: coverage.xml"
        echo ""
        echo "To view HTML report:"
        echo "  open htmlcov/index.html"
    fi
else
    echo ""
    echo "=========================================="
    echo -e "${RED}❌ Tests failed!${NC}"
    echo "=========================================="
    exit 1
fi
