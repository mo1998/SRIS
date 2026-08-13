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

# Read a value from .env (handles optional surrounding quotes)
env_get() {
	local key="$1"
	grep -E "^[[:space:]]*${key}=" .env 2>/dev/null | head -1 | cut -d= -f2- \
		| sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//"
}

# Compose command with environment-appropriate file and profiles
COMPOSE_ARGS=()
setup_compose() {
	if [ "$ENVIRONMENT" = "production" ]; then
		COMPOSE_ARGS=(docker compose -f docker-compose.prod.yml --profile certbot)
		if [ "$(env_get ENABLE_LOCAL_LLM)" = "true" ]; then
			COMPOSE_ARGS+=(--profile local-llm)
		fi
		if [ "$(env_get ENABLE_OBSERVABILITY)" != "false" ]; then
			COMPOSE_ARGS+=(--profile observability)
		fi
		if [ -n "$(env_get SLACK_WEBHOOK_URL)" ]; then
			COMPOSE_ARGS+=(--profile alerts)
		fi
	else
		COMPOSE_ARGS=(docker compose)
	fi
}

run_compose() {
	"${COMPOSE_ARGS[@]}" "$@"
}

# Ensure .env exists, selecting the right template per environment
ensure_env() {
	if [ -f .env ]; then
		return
	fi
	if [ "$ENVIRONMENT" = "production" ]; then
		echo -e "${YELLOW}⚠️  .env file not found. Creating from .env.production.example...${NC}"
		cp .env.production.example .env
	else
		echo -e "${YELLOW}⚠️  .env file not found. Creating from .env.example...${NC}"
		cp .env.example .env
	fi
	echo -e "${RED}❌ Please update .env with your configuration before proceeding!${NC}"
	exit 1
}

# Preflight checks for unsafe/incomplete configuration
preflight() {
	local debug
	debug=$(env_get DEBUG)
	if [ "$ENVIRONMENT" = "production" ] && [ "$debug" = "True" ]; then
		echo -e "${RED}❌ DEBUG must be False in production.${NC}"
		exit 1
	fi

	if grep -qE "^[A-Z0-9_]+=CHANGE_ME" .env; then
		echo -e "${RED}❌ .env contains CHANGE_ME placeholder values. Edit .env before deploying:${NC}"
		grep -nE "^[A-Z0-9_]+=CHANGE_ME" .env || true
		exit 1
	fi

	local secret
	secret=$(env_get SECRET_KEY)
	if [ ${#secret} -lt 32 ]; then
		echo -e "${RED}❌ SECRET_KEY must be at least 32 characters.${NC}"
		exit 1
	fi

	for key in POSTGRES_PASSWORD REDIS_PASSWORD FRONTEND_URL ALLOWED_ORIGINS; do
		if [ -z "$(env_get "$key")" ]; then
			echo -e "${RED}❌ $key is required in .env.${NC}"
			exit 1
		fi
	done

	local provider llm local_enabled cloud_enabled
	provider=$(env_get EVALUATION_PROVIDER)
	llm=$(env_get ENABLE_LOCAL_LLM)
	local_enabled=$(env_get LOCAL_LLM_ENABLED)
	cloud_enabled=$(env_get CLOUD_LLM_ENABLED)
	if [ "$provider" = "local_vllm" ] && [ "$llm" != "true" ]; then
		echo -e "${YELLOW}⚠️  EVALUATION_PROVIDER=local_vllm but ENABLE_LOCAL_LLM != true. Evaluations will use the fallback provider.${NC}"
	elif [ "$provider" = "hybrid" ] && [ "$local_enabled" = "true" ] && [ "$cloud_enabled" != "true" ]; then
		echo -e "${YELLOW}⚠️  EVALUATION_PROVIDER=hybrid with local enabled but cloud disabled. If local is unreachable, evaluations fall back to deterministic.${NC}"
	fi

	if [ "$(env_get ENABLE_OBSERVABILITY)" != "false" ] && [ -z "$(env_get GRAFANA_ADMIN_PASSWORD)" ]; then
		echo -e "${RED}❌ GRAFANA_ADMIN_PASSWORD is required when observability is enabled.${NC}"
		exit 1
	fi
}

# Check if Docker is running
check_docker() {
	if ! docker info > /dev/null 2>&1; then
		echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
		exit 1
	fi
	echo -e "${GREEN}✅ Docker is running${NC}"
}

# Check if docker-compose is available
check_docker_compose() {
	if ! docker compose version > /dev/null 2>&1; then
		echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose V2.${NC}"
		exit 1
	fi
	echo -e "${GREEN}✅ Docker Compose is available${NC}"
}

# Obtain/renew Let's Encrypt certificates (production only, idempotent)
ensure_certs() {
	if [ "$ENVIRONMENT" != "production" ]; then
		return
	fi

	local email domain
	email=$(env_get LETSENCRYPT_EMAIL)
	if [ -z "$email" ]; then
		echo -e "${YELLOW}⚠️  LETSENCRYPT_EMAIL not set; assuming certificates already exist in the certbot volume.${NC}"
		return
	fi

	domain=$(env_get DOMAIN)
	if [ -z "$domain" ]; then
		echo -e "${RED}❌ DOMAIN is required when LETSENCRYPT_EMAIL is set.${NC}"
		exit 1
	fi

	echo -e "${YELLOW}🔐 Obtaining/renewing Let's Encrypt certificates for $domain...${NC}"
	run_compose run --rm certbot certonly --webroot --webroot-path=/var/www/certbot \
		--email "$email" --agree-tos --no-eff-email -d "$domain" -d "www.$domain"
	echo -e "${GREEN}✅ Certificates ready${NC}"
}

# Function to pull latest images (production only)
pull_images() {
	if [ "$ENVIRONMENT" = "production" ]; then
		echo -e "${YELLOW}📦 Pulling latest images...${NC}"
		run_compose pull
	fi
}

# Function to build images
build_images() {
	echo -e "${YELLOW}🔨 Building Docker images...${NC}"
	run_compose build --no-cache
	echo -e "${GREEN}✅ Images built successfully${NC}"
}

# Function to run database migrations
run_migrations() {
	echo -e "${YELLOW}🗄️  Running database migrations...${NC}"
	run_compose up db-migrate
	echo -e "${GREEN}✅ Migrations completed${NC}"
}

# Function to start services
start_services() {
	echo -e "${YELLOW}🚀 Starting services...${NC}"
	run_compose up -d
	echo -e "${GREEN}✅ Services started${NC}"
}

# Function to check health
check_health() {
	echo -e "${YELLOW}🏥 Checking service health...${NC}"
	sleep 10

	run_compose ps

	echo -e "${GREEN}✅ All services are running!${NC}"
}

# Function to show logs
show_logs() {
	echo -e "${YELLOW}📝 Showing recent logs...${NC}"
	run_compose logs --tail=50
}

# Main deployment flow
main() {
	ensure_env
	check_docker
	check_docker_compose
	setup_compose
	preflight
	pull_images
	build_images
	run_migrations
	ensure_certs
	start_services
	check_health
	show_logs

	echo ""
	echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
	echo -e "${GREEN}║           🎉 Deployment Successful! 🎉               ║${NC}"
	echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
	echo ""

	if [ "$ENVIRONMENT" = "production" ]; then
		local domain
		domain=$(env_get DOMAIN)
		echo -e "${YELLOW}🌐 Frontend: https://${domain:-yourdomain.com}${NC}"
		echo -e "${YELLOW}🔧 Backend API: https://${domain:-yourdomain.com}/api${NC}"
		echo -e "${YELLOW}📚 API Docs: https://${domain:-yourdomain.com}/api/docs${NC}"
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
