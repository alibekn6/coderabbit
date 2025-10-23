
import asyncio
from notion_client import AsyncClient

from src.core.config import settings

async def find_kanban_database():
    notion = AsyncClient(auth=settings.NOTION_API_KEY)
    
    print("🔍 Searching for Kanban databases...\n")
    
    try:
        # Search for all databases
        response = await notion.search(filter={"property": "object", "value": "database"})
        
        databases = response.get("results", [])
        print(f"Found {len(databases)} databases total\n")
        
        # Look for databases that might be Kanban boards
        kanban_keywords = ["kanban", "board", "task", "project", "sprint", "desk"]
        
        for db in databases:
            db_id = db["id"]
            title = ""
            if db.get("title"):
                title = "".join([t["plain_text"] for t in db["title"]])
            elif db.get("properties", {}).get("Name", {}).get("title"):
                title = "Untitled Database"
            
            # Check if this might be a Kanban database
            is_potential_kanban = any(keyword in title.lower() for keyword in kanban_keywords)
            
            print(f"{'🎯' if is_potential_kanban else '📊'} Database: {title}")
            print(f"   ID: {db_id}")
            print(f"   URL: {db.get('url', 'N/A')}")
            print("   Properties:")
            
            properties = db.get("properties", {})
            
            # Check for properties that indicate this is a Kanban board
            has_status = False
            has_person = False
            has_project = False
            status_prop_name = None
            person_prop_name = None
            project_prop_name = None
            
            for prop_name, prop_info in properties.items():
                prop_type = prop_info.get("type", "unknown")
                print(f"      - {prop_name}: {prop_type}")
                
                # Look for status properties (often with color options)
                if prop_type == "status":
                    has_status = True
                    status_prop_name = prop_name
                elif prop_type == "select" and any(keyword in prop_name.lower() for keyword in ["status", "state", "stage"]):
                    has_status = True
                    status_prop_name = prop_name
                    # Check if it has color options
                    options = prop_info.get("select", {}).get("options", [])
                    if options:
                        print(f"         Options: {[opt['name'] + ' (' + opt.get('color', 'no color') + ')' for opt in options]}")
                
                # Look for person/responsible properties
                if prop_type == "people" and any(keyword in prop_name.lower() for keyword in ["responsible", "assignee", "owner", "assigned"]):
                    has_person = True
                    person_prop_name = prop_name
                
                # Look for project properties
                if any(keyword in prop_name.lower() for keyword in ["project", "initiative", "epic"]):
                    has_project = True
                    project_prop_name = prop_name
            
            # If this database has the key properties, fetch sample data
            if has_status or has_person or is_potential_kanban:
                print("\n   ✨ This looks like a potential Kanban database!")
                print(f"      Has Status: {has_status} ({status_prop_name})")
                print(f"      Has Person: {has_person} ({person_prop_name})")
                print(f"      Has Project: {has_project} ({project_prop_name})")
                
                # Fetch a few sample pages to see the data
                try:
                    pages_response = await notion.databases.query(database_id=db_id, page_size=3)
                    pages = pages_response.get("results", [])
                    
                    if pages:
                        print(f"\n      📄 Sample data from {len(pages)} pages:")
                        for i, page in enumerate(pages, 1):
                            print(f"\n      Page {i}:")
                            page_props = page.get("properties", {})
                            
                            # Print all properties to see what's available
                            for prop_name, prop_value in page_props.items():
                                prop_type = prop_value.get("type")
                                
                                if prop_type == "title":
                                    title_text = "".join([t["plain_text"] for t in prop_value.get("title", [])])
                                    print(f"         {prop_name}: {title_text}")
                                elif prop_type == "status":
                                    status = prop_value.get("status", {})
                                    status_name = status.get("name", "N/A")
                                    status_color = status.get("color", "N/A")
                                    print(f"         {prop_name}: {status_name} (color: {status_color})")
                                elif prop_type == "select":
                                    select = prop_value.get("select", {})
                                    if select:
                                        select_name = select.get("name", "N/A")
                                        select_color = select.get("color", "N/A")
                                        print(f"         {prop_name}: {select_name} (color: {select_color})")
                                elif prop_type == "people":
                                    people = prop_value.get("people", [])
                                    if people:
                                        people_names = [p.get("name", p.get("id")) for p in people]
                                        print(f"         {prop_name}: {', '.join(people_names)}")
                                elif prop_type == "rich_text":
                                    text = "".join([t["plain_text"] for t in prop_value.get("rich_text", [])])
                                    if text:
                                        print(f"         {prop_name}: {text}")
                                elif prop_type == "relation":
                                    relations = prop_value.get("relation", [])
                                    if relations:
                                        print(f"         {prop_name}: {len(relations)} related items")
                except Exception as e:
                    print(f"      ⚠️  Could not fetch sample data: {e}")
            
            print("\n" + "="*80 + "\n")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(find_kanban_database())
