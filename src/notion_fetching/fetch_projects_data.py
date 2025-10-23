import asyncio
from notion_client import AsyncClient

from src.core.config import settings

async def fetch_projects_data():
    notion = AsyncClient(auth=settings.NOTION_API_KEY)
    
    # Projects database ID
    database_id = "1b33b84f-1fac-807e-8133-f5641df4a085"
    
    print("🎯 Fetching data from Projects database...\n")
    
    try:
        # Fetch all pages from the database
        has_more = True
        start_cursor = None
        all_projects = []
        
        while has_more:
            query_params = {"database_id": database_id, "page_size": 100}
            if start_cursor:
                query_params["start_cursor"] = start_cursor
            
            response = await notion.databases.query(**query_params)
            all_projects.extend(response.get("results", []))
            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")
        
        print(f"📊 Found {len(all_projects)} projects\n")
        print("="*100)
        
        # Extract the data we need
        projects_data = []
        
        for page in all_projects:
            props = page.get("properties", {})
            
            # Project name (title property)
            project_name_prop = props.get("Project name", {})
            project_name = "Untitled"
            if project_name_prop.get("type") == "title" and project_name_prop.get("title"):
                project_name = "".join([t.get("plain_text", "") for t in project_name_prop["title"]])
                # If empty after joining, use Untitled
                if not project_name.strip():
                    project_name = "Untitled"
            
            # Health status (red/yellow/green)
            health_prop = props.get("Health", {})
            health_status = "N/A"
            health_color = "N/A"
            if health_prop.get("select") and health_prop["select"]:
                health_status = health_prop["select"].get("name", "N/A")
                health_color = health_prop["select"].get("color", "N/A")
            
            # Responsible person (Assignee)
            assignee_prop = props.get("Assignee", {})
            assignees = []
            if assignee_prop.get("people"):
                assignees = [p.get("name", p.get("id", "Unknown")) for p in assignee_prop["people"]]
            
            # Status (additional info)
            status_prop = props.get("Status", {})
            status = "N/A"
            if status_prop.get("status") and status_prop["status"]:
                status = status_prop["status"].get("name", "N/A")
            
            # Priority
            priority_prop = props.get("Priority", {})
            priority = "N/A"
            priority_color = "N/A"
            if priority_prop.get("select") and priority_prop["select"]:
                priority = priority_prop["select"].get("name", "N/A")
                priority_color = priority_prop["select"].get("color", "N/A")
            
            # Task count (if available)
            task_count_prop = props.get("Task Count", {})
            task_count = 0
            if task_count_prop.get("rollup"):
                task_count = task_count_prop["rollup"].get("number", 0) or 0
            
            project_data = {
                "project_name": project_name,
                "health_status": health_status,
                "health_color": health_color,
                "assignees": assignees if assignees else ["Unassigned"],
                "status": status,
                "priority": priority,
                "priority_color": priority_color,
                "task_count": int(task_count)
            }
            
            projects_data.append(project_data)
            
            # Print the data
            print(f"\n📁 Project: {project_data['project_name']}")
            print(f"   🚦 Health: {project_data['health_status']} (color: {project_data['health_color']})")
            print(f"   👤 Assignees: {', '.join(project_data['assignees'])}")
            print(f"   📊 Status: {project_data['status']}")
            print(f"   ⚡ Priority: {project_data['priority']} (color: {project_data['priority_color']})")
            print(f"   📝 Tasks: {project_data['task_count']}")
            print("-" * 100)
        
        print("\n\n✅ Summary:")
        print(f"   Total projects: {len(projects_data)}")
        
        # Count by health color (RED/YELLOW/GREEN - what you need!)
        health_counts = {}
        for project in projects_data:
            color = project["health_color"]
            health_counts[color] = health_counts.get(color, 0) + 1
        
        print("\n   Projects by health status (RED/YELLOW/GREEN):")
        for color, count in sorted(health_counts.items(), key=lambda x: x[1], reverse=True):
            emoji = "🔴" if color == "red" else "🟡" if color == "yellow" else "🟢" if color == "green" else "⚪"
            print(f"      {emoji} {color.upper()}: {count}")
        
        # Count by person
        person_counts = {}
        for project in projects_data:
            for person in project["assignees"]:
                person_counts[person] = person_counts.get(person, 0) + 1
        
        print("\n   Projects by responsible person:")
        for person, count in sorted(person_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"      {person}: {count}")
        
        # Show projects by health status
        print("\n\n🔴 RED Projects:")
        red_projects = [p for p in projects_data if p["health_color"] == "red"]
        if red_projects:
            for p in red_projects:
                print(f"   - {p['project_name']} (Assignees: {', '.join(p['assignees'])})")
        else:
            print("   None")
        
        print("\n🟡 YELLOW Projects:")
        yellow_projects = [p for p in projects_data if p["health_color"] == "yellow"]
        if yellow_projects:
            for p in yellow_projects:
                print(f"   - {p['project_name']} (Assignees: {', '.join(p['assignees'])})")
        else:
            print("   None")
        
        print("\n🟢 GREEN Projects:")
        green_projects = [p for p in projects_data if p["health_color"] == "green"]
        if green_projects:
            for p in green_projects:
                print(f"   - {p['project_name']} (Assignees: {', '.join(p['assignees'])})")
        else:
            print("   None")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fetch_projects_data())
