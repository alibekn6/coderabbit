import asyncio
from notion_client import AsyncClient

from core.config import settings

async def fetch_kanban_data():
    notion = AsyncClient(auth=settings.NOTION_API_KEY)
    
    # PBIs database ID
    database_id = "1fc3b84f-1fac-8022-9cdf-d70eb1da7312"
    
    print("🎯 Fetching data from PBIs (Kanban) database...\n")
    
    try:
        # Fetch all pages from the database
        has_more = True
        start_cursor = None
        all_pages = []
        
        while has_more:
            query_params = {"database_id": database_id, "page_size": 100}
            if start_cursor:
                query_params["start_cursor"] = start_cursor
            
            response = await notion.databases.query(**query_params)
            all_pages.extend(response.get("results", []))
            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")
        
        print(f"📊 Found {len(all_pages)} tasks in Kanban\n")
        print("="*100)
        
        # Extract the data we need
        kanban_data = []
        
        for page in all_pages:
            props = page.get("properties", {})
            
            # Task title
            title_prop = props.get("Название бага или предложение по улучшению", {})
            task_title = ""
            if title_prop.get("title"):
                task_title = "".join([t["plain_text"] for t in title_prop["title"]])
            
            # Project/Epic
            epic_prop = props.get("Epic", {})
            project = ""
            if epic_prop.get("rich_text"):
                project = "".join([t["plain_text"] for t in epic_prop["rich_text"]])
            
            # Status with color
            status_prop = props.get("Status", {})
            status_name = "N/A"
            status_color = "N/A"
            if status_prop.get("select") and status_prop["select"]:
                status_name = status_prop["select"].get("name", "N/A")
                status_color = status_prop["select"].get("color", "N/A")
            
            # Priority (also has status type with colors)
            priority_prop = props.get("Priority", {})
            priority_name = "N/A"
            priority_color = "N/A"
            if priority_prop.get("status") and priority_prop["status"]:
                priority_name = priority_prop["status"].get("name", "N/A")
                priority_color = priority_prop["status"].get("color", "N/A")
            
            # Responsible person (Assigned To)
            assigned_prop = props.get("Assigned To", {})
            assigned_to = []
            if assigned_prop.get("people"):
                assigned_to = [p.get("name", p.get("id", "Unknown")) for p in assigned_prop["people"]]
            
            # Also check Person field
            person_prop = props.get("Person", {})
            if person_prop.get("people") and not assigned_to:
                assigned_to = [p.get("name", p.get("id", "Unknown")) for p in person_prop["people"]]
            
            task_data = {
                "task_title": task_title or "Untitled",
                "project": project or "No Project",
                "status": status_name,
                "status_color": status_color,
                "priority": priority_name,
                "priority_color": priority_color,
                "assigned_to": assigned_to if assigned_to else ["Unassigned"]
            }
            
            kanban_data.append(task_data)
            
            # Print the data
            print(f"\n📌 Task: {task_data['task_title']}")
            print(f"   🎯 Project: {task_data['project']}")
            print(f"   📊 Status: {task_data['status']} (color: {task_data['status_color']})")
            print(f"   ⚡ Priority: {task_data['priority']} (color: {task_data['priority_color']})")
            print(f"   👤 Assigned To: {', '.join(task_data['assigned_to'])}")
            print("-" * 100)
        
        print(f"\n\n✅ Summary:")
        print(f"   Total tasks: {len(kanban_data)}")
        
        # Count by status color
        color_counts = {}
        for task in kanban_data:
            color = task["status_color"]
            color_counts[color] = color_counts.get(color, 0) + 1
        
        print(f"\n   Tasks by status color:")
        for color, count in sorted(color_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"      {color}: {count}")
        
        # Count by person
        person_counts = {}
        for task in kanban_data:
            for person in task["assigned_to"]:
                person_counts[person] = person_counts.get(person, 0) + 1
        
        print(f"\n   Tasks by person:")
        for person, count in sorted(person_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"      {person}: {count}")
        
        # Count by project
        project_counts = {}
        for task in kanban_data:
            project = task["project"]
            project_counts[project] = project_counts.get(project, 0) + 1
        
        print(f"\n   Tasks by project:")
        for project, count in sorted(project_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"      {project}: {count}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fetch_kanban_data())
