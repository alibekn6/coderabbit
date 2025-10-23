import asyncio
from src.clients.notion_client import NotionClient

async def find_kanban_database():
    """
    Search for Kanban board databases with:
    - Assignee/Responsible person field
    - Project/Task name field
    - Status field (especially with red/green/blue or similar)
    """
    client = NotionClient()
    
    print("=" * 80)
    print("🔍 SEARCHING FOR KANBAN BOARD DATABASE")
    print("Looking for: Person field + Status field + Project/Task name")
    print("=" * 80)
    print()
    
    # Search for all databases
    search_results = await client.client.search(
        filter={"property": "object", "value": "database"}
    )
    
    databases = search_results.get("results", [])
    print(f"📊 Found {len(databases)} total databases\n")
    
    kanban_candidates = []
    
    for idx, db in enumerate(databases, 1):
        db_id = db["id"]
        title = db.get("title", [{}])[0].get("plain_text", "Untitled")
        
        # Get full database details
        try:
            db_details = await client.get_database(db_id)
            properties = db_details.get("properties", {})
            
            # Check for Kanban-like structure
            has_person = False
            has_status = False
            has_title = False
            
            person_fields = []
            status_fields = []
            title_field = None
            
            for prop_name, prop_data in properties.items():
                prop_type = prop_data.get("type")
                
                # Check for person/people field
                if prop_type == "people":
                    has_person = True
                    person_fields.append(prop_name)
                
                # Check for status/select field
                if prop_type in ["status", "select"]:
                    has_status = True
                    status_fields.append(prop_name)
                    
                    # Check if it has color-based options
                    if prop_type == "select":
                        options = prop_data.get("select", {}).get("options", [])
                        colors = [opt.get("color") for opt in options]
                        if any(c in ["red", "green", "blue"] for c in colors):
                            status_fields[-1] += " (has red/green/blue colors!)"
                    elif prop_type == "status":
                        groups = prop_data.get("status", {}).get("groups", [])
                        colors = []
                        for group in groups:
                            colors.extend([opt.get("color") for opt in group.get("options", [])])
                        if any(c in ["red", "green", "blue"] for c in colors):
                            status_fields[-1] += " (has red/green/blue colors!)"
                
                # Check for title field
                if prop_type == "title":
                    has_title = True
                    title_field = prop_name
            
            # If it matches Kanban criteria, it's a candidate!
            if has_person and has_status and has_title:
                kanban_candidates.append({
                    "index": idx,
                    "id": db_id,
                    "title": title,
                    "url": db.get("url", ""),
                    "person_fields": person_fields,
                    "status_fields": status_fields,
                    "title_field": title_field,
                    "properties": properties
                })
                
                print("⭐" * 40)
                print(f"🎯 KANBAN CANDIDATE #{len(kanban_candidates)}: {title}")
                print("⭐" * 40)
                print(f"📌 Database ID: {db_id}")
                print(f"🔗 URL: {db.get('url', '')}")
                print(f"\n✅ MATCHES KANBAN CRITERIA:")
                print(f"   👤 Person fields: {', '.join(person_fields)}")
                print(f"   📊 Status fields: {', '.join(status_fields)}")
                print(f"   📝 Title field: {title_field}")
                print(f"\n📊 All Properties ({len(properties)} columns):")
                for prop_name, prop_data in properties.items():
                    prop_type = prop_data.get("type")
                    print(f"   • {prop_name} ({prop_type})")
                
                # Try to get sample data
                try:
                    sample = await client.query_database(db_id, page_size=3)
                    pages = sample.get("results", [])
                    print(f"\n📦 Contains {len(pages)} sample page(s):")
                    
                    for page in pages[:3]:
                        props = page.get("properties", {})
                        
                        # Extract key fields
                        title_val = "N/A"
                        person_val = "N/A"
                        status_val = "N/A"
                        
                        for prop_name, prop_data in props.items():
                            prop_type = prop_data.get("type")
                            
                            if prop_type == "title":
                                title_texts = prop_data.get("title", [])
                                if title_texts:
                                    title_val = title_texts[0].get("plain_text", "N/A")
                            
                            elif prop_type == "people":
                                people_list = prop_data.get("people", [])
                                if people_list:
                                    person_val = people_list[0].get("name", "N/A")
                            
                            elif prop_type in ["status", "select"]:
                                if prop_type == "status":
                                    status_data = prop_data.get("status")
                                    if status_data:
                                        status_val = f"{status_data.get('name', 'N/A')} ({status_data.get('color', '')})"
                                else:
                                    select_data = prop_data.get("select")
                                    if select_data:
                                        status_val = f"{select_data.get('name', 'N/A')} ({select_data.get('color', '')})"
                        
                        print(f"\n      📄 {title_val}")
                        print(f"         👤 Responsible: {person_val}")
                        print(f"         🚦 Status: {status_val}")
                
                except Exception as e:
                    print(f"\n⚠️  Could not fetch sample data: {e}")
                
                print("\n")
        
        except Exception as e:
            print(f"❌ Error processing database #{idx}: {e}")
            continue
    
    print("\n" + "=" * 80)
    print(f"✨ SUMMARY: Found {len(kanban_candidates)} Kanban board candidate(s)")
    print("=" * 80)
    
    if kanban_candidates:
        print("\n🎯 RECOMMENDED DATABASE(S):")
        for i, candidate in enumerate(kanban_candidates, 1):
            print(f"\n{i}. {candidate['title']}")
            print(f"   Database ID: {candidate['id']}")
            print(f"   URL: {candidate['url']}")
            print(f"   Person: {', '.join(candidate['person_fields'])}")
            print(f"   Status: {', '.join(candidate['status_fields'])}")
            print(f"   Title: {candidate['title_field']}")
        
        print("\n" + "=" * 80)
        print("💡 To use a database, add this to your .env file:")
        print(f"   NOTION_DATABASE_ID={kanban_candidates[0]['id']}")
        print("=" * 80)
    else:
        print("\n❌ No Kanban board databases found matching criteria")
        print("   (Looking for: person field + status field + title field)")

if __name__ == "__main__":
    asyncio.run(find_kanban_database())
