from src.clients.notion_client import NotionClient
from src.models.notion import (
    NotionTask,
    TaskProperties,
    NotionTasksResponse,
    NotionProject,
    ProjectProperties,
    NotionProjectsResponse,
    ProjectStatusSummary,
    ProjectStatsResponse,
    MemberInfo,
    TodoProperties,
    NotionTodo,
    MemberWithTodos,
    TodosByMemberResponse,
    OverdueTodo,
    OverdueTodosResponse,
    TodoStatistics,
)
from src.core.config import settings
from src.core.logging import get_logger
from datetime import datetime, date
from typing import Optional

logger = get_logger(__name__)


class NotionService:
    # Name mapping from KozTeam database names to Kanban task names
    # This handles cases where members use different name formats across databases
    MEMBER_NAME_MAPPING = {
        # KozTeam name: [possible Kanban names]
        "Adilov Amir": ["Адилов Амир", "Adilov Amir"],
        "Dias": ["Dias Yerlan", "Dias"],
        "Kainazarov Zhassulan": ["Zhasulan Kainazarov", "Zhassulan Kainazarov", "Kainazarov Zhassulan"],
        "Melsov Yernur": ["Ернур Мэлсов", "Yernur Melsov", "Melsov Yernur"],
        "Nabi S.": ["nabi satybaldin", "Nabi S.", "Nabi"],
        "Shakman Madina": ["Мадина Шакман", "Madina Shakman", "Shakman Madina"],
        "Альмухамед": ["Almukhamed Amitov", "Альмухамед"],
        "Асанали": ["Assanali", "Асанали"],
        "Дамир Какаров": ["Damir Kakarov", "Дамир Какаров"],
        "Ермухамед": ["Yermukhamed Kuatov", "Ермухамед"],
        "Ернур Касым": ["Yernur K", "Ернур Касым"],
        "Жибек K. A.": ["Zhibek Kazbek", "Жибек K. A."],
        ".Жаксиликов Райымбек": [".Zhaxilikov Raiymbek", "Zhaxilikov Raiymbek", ".Жаксиликов Райымбек", "Жаксиликов Райымбек"],
        # Add remaining members that already match well
        "Aibar": ["Aibar Kairat", "Aibar"],
        "Ait Aiym": ["Aiym Ait", "Ait Aiym"],
        "Alibek": ["Alibek Anuarbek", "Alibek"],
    }

    def __init__(self):
        self.client = NotionClient()

    async def get_all_tasks(self) -> NotionTasksResponse:
        """Get all tasks from the Notion database"""
        result = await self.client.test_connection()
        tasks = []

        for page in result.get("results", []):
            task = self._parse_task_from_page(page)
            tasks.append(task)

        return NotionTasksResponse(
            total_count=len(tasks),
            tasks=tasks
        )

    async def query_tasks(self, status: str = None, priority: str = None) -> NotionTasksResponse:
        """Query tasks with filters"""
        filters = {}
        
        if status:
            filters["property"] = "Status"
            filters["status"] = {"equals": status}
        
        if priority:
            filters["property"] = "Priority"
            filters["select"] = {"equals": priority}

        result = await self.client.query_database(
            database_id=settings.NOTION_DATABASE_ID,
            filter_params=filters if filters else None
        )
        
        tasks = []
        for page in result.get("results", []):
            task = self._parse_task_from_page(page)
            tasks.append(task)

        return NotionTasksResponse(
            total_count=len(tasks),
            tasks=tasks
        )

    def _parse_task_from_page(self, page: dict) -> NotionTask:
        """Parse a Notion page into a NotionTask object"""
        properties = page.get("properties", {})
        
        task_name = ""
        if "Task name" in properties:
            title_texts = properties["Task name"].get("title", [])
            task_name = "".join([t.get("plain_text", "") for t in title_texts])

        status = None
        if "Status" in properties:
            status_data = properties["Status"].get("status")
            status = status_data.get("name") if status_data else None

        priority = None
        if "Priority" in properties:
            priority_data = properties["Priority"].get("select")
            priority = priority_data.get("name") if priority_data else None

        effort_level = None
        if "Effort level" in properties:
            effort_data = properties["Effort level"].get("select")
            effort_level = effort_data.get("name") if effort_data else None

        description = None
        if "Description" in properties:
            desc_texts = properties["Description"].get("rich_text", [])
            description = "".join([t.get("plain_text", "") for t in desc_texts])

        due_date = None
        if "Due date" in properties:
            date_data = properties["Due date"].get("date")
            if date_data:
                due_date = date_data.get("start")

        task_type = []
        if "Task type" in properties:
            type_options = properties["Task type"].get("multi_select", [])
            task_type = [opt.get("name") for opt in type_options]

        assignee = []
        if "Assignee" in properties:
            people = properties["Assignee"].get("people", [])
            assignee = [p.get("name", p.get("id")) for p in people]

        task_properties = TaskProperties(
            task_name=task_name,
            status=status,
            priority=priority,
            effort_level=effort_level,
            description=description,
            due_date=due_date,
            task_type=task_type,
            assignee=assignee
        )

        return NotionTask(
            page_id=page["id"],
            created_time=page["created_time"],
            last_edited_time=page["last_edited_time"],
            properties=task_properties
        )

    async def get_all_projects(self) -> NotionProjectsResponse:
        """Get all projects from the Notion Projects database"""
        logger.info("fetching_all_projects", database_id=settings.NOTION_DATABASE_ID)

        try:
            has_more = True
            start_cursor = None
            all_pages = []

            while has_more:
                query_params = {"page_size": 100}
                if start_cursor:
                    query_params["start_cursor"] = start_cursor

                result = await self.client.query_database(
                    database_id=settings.NOTION_DATABASE_ID,
                    filter_params=None,
                    **query_params
                )

                all_pages.extend(result.get("results", []))
                has_more = result.get("has_more", False)
                start_cursor = result.get("next_cursor")

            # Parse projects
            projects = []
            for page in all_pages:
                project = self._parse_project_from_page(page)
                projects.append(project)

            logger.info("projects_fetched", count=len(projects))

            return NotionProjectsResponse(
                total_count=len(projects),
                projects=projects
            )

        except Exception as e:
            logger.error("error_fetching_projects", error=str(e))
            raise

    async def get_projects_by_health(
        self, health_color: str
    ) -> NotionProjectsResponse:
        """
        Get projects filtered by health status color (red, yellow, green)

        Args:
            health_color: The health status color ('red', 'yellow', 'green')

        Returns:
            NotionProjectsResponse with filtered projects
        """
        logger.info("fetching_projects_by_health", health_color=health_color)

        try:
            filters = {
                "property": "Health",
                "select": {"equals": health_color.capitalize()}
            }

            result = await self.client.query_database(
                database_id=settings.NOTION_DATABASE_ID,
                filter_params=filters
            )

            projects = []
            for page in result.get("results", []):
                project = self._parse_project_from_page(page)
                projects.append(project)

            logger.info(
                "projects_filtered_by_health",
                health_color=health_color,
                count=len(projects)
            )

            return NotionProjectsResponse(
                total_count=len(projects),
                projects=projects
            )

        except Exception as e:
            logger.error("error_filtering_projects_by_health", error=str(e))
            raise

    async def get_project_statistics(self) -> ProjectStatsResponse:
        """
        Get project statistics including counts by health status and assignee

        Returns:
            ProjectStatsResponse with aggregated statistics
        """
        logger.info("calculating_project_statistics")

        try:
            all_projects = await self.get_all_projects()

            status_counts = {"red": 0, "yellow": 0, "green": 0, "not_set": 0}
            assignee_counts = {}

            for project in all_projects.projects:
                health_color = project.properties.health_color
                if health_color == "red":
                    status_counts["red"] += 1
                elif health_color == "yellow":
                    status_counts["yellow"] += 1
                elif health_color == "green":
                    status_counts["green"] += 1
                else:
                    status_counts["not_set"] += 1

                # Count by assignee
                for assignee in project.properties.assignees:
                    assignee_counts[assignee] = assignee_counts.get(assignee, 0) + 1

            status_summary = ProjectStatusSummary(
                red=status_counts["red"],
                yellow=status_counts["yellow"],
                green=status_counts["green"],
                not_set=status_counts["not_set"]
            )

            logger.info(
                "project_statistics_calculated",
                total=all_projects.total_count,
                red=status_counts["red"],
                yellow=status_counts["yellow"],
                green=status_counts["green"]
            )

            return ProjectStatsResponse(
                total_projects=all_projects.total_count,
                status_summary=status_summary,
                projects_by_assignee=assignee_counts
            )

        except Exception as e:
            logger.error("error_calculating_project_statistics", error=str(e))
            raise

    def _parse_project_from_page(self, page: dict) -> NotionProject:
        """Parse a Notion page into a NotionProject object"""
        properties = page.get("properties", {})

        project_name = ""
        if "Project name" in properties:
            title_texts = properties["Project name"].get("title", [])
            project_name = "".join([t.get("plain_text", "") for t in title_texts])

        health_status = None
        health_color = None
        if "Health" in properties:
            health_data = properties["Health"].get("select")
            if health_data:
                health_status = health_data.get("name")
                health_color = health_data.get("color")


        status = None
        if "Status" in properties:
            status_data = properties["Status"].get("status")
            if status_data:
                status = status_data.get("name")


        priority = None
        priority_color = None
        if "Priority" in properties:
            priority_data = properties["Priority"].get("select")
            if priority_data:
                priority = priority_data.get("name")
                priority_color = priority_data.get("color")

        assignees = []
        if "Assignee" in properties:
            people = properties["Assignee"].get("people", [])
            assignees = [
                p.get("name", p.get("id", "Unknown")) for p in people
            ]
            if not assignees:
                assignees = ["Unassigned"]
        else:
            assignees = ["Unassigned"]


        task_count = 0
        if "Task Count" in properties:
            rollup_data = properties["Task Count"].get("rollup")
            if rollup_data:
                task_count = rollup_data.get("number", 0) or 0

        project_properties = ProjectProperties(
            project_name=project_name or "Untitled",
            health_status=health_status,
            health_color=health_color,
            status=status,
            priority=priority,
            priority_color=priority_color,
            assignees=assignees,
            task_count=int(task_count)
        )

        return NotionProject(
            page_id=page["id"],
            created_time=page["created_time"],
            last_edited_time=page["last_edited_time"],
            url=page.get("url", ""),
            properties=project_properties
        )

    async def get_all_member_todos(
        self, status_filter: Optional[str] = None
    ) -> TodosByMemberResponse:
        """
        Get todos for all team members from the centralized Kanban board
        
        OPTIMIZED: By default, only fetches To-do and In-progress tasks (not completed tasks)
        for faster performance.

        Args:
            status_filter: Optional status to filter todos (e.g., 'To-do', 'In-progress', 'Done')
                          If None, fetches only To-do and In-progress tasks

        Returns:
            TodosByMemberResponse with all members and their todos
        """
        logger.info(
            "fetching_all_member_todos", 
            status_filter=status_filter,
            note="Only fetching active tasks (To-do, In-progress) by default for performance"
        )

        try:
            koz_team_db_id = "1c33b84f1fac80e78028e7d1713b96d1"

            result = await self.client.query_database(
                database_id=koz_team_db_id,
                filter_params=None
            )

            members_with_todos = []
            members_with_tasks_count = 0

            for page in result.get("results", []):
                member_data = await self._fetch_member_with_todos(
                    page, status_filter
                )

                if member_data.total_tasks > 0:
                    members_with_tasks_count += 1

                members_with_todos.append(member_data)

            logger.info(
                "member_todos_fetched",
                total_members=len(members_with_todos),
                members_with_tasks=members_with_tasks_count
            )

            return TodosByMemberResponse(
                total_members=len(members_with_todos),
                members_with_tasks=members_with_tasks_count,
                members=members_with_todos
            )

        except Exception as e:
            logger.error("error_fetching_member_todos", error=str(e))
            raise

    async def get_member_todos_by_name(
        self, member_name: str, status_filter: Optional[str] = None
    ) -> MemberWithTodos:
        """
        Get todos for a specific team member by name

        Args:
            member_name: Name of the team member
            status_filter: Optional status to filter todos

        Returns:
            MemberWithTodos for the specified member
        """
        logger.info(
            "fetching_member_todos_by_name",
            member_name=member_name,
            status_filter=status_filter
        )

        try:
            koz_team_db_id = "1c33b84f1fac80e78028e7d1713b96d1"

            # Query for specific member by name
            filters = {
                "property": "Name",
                "title": {"contains": member_name}
            }

            result = await self.client.query_database(
                database_id=koz_team_db_id,
                filter_params=filters
            )

            if not result.get("results"):
                raise ValueError(f"Member '{member_name}' not found")

            # Get first matching member
            page = result["results"][0]
            member_data = await self._fetch_member_with_todos(page, status_filter)

            logger.info(
                "member_todos_fetched_by_name",
                member_name=member_name,
                total_tasks=member_data.total_tasks
            )

            return member_data

        except Exception as e:
            logger.error(
                "error_fetching_member_todos_by_name",
                member_name=member_name,
                error=str(e)
            )
            raise

    async def get_overdue_todos(self) -> OverdueTodosResponse:
        """
        Get all overdue todos across all team members

        Returns:
            OverdueTodosResponse with all overdue todos
        """
        logger.info("fetching_overdue_todos")

        try:
            all_members = await self.get_all_member_todos()
            overdue_todos = []

            for member_with_todos in all_members.members:
                for todo in member_with_todos.todos:
                    if todo.properties.is_overdue:
                        overdue_todos.append(
                            OverdueTodo(
                                member_name=member_with_todos.member.name,
                                member_position=member_with_todos.member.position,
                                todo=todo
                            )
                        )

            logger.info("overdue_todos_fetched", total_overdue=len(overdue_todos))

            return OverdueTodosResponse(
                total_overdue=len(overdue_todos),
                overdue_todos=overdue_todos
            )

        except Exception as e:
            logger.error("error_fetching_overdue_todos", error=str(e))
            raise

    async def get_todo_statistics(self) -> TodoStatistics:
        """
        Get aggregated statistics about todos across all members

        Returns:
            TodoStatistics with aggregated data
        """
        logger.info("calculating_todo_statistics")

        try:
            all_members = await self.get_all_member_todos()

            total_todos = 0
            status_counts = {}
            overdue_by_member = {}
            members_without_tasks = 0

            for member_with_todos in all_members.members:
                total_todos += member_with_todos.total_tasks

                # Aggregate status counts
                for status, count in member_with_todos.tasks_by_status.items():
                    status_counts[status] = status_counts.get(status, 0) + count

                # Track overdue by member
                if member_with_todos.overdue_count > 0:
                    overdue_by_member[member_with_todos.member.name] = (
                        member_with_todos.overdue_count
                    )

                # Count members without tasks
                if member_with_todos.total_tasks == 0:
                    members_without_tasks += 1

            total_overdue = sum(overdue_by_member.values())

            logger.info(
                "todo_statistics_calculated",
                total_members=all_members.total_members,
                total_todos=total_todos,
                total_overdue=total_overdue
            )

            return TodoStatistics(
                total_members=all_members.total_members,
                members_with_tasks=all_members.members_with_tasks,
                members_without_tasks=members_without_tasks,
                total_todos=total_todos,
                todos_by_status=status_counts,
                total_overdue=total_overdue,
                overdue_by_member=overdue_by_member
            )

        except Exception as e:
            logger.error("error_calculating_todo_statistics", error=str(e))
            raise

    async def _fetch_member_with_todos(
        self, page: dict, status_filter: Optional[str] = None
    ) -> MemberWithTodos:
        """
        Internal method to fetch a member's todos from the centralized Kanban board
        
        OPTIMIZED: Only fetches To-do and In-progress tasks to improve performance.
        Filters by member name and status in the Notion API query itself.

        Args:
            page: The Notion page representing the team member
            status_filter: Optional status to filter todos (if None, fetches To-do and In-progress)

        Returns:
            MemberWithTodos with member info and their todos
        """
        properties = page.get("properties", {})

        # Parse member info
        member_info = self._parse_member_info(properties)

        # Initialize todos list
        todos = []

        try:
            # Use the centralized Kanban board database
            # This is the correct database that contains ALL members' tasks
            centralized_kanban_id = "1c33b84f-1fac-8055-a0f3-e192311652ab"

            # OPTIMIZATION: Only fetch To-do and In-progress tasks by default
            # This dramatically reduces the amount of data fetched (no completed tasks)
            
            if status_filter:
                # If specific status requested, fetch only that
                statuses_to_fetch = [status_filter]
            else:
                # By default, only fetch active tasks (not Done/Cancelled)
                statuses_to_fetch = ["To-do", "In-progress"]
            
            # Fetch tasks for each status
            for status in statuses_to_fetch:
                has_more = True
                start_cursor = None

                while has_more:
                    query_params = {"page_size": 100}
                    if start_cursor:
                        query_params["start_cursor"] = start_cursor

                    # Filter by status in the API query
                    filter_params = {
                        "property": "Status",
                        "status": {"equals": status}
                    }

                    todos_result = await self.client.query_database(
                        database_id=centralized_kanban_id,
                        filter_params=filter_params,
                        **query_params
                    )

                    # Filter for this specific member in the results
                    # Check both "Person" and "Assign" properties
                    for todo_page in todos_result.get("results", []):
                        todo_props = todo_page.get("properties", {})
                        is_assigned_to_member = False

                        # Check Person property
                        # Use flexible matching to handle:
                        # - Case differences: "Nabi S." vs "nabi satybaldin"
                        # - Name order: "Kainazarov Zhassulan" vs "Zhasulan Kainazarov"
                        # - Partial names: "Alibek" vs "Alibek Anuarbek"
                        if "Person" in todo_props:
                            people_list = todo_props["Person"].get("people", [])
                            for person in people_list:
                                person_name = person.get("name", "")
                                if self._names_match(member_info.name, person_name):
                                    is_assigned_to_member = True
                                    break

                        # Check Assign property
                        if not is_assigned_to_member and "Assign" in todo_props:
                            assign_list = todo_props["Assign"].get("people", [])
                            for person in assign_list:
                                person_name = person.get("name", "")
                                if self._names_match(member_info.name, person_name):
                                    is_assigned_to_member = True
                                    break

                        # If task is assigned to this member, parse and add it
                        if is_assigned_to_member:
                            todo = self._parse_todo_from_page(todo_page)
                            todos.append(todo)

                    has_more = todos_result.get("has_more", False)
                    start_cursor = todos_result.get("next_cursor")

        except Exception as e:
            logger.warning(
                "error_fetching_member_todos",
                member_name=member_info.name,
                error=str(e)
            )

        # Calculate statistics
        status_counts = {}
        overdue_count = 0

        for todo in todos:
            status = todo.properties.status or "No Status"
            status_counts[status] = status_counts.get(status, 0) + 1
            if todo.properties.is_overdue:
                overdue_count += 1

        return MemberWithTodos(
            member=member_info,
            total_tasks=len(todos),
            tasks_by_status=status_counts,
            overdue_count=overdue_count,
            todos=todos
        )

    def _names_match(self, member_name: str, person_name: str) -> bool:
        """
        Match member names using hardcoded mapping + flexible fallback

        First checks the MEMBER_NAME_MAPPING for exact matches, then falls back
        to flexible matching for cases not in the mapping.

        Args:
            member_name: Name from KozTeam database
            person_name: Name from task assignment

        Returns:
            True if names match, False otherwise
        """
        if not member_name or not person_name:
            return False

        # PRIORITY 1: Check hardcoded mapping first
        if member_name in self.MEMBER_NAME_MAPPING:
            # Case-insensitive comparison with mapped names
            person_lower = person_name.lower().strip()
            for mapped_name in self.MEMBER_NAME_MAPPING[member_name]:
                if person_lower == mapped_name.lower().strip():
                    return True

        # PRIORITY 2: Exact match after normalization
        member_lower = member_name.lower().strip().lstrip('.')
        person_lower = person_name.lower().strip().lstrip('.')

        if member_lower == person_lower:
            return True

        # PRIORITY 3: Bidirectional substring match (for names not in mapping)
        if member_lower in person_lower or person_lower in member_lower:
            return True

        # PRIORITY 4: Split names into parts and check for common parts
        # This handles name order differences for unmapped names
        member_parts = set(member_lower.replace('.', ' ').split())
        person_parts = set(person_lower.replace('.', ' ').split())

        # Remove very short parts (like initials) as they can cause false matches
        member_parts = {p for p in member_parts if len(p) > 2}
        person_parts = {p for p in person_parts if len(p) > 2}

        # If we have at least 1 significant name part in common, consider it a match
        common_parts = member_parts & person_parts
        if common_parts:
            if any(len(part) >= 3 for part in common_parts):
                return True

        # PRIORITY 5: Check if any member part is contained in any person part
        for m_part in member_parts:
            if len(m_part) >= 3:  # Only check significant parts
                for p_part in person_parts:
                    if len(p_part) >= 3:
                        if m_part in p_part or p_part in m_part:
                            return True

        return False

    def _parse_member_info(self, properties: dict) -> MemberInfo:
        """Parse member information from page properties"""
        name = None
        if "Name" in properties:
            title_texts = properties["Name"].get("title", [])
            name = "".join([t.get("plain_text", "") for t in title_texts])

        position = None
        if "Position" in properties:
            position_texts = properties["Position"].get("rich_text", [])
            position = "".join([t.get("plain_text", "") for t in position_texts])

        status = None
        if "Status" in properties:
            status_data = properties["Status"].get("status")
            status = status_data.get("name") if status_data else None

        tg_id = None
        if "tg_id" in properties:
            tg_id_texts = properties["tg_id"].get("rich_text", [])
            tg_id = "".join([t.get("plain_text", "") for t in tg_id_texts])

        start_date = None
        if "Start Date" in properties:
            date_data = properties["Start Date"].get("date")
            if date_data:
                start_date = date_data.get("start")

        return MemberInfo(
            name=name or "Unknown",
            position=position,
            status=status,
            tg_id=tg_id,
            start_date=start_date
        )

    def _parse_todo_from_page(self, page: dict) -> NotionTodo:
        """Parse a todo from a Notion page"""
        properties = page.get("properties", {})

        # Parse todo properties
        name = None
        if "Name" in properties:
            title_texts = properties["Name"].get("title", [])
            name = "".join([t.get("plain_text", "") for t in title_texts])

        status = None
        if "Status" in properties:
            status_data = properties["Status"].get("status")
            status = status_data.get("name") if status_data else None

        deadline = None
        if "Deadline" in properties:
            date_data = properties["Deadline"].get("date")
            if date_data:
                deadline = date_data.get("start")

        date_done = None
        if "Date Done" in properties:
            date_data = properties["Date Done"].get("date")
            if date_data:
                date_done = date_data.get("start")

        project_ids = []
        if "Project" in properties:
            relations = properties["Project"].get("relation", [])
            project_ids = [rel["id"] for rel in relations]

        # Check if overdue
        is_overdue = False
        if deadline and status not in ["Done", "Cancelled"]:
            try:
                deadline_date = datetime.fromisoformat(
                    deadline.replace("Z", "+00:00")
                ).date()
                today = date.today()
                if deadline_date < today:
                    is_overdue = True
            except Exception:
                pass

        todo_properties = TodoProperties(
            name=name or "Untitled",
            status=status,
            deadline=deadline,
            date_done=date_done,
            is_overdue=is_overdue,
            project_ids=project_ids
        )

        return NotionTodo(
            id=page["id"],
            url=page.get("url", ""),
            properties=todo_properties
        )


notion_service = NotionService()
