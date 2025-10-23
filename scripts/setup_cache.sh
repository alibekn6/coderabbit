#!/bin/bash

# Notion Cache System - Quick Setup Script
# This script automates the setup process for the caching system

set -e  # Exit on error

echo "🚀 Notion Cache System - Quick Setup"
echo "===================================="
echo ""

# Check if Redis is installed
echo "📦 Checking Redis installation..."
if command -v redis-cli &> /dev/null; then
    echo "   ✓ Redis is installed"
else
    echo "   ✗ Redis is not installed"
    echo ""
    echo "   Please install Redis:"
    echo "   - macOS: brew install redis"
    echo "   - Linux: sudo apt-get install redis-server"
    echo "   - Docker: docker run -d -p 6379:6379 redis:alpine"
    exit 1
fi

# Check if Redis is running
echo ""
echo "🔌 Checking Redis connection..."
if redis-cli ping &> /dev/null; then
    echo "   ✓ Redis is running"
else
    echo "   ✗ Redis is not running"
    echo "   Starting Redis..."
    
    # Try to start Redis (macOS)
    if command -v brew &> /dev/null; then
        brew services start redis
        sleep 2
        if redis-cli ping &> /dev/null; then
            echo "   ✓ Redis started successfully"
        else
            echo "   ✗ Failed to start Redis"
            exit 1
        fi
    else
        echo "   Please start Redis manually:"
        echo "   - macOS: brew services start redis"
        echo "   - Linux: sudo systemctl start redis"
        exit 1
    fi
fi

# Install Python dependencies
echo ""
echo "📥 Installing Python dependencies..."
pip install -e . || {
    echo "   ✗ Failed to install dependencies"
    exit 1
}
echo "   ✓ Dependencies installed"

# Run database migrations
echo ""
echo "🗄️  Running database migrations..."
echo "   Generating migration..."
alembic revision --autogenerate -m "add_notion_cache_tables" || {
    echo "   ⚠️  Migration generation failed (tables may already exist)"
}

echo "   Applying migrations..."
alembic upgrade head || {
    echo "   ✗ Failed to apply migrations"
    exit 1
}
echo "   ✓ Migrations completed"

# Create .env if not exists
if [ ! -f .env ]; then
    echo ""
    echo "⚙️  Creating .env file..."
    cat > .env.example << 'EOF'
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Cache Settings
CACHE_UPDATE_INTERVAL_MINUTES=30

# Celery (optional overrides)
# CELERY_BROKER_URL=redis://localhost:6379/0
# CELERY_RESULT_BACKEND=redis://localhost:6379/0
EOF
    echo "   ✓ Created .env.example"
    echo "   ⚠️  Please create .env file with your configuration"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "===================================="
echo "📋 Next Steps:"
echo "===================================="
echo ""
echo "1. Start the services (in separate terminals):"
echo ""
echo "   Terminal 1 - FastAPI:"
echo "   $ make run-local"
echo ""
echo "   Terminal 2 - Celery Worker:"
echo "   $ make celery-worker"
echo ""
echo "   Terminal 3 - Celery Beat:"
echo "   $ make celery-beat"
echo ""
echo "   OR combine worker + beat (dev only):"
echo "   $ make celery-worker-beat"
echo ""
echo "2. Initialize the cache:"
echo "   $ make init-cache"
echo ""
echo "3. Check cache status via API:"
echo "   $ curl http://localhost:8888/api/v1/cache-info/projects"
echo ""
echo "===================================="
echo "📚 Documentation:"
echo "   - CACHE_IMPLEMENTATION.md - Quick overview"
echo "   - CACHE_SYSTEM_GUIDE.md   - Full documentation"
echo "===================================="
echo ""
