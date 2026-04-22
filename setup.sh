#!/bin/bash

# AMS Backend Setup Script
# This script sets up the complete AMS backend environment

set -e  # Exit on any error

echo "🚀 Starting AMS Backend Setup..."

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command_exists docker; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command_exists docker-compose; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Check if .env exists, if not copy from .env.example
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "✅ .env file created. You may want to review and modify it."
else
    echo "✅ .env file already exists"
fi

# Build and start services
echo "🏗️  Building Docker images..."
docker-compose build

echo "🔄 Starting services..."
docker-compose up -d

echo "⏳ Waiting for services to be healthy..."
# Wait for PostgreSQL to be ready
while ! docker-compose exec -T postgres pg_isready -U ams_user -d ams_db > /dev/null 2>&1; do
    echo "⏳ Waiting for PostgreSQL..."
    sleep 2
done

# Wait for Redis to be ready
while ! docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; do
    echo "⏳ Waiting for Redis..."
    sleep 2
done

# Wait for FastAPI to be ready
while ! curl -f http://localhost:8000/health > /dev/null 2>&1; do
    echo "⏳ Waiting for FastAPI..."
    sleep 2
done

echo "✅ All services are healthy"

# Run database migrations
echo "🗄️  Running database migrations..."
docker-compose exec -T fastapi alembic upgrade head

# Seed database with sample data
echo "🌱 Seeding database with sample data..."
docker-compose exec -T fastapi python seed_db.py

echo ""
echo "🎉 AMS Backend setup completed successfully!"
echo ""
echo "📍 Service URLs:"
echo "   • API Documentation: http://localhost:8000/api/v1/docs"
echo "   • API Base URL:      http://localhost:8000/api/v1"
echo "   • Health Check:      http://localhost:8000/health"
echo ""
echo "🔑 Default Credentials:"
echo "   • Admin:    admin@ams.local / admin123"
echo "   • Operator: operator@ams.local / operator123"
echo "   • Viewer:   viewer@ams.local / viewer123"
echo ""
echo "🔧 Useful Commands:"
echo "   • View logs:         docker-compose logs -f"
echo "   • Stop services:     docker-compose down"
echo "   • Restart services:  docker-compose restart"
echo "   • Shell access:      docker-compose exec fastapi bash"
echo ""
echo "✨ Your AMS Backend is ready to use!"
