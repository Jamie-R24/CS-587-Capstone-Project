#!/bin/bash
# System Test Runner
# Convenience script for running system tests with proper configuration

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================================"
echo "System Tests Runner"
echo -e "======================================================================${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check if Docker is running
if ! docker ps > /dev/null 2>&1; then
    echo -e "${RED}ERROR: Docker is not running or not accessible${NC}"
    echo "Please start Docker and try again"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}ERROR: docker-compose is not installed${NC}"
    echo "Please install docker-compose and try again"
    exit 1
fi
echo -e "${GREEN}✓ docker-compose is available${NC}"

# Check if pytest is installed
if ! pytest --version > /dev/null 2>&1; then
    echo -e "${RED}ERROR: pytest is not installed${NC}"
    echo "Install with: pip install pytest==7.4.3 pytest-timeout==2.2.0 docker==7.0.0"
    exit 1
fi
echo -e "${GREEN}✓ pytest is installed${NC}"

# Check if docker Python package is installed
if ! python3 -c "import docker" > /dev/null 2>&1; then
    echo -e "${RED}ERROR: docker Python package is not installed${NC}"
    echo "Install with: pip install docker==7.0.0"
    exit 1
fi
echo -e "${GREEN}✓ docker Python package is installed${NC}"

echo ""

# Parse command line arguments
TEST_FILE=""
TIMEOUT=1800
VERBOSE="-v -s"

if [ "$1" == "quick" ]; then
    TEST_FILE="tests/system/test_container_integration.py"
    echo -e "${BLUE}Running quick test (container integration only)${NC}"
elif [ "$1" == "detection" ]; then
    TEST_FILE="tests/system/test_end_to_end_detection.py"
    echo -e "${BLUE}Running detection pipeline tests${NC}"
elif [ "$1" == "retraining" ]; then
    TEST_FILE="tests/system/test_retraining_cycle.py"
    TIMEOUT=900
    echo -e "${BLUE}Running retraining cycle tests (~10 min)${NC}"
elif [ "$1" == "poisoning" ]; then
    TEST_FILE="tests/system/test_poisoning_impact.py"
    TIMEOUT=1200
    echo -e "${BLUE}Running poisoning impact tests (~15 min)${NC}"
elif [ "$1" == "all" ] || [ -z "$1" ]; then
    TEST_FILE="tests/system/"
    echo -e "${BLUE}Running ALL system tests (~35 min)${NC}"
else
    echo -e "${YELLOW}Usage: $0 [quick|detection|retraining|poisoning|all]${NC}"
    echo ""
    echo "Options:"
    echo "  quick      - Run container integration tests only (~5 min)"
    echo "  detection  - Run end-to-end detection tests (~5 min)"
    echo "  retraining - Run retraining cycle tests (~10 min)"
    echo "  poisoning  - Run poisoning impact tests (~15 min)"
    echo "  all        - Run all system tests (~35 min) [default]"
    echo ""
    exit 1
fi

echo ""
echo -e "${YELLOW}Test Configuration:${NC}"
echo "  Test file: $TEST_FILE"
echo "  Verbosity: $VERBOSE"
echo "  Note: Individual tests have timeout decorators (600-1200s)"
echo ""

# Clean up any existing containers
echo -e "${YELLOW}Cleaning up any existing containers...${NC}"
cd /home/jamier/Desktop/CS-587-Capstone-Project
docker-compose down -v > /dev/null 2>&1 || true
echo -e "${GREEN}✓ Cleanup complete${NC}"
echo ""

# Run tests
echo -e "${BLUE}======================================================================"
echo "Starting tests..."
echo -e "======================================================================${NC}"
echo ""

# Note: Individual tests have @pytest.mark.timeout decorators, so we don't need --timeout
if pytest "$TEST_FILE" $VERBOSE; then
    echo ""
    echo -e "${GREEN}======================================================================"
    echo "✓ ALL TESTS PASSED!"
    echo -e "======================================================================${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}======================================================================"
    echo "✗ SOME TESTS FAILED"
    echo -e "======================================================================${NC}"
    echo ""
    echo "Debugging tips:"
    echo "  1. Check container logs: docker logs workstation"
    echo "  2. View container status: docker ps"
    echo "  3. Review test output above for specific failures"
    echo "  4. Consult tests/system/README.md for troubleshooting"
    echo ""
    exit 1
fi
