#!/bin/bash

# Script to populate cache and test the /api/v1/employees endpoint

echo "🚀 Cache Population & Endpoint Test Script"
echo "=========================================="
echo ""

# Step 1: Trigger cache updates
echo "📥 Step 1: Triggering cache updates..."
docker-compose exec app python -c "
from src.tasks.notion_cache_tasks import update_projects_cache, update_todos_cache, update_tasks_cache
print('Triggering projects cache update...')
update_projects_cache.delay()
print('Triggering todos cache update...')
update_todos_cache.delay()
print('Triggering tasks cache update...')
update_tasks_cache.delay()
print('✅ All cache update tasks triggered!')
"

echo ""
echo "⏳ Step 2: Waiting for cache to populate (30 seconds)..."
sleep 30

echo ""
echo "📊 Step 3: Checking cache status..."
docker-compose logs celery-worker --tail 10 | grep -i "cache updated\|succeeded"

echo ""
echo "🔐 Step 4: Getting authentication token..."
echo "Please enter your username:"
read USERNAME
echo "Please enter your password:"
read -s PASSWORD

# Get JWT token
TOKEN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}")

TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

if [ -z "$TOKEN" ] || [ "$TOKEN" == "None" ]; then
    echo "❌ Authentication failed!"
    echo "Response: $TOKEN_RESPONSE"
    echo ""
    echo "💡 Make sure you have a user account. To create one:"
    echo "   docker-compose exec app python -c \"from src.services.auth_service import AuthService; from src.db.sync_database import get_sync_db; db = next(get_sync_db()); service = AuthService(db); user = service.register_user('your_username', 'your_password', 'your@email.com'); print(f'User created: {user.username}')\""
    exit 1
fi

echo "✅ Authentication successful!"
echo ""

# Test the endpoint
echo "🎯 Step 5: Testing /api/v1/employees endpoint..."
RESPONSE=$(curl -s -X GET "http://localhost:8000/api/v1/employees" \
  -H "Authorization: Bearer $TOKEN")

# Check if response has data
EMPLOYEE_COUNT=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_employees', 0))" 2>/dev/null)

if [ "$EMPLOYEE_COUNT" -gt 0 ]; then
    echo "✅ SUCCESS! Found $EMPLOYEE_COUNT employees"
    echo ""
    echo "📋 Employee Summary:"
    echo $RESPONSE | python3 -c "
import sys, json
data = json.load(sys.stdin)
for emp in data.get('employees', []):
    name = emp['employee_name']
    projects = emp['total_projects']
    health = emp['projects_by_health']
    print(f\"  👤 {name}: {projects} projects (🔴 {health['red']} 🟡 {health['yellow']} 🟢 {health['green']})\")
"
else
    echo "⚠️  No employees found in response"
    echo "Response: $RESPONSE"
    echo ""
    echo "💡 This might mean:"
    echo "   1. Cache is still populating (wait a bit longer)"
    echo "   2. No projects have assignees in Notion"
    echo "   3. Cache update failed (check logs)"
fi

echo ""
echo "🎉 Test complete!"
echo ""
echo "📚 To view full response:"
echo "curl -X GET 'http://localhost:8000/api/v1/employees' \\"
echo "  -H 'Authorization: Bearer $TOKEN' | jq"
