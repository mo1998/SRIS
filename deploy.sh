#!/bin/bash

# Smart Remote Interview System - Deployment Script
# Usage: ./deploy.sh [production|staging|development]

set -e

ENVIRONMENT=${1:-development}

echo "🚀 Deploying Smart Remote Interview System..."
echo "📋 Environment: $ENVIRONMENT"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}⚠️  Please update .env with your configuration before proceeding!${NC}"
    exit 1
fi

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker is running${NC}"
}

# Function to check if docker-compose is available
check_docker_compose() {
    if ! docker compose version > /dev/null 2>&1; then
        echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose V2.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker Compose is available${NC}"
}

# Function to pull latest images (production only)
pull_images() {
    if [ "$ENVIRONMENT" = "production" ]; then
        echo -e "${YELLOW}📦 Pulling latest images...${NC}"
        docker compose -f docker-compose.prod.yml pull
    fi
}

# Function to build images
build_images() {
    echo -e "${YELLOW}🔨 Building Docker images...${NC}"
    if [ "$ENVIRONMENT" = "production" ]; then
        docker compose -f docker-compose.prod.yml build --no-cache
    else
        docker compose build --no-cache
    fi
    echo -e "${GREEN}✅ Images built successfully${NC}"
}

# Function to run database migrations
run_migrations() {
    echo -e "${YELLOW}🗄️  Running database migrations...${NC}"
    if [ "$ENVIRONMENT" = "production" ]; then
        docker compose -f docker-compose.prod.yml up db-migrate
    else
        docker compose up db-migrate
    fi
    echo -e "${GREEN}✅ Migrations completed${NC}"
}

# Function to start services
start_services() {
    echo -e "${YELLOW}🚀 Starting services...${NC}"
    if [ "$ENVIRONMENT" = "production" ]; then
        docker compose -f docker-compose.prod.yml up -d
    else
        docker compose up -d
    fi
    echo -e "${GREEN}✅ Services started${NC}"
}

# Function to check health
check_health() {
    echo -e "${YELLOW}🏥 Checking service health...${NC}"
    sleep 10
    
    if [ "$ENVIRONMENT" = "production" ]; then
        docker compose -f docker-compose.prod.yml ps
    else
        docker compose ps
    fi
    
    echo -e "${GREEN}✅ All services are running!${NC}"
}

# Function to show logs
show_logs() {
    echo -e "${YELLOW}📝 Showing recent logs...${NC}"
    if [ "$ENVIRONMENT" = "production" ]; then
        docker compose -f docker-compose.prod.yml logs --tail=50
    else
        docker compose logs --tail=50
    fi
}

# Main deployment flow
main() {
    check_docker
    check_docker_compose
    pull_images
    build_images
    run_migrations
    start_services
    check_health
    show_logs
    
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║           🎉 Deployment Successful! 🎉               ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    if [ "$ENVIRONMENT" = "production" ]; then
        echo -e "${YELLOW}🌐 Frontend: https://yourdomain.com${NC}"
        echo -e "${YELLOW}🔧 Backend API: https://yourdomain.com/api${NC}"
        echo -e "${YELLOW}📚 API Docs: https://yourdomain.com/api/docs${NC}"
    else
        echo -e "${YELLOW}🌐 Frontend: http://localhost${NC}"
        echo -e "${YELLOW}🔧 Backend API: http://localhost:8000${NC}"
        echo -e "${YELLOW}📚 API Docs: http://localhost:8000/docs${NC}"
    fi
    
    echo ""
    echo -e "${YELLOW}Useful commands:${NC}"
    echo -e "  View logs:          docker compose logs -f"
    echo -e "  Stop services:      docker compose down"
    echo -e "  Restart services:   docker compose restart"
    echo -e "  Rebuild:            ./deploy.sh $ENVIRONMENT"
    echo ""
}

main
