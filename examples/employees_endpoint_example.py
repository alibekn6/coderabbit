"""
Example usage and test for the new /api/v1/employees endpoint
"""

# Example Response Structure
example_response = {
    "total_employees": 5,
    "employees_with_projects": 5,
    "employees": [
        {
            "employee_name": "Alice Johnson",
            "total_projects": 4,
            "projects_by_health": {
                "red": 1,
                "yellow": 1,
                "green": 2,
                "not_set": 0
            },
            "projects": [
                {
                    "page_id": "project-abc-123",
                    "project_name": "KOZ AI Platform v2",
                    "status": "In Progress",
                    "health_status": "Healthy",
                    "health_color": "green",
                    "priority": "High",
                    "priority_color": "red",
                    "task_count": 24,
                    "url": "https://www.notion.so/project-abc-123",
                    "created_time": "2024-01-15T10:30:00Z",
                    "last_edited_time": "2024-10-17T14:20:00Z"
                },
                {
                    "page_id": "project-def-456",
                    "project_name": "Mobile App Redesign",
                    "status": "Planning",
                    "health_status": "At Risk",
                    "health_color": "red",
                    "priority": "Medium",
                    "priority_color": "yellow",
                    "task_count": 12,
                    "url": "https://www.notion.so/project-def-456",
                    "created_time": "2024-02-20T09:15:00Z",
                    "last_edited_time": "2024-10-16T16:45:00Z"
                },
                {
                    "page_id": "project-ghi-789",
                    "project_name": "Customer Dashboard",
                    "status": "Active",
                    "health_status": "On Track",
                    "health_color": "green",
                    "priority": "Low",
                    "priority_color": "green",
                    "task_count": 8,
                    "url": "https://www.notion.so/project-ghi-789",
                    "created_time": "2024-03-10T11:00:00Z",
                    "last_edited_time": "2024-10-15T13:30:00Z"
                },
                {
                    "page_id": "project-jkl-012",
                    "project_name": "Internal Tools Update",
                    "status": "On Hold",
                    "health_status": "Needs Attention",
                    "health_color": "yellow",
                    "priority": "Low",
                    "priority_color": "green",
                    "task_count": 5,
                    "url": "https://www.notion.so/project-jkl-012",
                    "created_time": "2024-04-05T14:20:00Z",
                    "last_edited_time": "2024-10-10T10:15:00Z"
                }
            ]
        },
        {
            "employee_name": "Bob Smith",
            "total_projects": 2,
            "projects_by_health": {
                "red": 0,
                "yellow": 0,
                "green": 2,
                "not_set": 0
            },
            "projects": [
                {
                    "page_id": "project-mno-345",
                    "project_name": "API Integration",
                    "status": "In Progress",
                    "health_status": "Healthy",
                    "health_color": "green",
                    "priority": "High",
                    "priority_color": "red",
                    "task_count": 15,
                    "url": "https://www.notion.so/project-mno-345",
                    "created_time": "2024-05-12T08:30:00Z",
                    "last_edited_time": "2024-10-17T09:45:00Z"
                },
                {
                    "page_id": "project-pqr-678",
                    "project_name": "Documentation Overhaul",
                    "status": "Active",
                    "health_status": "On Track",
                    "health_color": "green",
                    "priority": "Medium",
                    "priority_color": "yellow",
                    "task_count": 10,
                    "url": "https://www.notion.so/project-pqr-678",
                    "created_time": "2024-06-01T10:00:00Z",
                    "last_edited_time": "2024-10-16T15:20:00Z"
                }
            ]
        },
        {
            "employee_name": "Carol Williams",
            "total_projects": 3,
            "projects_by_health": {
                "red": 2,
                "yellow": 1,
                "green": 0,
                "not_set": 0
            },
            "projects": [
                {
                    "page_id": "project-stu-901",
                    "project_name": "Security Audit",
                    "status": "Critical",
                    "health_status": "Critical",
                    "health_color": "red",
                    "priority": "Urgent",
                    "priority_color": "red",
                    "task_count": 20,
                    "url": "https://www.notion.so/project-stu-901",
                    "created_time": "2024-07-15T12:00:00Z",
                    "last_edited_time": "2024-10-17T16:30:00Z"
                },
                {
                    "page_id": "project-vwx-234",
                    "project_name": "Performance Optimization",
                    "status": "Behind Schedule",
                    "health_status": "At Risk",
                    "health_color": "red",
                    "priority": "High",
                    "priority_color": "red",
                    "task_count": 18,
                    "url": "https://www.notion.so/project-vwx-234",
                    "created_time": "2024-08-01T09:30:00Z",
                    "last_edited_time": "2024-10-16T14:10:00Z"
                },
                {
                    "page_id": "project-yz-567",
                    "project_name": "Testing Framework",
                    "status": "In Progress",
                    "health_status": "Needs Attention",
                    "health_color": "yellow",
                    "priority": "Medium",
                    "priority_color": "yellow",
                    "task_count": 11,
                    "url": "https://www.notion.so/project-yz-567",
                    "created_time": "2024-09-10T11:15:00Z",
                    "last_edited_time": "2024-10-15T12:50:00Z"
                }
            ]
        }
    ]
}

# Usage Examples

def analyze_employee_workload(response):
    """Analyze employee workload from the response"""
    print("=== EMPLOYEE WORKLOAD ANALYSIS ===\n")
    
    for employee in response["employees"]:
        name = employee["employee_name"]
        total = employee["total_projects"]
        health = employee["projects_by_health"]
        
        print(f"👤 {name}")
        print(f"   Total Projects: {total}")
        print(f"   🔴 Red (Critical): {health['red']}")
        print(f"   🟡 Yellow (At Risk): {health['yellow']}")
        print(f"   🟢 Green (Healthy): {health['green']}")
        print(f"   ⚪ Not Set: {health['not_set']}")
        
        # Risk assessment
        risk_score = health['red'] * 3 + health['yellow'] * 2
        if risk_score > 5:
            print(f"   ⚠️  HIGH RISK - Too many critical/at-risk projects!")
        elif risk_score > 0:
            print(f"   ⚡ MODERATE RISK - Some projects need attention")
        else:
            print(f"   ✅ LOW RISK - All projects healthy")
        
        print()

def find_critical_projects(response):
    """Find all critical (red) projects and their owners"""
    print("=== CRITICAL PROJECTS REPORT ===\n")
    
    critical_found = False
    for employee in response["employees"]:
        red_projects = [
            p for p in employee["projects"]
            if p["health_color"] == "red"
        ]
        
        if red_projects:
            critical_found = True
            print(f"👤 {employee['employee_name']} has {len(red_projects)} critical project(s):")
            for project in red_projects:
                print(f"   🔴 {project['project_name']}")
                print(f"      Status: {project['status']}")
                print(f"      Priority: {project['priority']}")
                print(f"      Tasks: {project['task_count']}")
                print(f"      Link: {project['url']}")
            print()
    
    if not critical_found:
        print("✅ No critical projects found!")

def show_employee_projects(response, employee_name):
    """Show all projects for a specific employee"""
    print(f"=== PROJECTS FOR {employee_name.upper()} ===\n")
    
    for employee in response["employees"]:
        if employee["employee_name"].lower() == employee_name.lower():
            print(f"Total Projects: {employee['total_projects']}")
            print(f"Health Distribution: {employee['projects_by_health']}\n")
            
            for project in employee["projects"]:
                health_emoji = {
                    "red": "🔴",
                    "yellow": "🟡",
                    "green": "🟢",
                    None: "⚪"
                }.get(project["health_color"], "⚪")
                
                print(f"{health_emoji} {project['project_name']}")
                print(f"   Status: {project['status']}")
                print(f"   Health: {project['health_status']}")
                print(f"   Priority: {project['priority']}")
                print(f"   Tasks: {project['task_count']}")
                print(f"   Link: {project['url']}")
                print()
            return
    
    print(f"❌ Employee '{employee_name}' not found!")

# Run examples
if __name__ == "__main__":
    # Example 1: Analyze workload
    analyze_employee_workload(example_response)
    
    print("\n" + "="*50 + "\n")
    
    # Example 2: Find critical projects
    find_critical_projects(example_response)
    
    print("\n" + "="*50 + "\n")
    
    # Example 3: Show specific employee's projects
    show_employee_projects(example_response, "Alice Johnson")

# cURL Examples for testing

"""
# 1. Get all employees with projects
curl -X GET "http://localhost:8000/api/v1/employees" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"

# 2. Get employees with projects (with jq formatting)
curl -X GET "http://localhost:8000/api/v1/employees" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" | jq

# 3. Filter to show only employees with critical projects
curl -X GET "http://localhost:8000/api/v1/employees" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" | \
  jq '.employees[] | select(.projects_by_health.red > 0)'

# 4. Count total projects across all employees
curl -X GET "http://localhost:8000/api/v1/employees" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" | \
  jq '[.employees[].total_projects] | add'

# 5. Show employee names and their project counts
curl -X GET "http://localhost:8000/api/v1/employees" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" | \
  jq '.employees[] | {name: .employee_name, projects: .total_projects}'
"""
