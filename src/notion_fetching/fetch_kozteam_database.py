import asyncio
from notion_client import AsyncClient
import os
from dotenv import load_dotenv

load_dotenv()

async def fetch_database():
    notion = AsyncClient(auth=os.getenv('NOTION_API_KEY'))
    
    # Get database info
    database_id = '1c33b84f1fac80e78028e7d1713b96d1'
    db = await notion.databases.retrieve(database_id=database_id)
    
    print(f'\n📊 Database: {db["title"][0]["plain_text"]}')
    print(f'ID: {database_id}\n')
    
    print('Properties:')
    for prop_name, prop_data in db['properties'].items():
        prop_type = prop_data['type']
        print(f'  - {prop_name}: {prop_type}', end='')
        
        if prop_type == 'select' and 'select' in prop_data:
            options = [opt['name'] for opt in prop_data['select'].get('options', [])]
            print(f' {options}')
        elif prop_type == 'multi_select' and 'multi_select' in prop_data:
            options = [opt['name'] for opt in prop_data['multi_select'].get('options', [])]
            print(f' {options}')
        elif prop_type == 'status' and 'status' in prop_data:
            options = [opt['name'] for opt in prop_data['status'].get('options', [])]
            print(f' {options}')
        else:
            print()
    
    # Get some sample pages
    print('\nSample data (first 5 pages):')
    response = await notion.databases.query(
        database_id=database_id,
        page_size=5
    )
    
    for i, page in enumerate(response['results'], 1):
        print(f'\n{i}. Page:')
        page_id = page['id']
        member_name = None

        # Get member properties
        for prop_name, prop_data in page['properties'].items():
            prop_type = prop_data['type']
            value = None

            if prop_type == 'title':
                value = prop_data['title'][0]['plain_text'] if prop_data['title'] else None
                if prop_name == 'Name':
                    member_name = value
            elif prop_type == 'rich_text':
                value = prop_data['rich_text'][0]['plain_text'] if prop_data['rich_text'] else None
            elif prop_type == 'select':
                value = prop_data['select']['name'] if prop_data['select'] else None
            elif prop_type == 'multi_select':
                value = [opt['name'] for opt in prop_data['multi_select']]
            elif prop_type == 'people':
                value = [p.get('name', 'Unknown') for p in prop_data['people']]
            elif prop_type == 'date':
                value = prop_data['date']['start'] if prop_data['date'] else None
            elif prop_type == 'status':
                value = prop_data['status']['name'] if prop_data['status'] else None
            elif prop_type == 'relation':
                value = f"{len(prop_data['relation'])} related items"

            if value:
                print(f'   {prop_name}: {value}')

        # Fetch child blocks (tasks) from this member's Kanban desk
        print(f'\n   📋 Fetching tasks for {member_name}...')
        try:
            blocks_response = await notion.blocks.children.list(block_id=page_id, page_size=10)

            if blocks_response['results']:
                print(f'   Found {len(blocks_response["results"])} child blocks')

                # Get first task as sample
                for block in blocks_response['results'][:1]:
                    block_type = block['type']
                    print(f'\n   Sample Task Block:')
                    print(f'     Type: {block_type}')
                    print(f'     ID: {block["id"]}')

                    # Try to extract task content
                    if block_type == 'child_database':
                        print(f'     ✅ Found child database (Kanban board)')
                        child_db_id = block['id']

                        # Query the child database for tasks
                        tasks_response = await notion.databases.query(
                            database_id=child_db_id,
                            page_size=3
                        )

                        print(f'     Tasks in database: {len(tasks_response["results"])}')

                        # Show first task
                        if tasks_response['results']:
                            task = tasks_response['results'][0]
                            print(f'\n     🎯 Sample Task:')
                            for task_prop_name, task_prop_data in task['properties'].items():
                                task_prop_type = task_prop_data['type']
                                task_value = None

                                if task_prop_type == 'title':
                                    task_value = task_prop_data['title'][0]['plain_text'] if task_prop_data['title'] else None
                                elif task_prop_type == 'rich_text':
                                    task_value = task_prop_data['rich_text'][0]['plain_text'] if task_prop_data['rich_text'] else None
                                elif task_prop_type == 'select':
                                    task_value = task_prop_data['select']['name'] if task_prop_data['select'] else None
                                elif task_prop_type == 'status':
                                    task_value = task_prop_data['status']['name'] if task_prop_data['status'] else None
                                elif task_prop_type == 'date':
                                    task_value = task_prop_data['date']['start'] if task_prop_data['date'] else None
                                elif task_prop_type == 'relation':
                                    task_value = f"{len(task_prop_data['relation'])} relations"

                                if task_value:
                                    print(f'        {task_prop_name}: {task_value}')

                    elif block_type in ['paragraph', 'heading_1', 'heading_2', 'heading_3']:
                        text_key = block_type
                        if text_key in block and 'rich_text' in block[text_key]:
                            text = ' '.join([t['plain_text'] for t in block[text_key]['rich_text']])
                            print(f'     Content: {text}')

                    elif block_type == 'to_do':
                        checked = block['to_do'].get('checked', False)
                        text = ' '.join([t['plain_text'] for t in block['to_do']['rich_text']])
                        print(f'     To-do: [{["✗", "✓"][checked]}] {text}')
            else:
                print(f'   No child blocks found')

        except Exception as e:
            print(f'   Error fetching blocks: {str(e)}')

asyncio.run(fetch_database())
