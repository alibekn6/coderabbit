import asyncio
from notion_client import AsyncClient

from core.config import settings
async def find_projects_database():
    notion = AsyncClient(auth=settings.NOTION_API_KEY)
    
    print("🔍 Searching for Projects database (parent of PBIs/tasks)...\n")
    
    try:
        # Search for all databases
        response = await notion.search(filter={"property": "object", "value": "database"})
        
        databases = response.get("results", [])
        print(f"Found {len(databases)} databases total\n")
        
        # Look for databases that might contain projects
        project_keywords = ["project", "epic", "initiative", "программ", "проект"]
        
        for db in databases:
            db_id = db["id"]
            title = ""
            if db.get("title"):
                title = "".join([t["plain_text"] for t in db["title"]])
            elif db.get("properties", {}).get("Name", {}).get("title"):
                title = "Untitled Database"
            
            # Check if this might be a projects database
            is_potential_projects = any(keyword in title.lower() for keyword in project_keywords)
            
            properties = db.get("properties", {})
            
            # Look for key properties that indicate this is a projects database
            has_status_with_colors = False
            has_person = False
            has_relation_to_tasks = False
            status_prop_name = None
            person_prop_name = None
            
            for prop_name, prop_info in properties.items():
                prop_type = prop_info.get("type", "unknown")
                
                # Look for status/select with color options
                if prop_type == "status":
                    has_status_with_colors = True
                    status_prop_name = prop_name
                elif prop_type == "select":
                    options = prop_info.get("select", {}).get("options", [])
                    if options and any(opt.get("color") in ["red", "green", "blue"] for opt in options):
                        has_status_with_colors = True
                        status_prop_name = prop_name
                
                # Look for person properties
                if prop_type == "people":
                    has_person = True
                    person_prop_name = prop_name
                
                # Look for relations (might relate to tasks)
                if prop_type == "relation":
                    has_relation_to_tasks = True
            
            # If this database looks like a projects database, print details
            if (is_potential_projects or has_status_with_colors) and (has_person or has_relation_to_tasks):
                print(f"🎯 POTENTIAL PROJECT DATABASE: {title}")
                print(f"   ID: {db_id}")
                print(f"   URL: {db.get('url', 'N/A')}")
                print(f"   Properties:")
                
                for prop_name, prop_info in properties.items():
                    prop_type = prop_info.get("type", "unknown")
                    print(f"      - {prop_name}: {prop_type}")
                    
                    # Show options for select/status fields
                    if prop_type == "select":
                        options = prop_info.get("select", {}).get("options", [])
                        if options:
                            print(f"         Options: {[opt['name'] + ' (' + opt.get('color', 'no color') + ')' for opt in options]}")
                    elif prop_type == "status":
                        options = prop_info.get("status", {}).get("options", [])
                        if options:
                            print(f"         Options: {[opt['name'] + ' (' + opt.get('color', 'no color') + ')' for opt in options]}")
                    elif prop_type == "relation":
                        database_id = prop_info.get("relation", {}).get("database_id")
                        if database_id:
                            print(f"         Relates to database: {database_id}")
                
                print(f"\n   ✨ Key indicators:")
                print(f"      Has Status with colors: {has_status_with_colors} ({status_prop_name})")
                print(f"      Has Person: {has_person} ({person_prop_name})")
                print(f"      Has Relation to tasks: {has_relation_to_tasks}")
                
                # Fetch sample data
                try:
                    pages_response = await notion.databases.query(database_id=db_id, page_size=5)
                    pages = pages_response.get("results", [])
                    
                    if pages:
                        print(f"\n      📄 Sample data from {len(pages)} projects:")
                        for i, page in enumerate(pages, 1):
                            print(f"\n      Project {i}:")
                            page_props = page.get("properties", {})
                            
                            # Print all properties
                            for prop_name, prop_value in page_props.items():
                                prop_type = prop_value.get("type")
                                
                                if prop_type == "title":
                                    title_text = "".join([t["plain_text"] for t in prop_value.get("title", [])])
                                    print(f"         {prop_name}: {title_text}")
                                elif prop_type == "status":
                                    status = prop_value.get("status", {})
                                    if status:
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
                                        print(f"         {prop_name}: {text[:100]}")
                                elif prop_type == "relation":
                                    relations = prop_value.get("relation", [])
                                    print(f"         {prop_name}: {len(relations)} related items")
                except Exception as e:
                    print(f"      ⚠️  Could not fetch sample data: {e}")
                
                print("\n" + "="*100 + "\n")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(find_projects_database())
