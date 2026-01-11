#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Hospital API Performance Test               ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓ ${PYTHON_VERSION}${NC}"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -q -r backend/requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Check database configuration
if [ -n "$DATABASE_URL" ]; then
    echo -e "${GREEN}✓ DATABASE_URL is set (PostgreSQL)${NC}"
else
    echo -e "${YELLOW}⚠ DATABASE_URL not set. Using SQLite for local development${NC}"
fi

echo ""
echo -e "${BLUE}Starting servers...${NC}"
echo ""

# Start backend server in background
echo -e "${GREEN}Starting backend server on port 8000...${NC}"
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to start
echo -e "${YELLOW}Waiting for backend to start...${NC}"
for i in {1..10}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is ready${NC}"
        break
    fi
    sleep 1
done

# Seed database via API
echo -e "${YELLOW}Seeding database with 1000 test records...${NC}"
SEED_RESULT=$(curl -s -X POST "http://localhost:8000/api/seed?count=1000")
echo -e "${GREEN}✓ ${SEED_RESULT}${NC}"

# Start simple HTTP server for frontend
echo -e "${GREEN}Starting frontend server on port 8080...${NC}"
python -m http.server 8080 --directory frontend &
FRONTEND_PID=$!

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Servers Running                              ║${NC}"
echo -e "${BLUE}╠══════════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║  Backend:  ${GREEN}http://localhost:8000${BLUE}             ║${NC}"
echo -e "${BLUE}║  Frontend: ${GREEN}http://localhost:8080${BLUE}             ║${NC}"
echo -e "${BLUE}║  API Docs: ${GREEN}http://localhost:8000/docs${BLUE}        ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all servers${NC}"

# Trap Ctrl+C to cleanup
cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping servers...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN}✓ All servers stopped${NC}"
    exit 0
}
trap cleanup INT TERM

# Wait for processes
wait
