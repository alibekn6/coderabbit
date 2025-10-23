import asyncio
from notion_client import AsyncClient
import os
from dotenv import load_dotenv
from datetime import datetime, date
from typing import List, Dict, Any

load_dotenv()


async def fetch_all_member_tasks():
    """
    Fetch all tasks from all team members' Kanban desks in KOZ TEAM database.
    Returns structured data with member info and their tasks.
    """
    notion = AsyncClient(auth=os.getenv('NOTION_API_KEY'))

    # KOZ TEAM database ID
    database_id = '1c33b84f1fac80e78028e7d1713b96d1'

    all_members_data = []

    # Get all team members
    response = await notion.databases.query(database_id=database_id)

    print(f'📊 Found {len(response["results"])} team members\n')

    for page in response['results']:
        page_id = page['id']

        # Extract member info
        member_info = {
            'name': None,
            'position': None,
            'status': None,
            'tg_id': None,
            'start_date': None,
            'tasks': []
        }

        # Parse member properties
        for prop_name, prop_data in page['properties'].items():
            prop_type = prop_data['type']

            if prop_type == 'title' and prop_name == 'Name':
                member_info['name'] = prop_data['title'][0]['plain_text'] if prop_data['title'] else None
            elif prop_type == 'rich_text' and prop_name == 'Position':
                member_info['position'] = prop_data['rich_text'][0]['plain_text'] if prop_data['rich_text'] else None
            elif prop_type == 'status' and prop_name == 'Status':
                member_info['status'] = prop_data['status']['name'] if prop_data['status'] else None
            elif prop_type == 'rich_text' and prop_name == 'tg_id':
                member_info['tg_id'] = prop_data['rich_text'][0]['plain_text'] if prop_data['rich_text'] else None
            elif prop_type == 'date' and prop_name == 'Start Date':
                member_info['start_date'] = prop_data['date']['start'] if prop_data['date'] else None

        # Fetch child blocks to find Kanban board
        try:
            blocks_response = await notion.blocks.children.list(block_id=page_id)

            for block in blocks_response['results']:
                if block['type'] == 'child_database':
                    # Found the Kanban board database
                    child_db_id = block['id']

                    # Query all tasks from this Kanban board
                    tasks_response = await notion.databases.query(
                        database_id=child_db_id,
                        page_size=100  # Adjust as needed
                    )

                    # Parse each task
                    for task in tasks_response['results']:
                        task_data = {
                            'id': task['id'],
                            'name': None,
                            'status': None,
                            'deadline': None,
                            'date_done': None,
                            'project': None,
                            'is_overdue': False,
                            'url': task['url']
                        }

                        # Parse task properties
                        for task_prop_name, task_prop_data in task['properties'].items():
                            task_prop_type = task_prop_data['type']

                            if task_prop_type == 'title' and task_prop_name == 'Name':
                                task_data['name'] = task_prop_data['title'][0]['plain_text'] if task_prop_data['title'] else None
                            elif task_prop_type == 'status' and task_prop_name == 'Status':
                                task_data['status'] = task_prop_data['status']['name'] if task_prop_data['status'] else None
                            elif task_prop_type == 'date' and task_prop_name == 'Deadline':
                                task_data['deadline'] = task_prop_data['date']['start'] if task_prop_data['date'] else None
                            elif task_prop_type == 'date' and task_prop_name == 'Date Done':
                                task_data['date_done'] = task_prop_data['date']['start'] if task_prop_data['date'] else None
                            elif task_prop_type == 'relation' and task_prop_name == 'Project':
                                if task_prop_data['relation']:
                                    # We have project relations, could fetch project names later
                                    task_data['project'] = [rel['id'] for rel in task_prop_data['relation']]

                        # Check if task is overdue
                        if task_data['deadline'] and task_data['status'] not in ['Done', 'Cancelled']:
                            deadline_date = datetime.fromisoformat(task_data['deadline'].replace('Z', '+00:00')).date()
                            today = date.today()
                            if deadline_date < today:
                                task_data['is_overdue'] = True

                        member_info['tasks'].append(task_data)

        except Exception as e:
            print(f'⚠️  Error fetching tasks for {member_info["name"]}: {str(e)}')

        all_members_data.append(member_info)

    return all_members_data


async def display_member_tasks(members_data: List[Dict[str, Any]]):
    """Display tasks in a readable format"""

    for member in members_data:
        print(f'\n{"="*60}')
        print(f'👤 {member["name"]} - {member["position"]}')
        print(f'   Status: {member["status"]}')

        if not member['tasks']:
            print(f'   📭 No tasks found')
            continue

        print(f'   📋 Total Tasks: {len(member["tasks"])}')

        # Count by status
        status_counts = {}
        overdue_count = 0

        for task in member['tasks']:
            status = task['status'] or 'No Status'
            status_counts[status] = status_counts.get(status, 0) + 1
            if task['is_overdue']:
                overdue_count += 1

        print(f'   📊 By Status: {status_counts}')
        if overdue_count > 0:
            print(f'   ⚠️  Overdue Tasks: {overdue_count}')

        # Show sample tasks
        print(f'\n   Sample Tasks:')
        for task in member['tasks'][:3]:
            overdue_marker = '🔴 OVERDUE' if task['is_overdue'] else ''
            print(f'   - [{task["status"]}] {task["name"]} {overdue_marker}')
            if task['deadline']:
                print(f'     Deadline: {task["deadline"]}')


async def get_overdue_tasks(members_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get all overdue tasks across all members"""
    overdue_tasks = []

    for member in members_data:
        for task in member['tasks']:
            if task['is_overdue']:
                overdue_tasks.append({
                    'member_name': member['name'],
                    'member_position': member['position'],
                    'task_name': task['name'],
                    'deadline': task['deadline'],
                    'status': task['status'],
                    'url': task['url']
                })

    return overdue_tasks


async def main():
    print('🚀 Fetching all team member tasks from KOZ TEAM...\n')

    # Fetch all data
    members_data = await fetch_all_member_tasks()

    # Display summary
    await display_member_tasks(members_data)

    # Show overdue tasks
    overdue_tasks = await get_overdue_tasks(members_data)

    if overdue_tasks:
        print(f'\n{"="*60}')
        print(f'🔴 ALL OVERDUE TASKS ({len(overdue_tasks)})')
        print(f'{"="*60}')

        for task in overdue_tasks:
            print(f'\n👤 {task["member_name"]} ({task["member_position"]})')
            print(f'   Task: {task["task_name"]}')
            print(f'   Deadline: {task["deadline"]}')
            print(f'   Status: {task["status"]}')

    print(f'\n✅ Done!')


if __name__ == '__main__':
    asyncio.run(main())
