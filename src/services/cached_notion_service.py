"""
Cached Notion Service - Returns data from cache instead of calling Notion API directly.
This dramatically improves response times from 3-4 minutes to milliseconds.
"""
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date

from src.repositories.cache_repository import CacheRepository
from src.models.notion import (
    NotionProject,
    ProjectProperties,
    NotionProjectsResponse,
    NotionTask,
    TaskProperties,
    NotionTasksResponse,
    MemberInfo,
    NotionTodo,
    TodoProperties,
    MemberWithTodos,
    TodosByMemberResponse,
    OverdueTodo,
    OverdueTodosResponse,
    TodoStatistics,
    ProjectStatsResponse,
    ProjectStatusSummary,
    EmployeeProject,
    EmployeeWithProjects,
    EmployeesWithProjectsResponse,
)


class CachedNotionService:
    """Service layer that reads Notion data from cache"""

    def __init__(self, db: Session):
        self.cache_repo = CacheRepository(db)

    def get_cache_info(self, cache_type: str) -> dict:
        """Get information about cache freshness"""
        metadata = self.cache_repo.get_cache_metadata(cache_type)
        if not metadata:
            return {
                "cache_type": cache_type,
                "exists": False,
                "message": "Cache not initialized yet"
            }
        
        return {
            "cache_type": cache_type,
            "exists": True,
            "last_updated": metadata.last_updated.isoformat(),
            "total_records": metadata.total_records,
            "update_duration_seconds": metadata.update_duration_seconds,
            "is_updating": metadata.is_updating,
            "error_message": metadata.error_message
        }

    # ============= Projects Operations =============

    def get_all_projects(self) -> NotionProjectsResponse:
        """Get all projects from cache"""
        cached_projects = self.cache_repo.get_all_cached_projects()
        
        # Convert cache models to Pydantic models
        projects = []
        for cached_project in cached_projects:
            project = NotionProject(
                page_id=cached_project.page_id,
                created_time=cached_project.notion_created_time,
                last_edited_time=cached_project.notion_last_edited_time,
                url=cached_project.url,
                properties=ProjectProperties(
                    project_name=cached_project.project_name,
                    health_status=cached_project.health_status,
                    health_color=cached_project.health_color,
                    status=cached_project.status,
                    priority=cached_project.priority,
                    priority_color=cached_project.priority_color,
                    assignees=cached_project.assignees or [],
                    task_count=cached_project.task_count
                )
            )
            projects.append(project)
        
        return NotionProjectsResponse(
            total_count=len(projects),
            projects=projects
        )

    def get_projects_by_health(self, health_color: str) -> NotionProjectsResponse:
        """Get projects filtered by health color"""
        all_projects = self.get_all_projects()
        
        # Filter by health color
        filtered_projects = [
            project for project in all_projects.projects
            if project.properties.health_color == health_color
        ]
        
        return NotionProjectsResponse(
            total_count=len(filtered_projects),
            projects=filtered_projects
        )

    def get_project_statistics(self) -> ProjectStatsResponse:
        """Get project statistics from cache"""
        all_projects = self.get_all_projects()

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

        return ProjectStatsResponse(
            total_projects=all_projects.total_count,
            status_summary=status_summary,
            projects_by_assignee=assignee_counts
        )

    # ============= Tasks Operations =============

    def get_all_tasks(self) -> NotionTasksResponse:
        """Get all tasks from cache"""
        cached_tasks = self.cache_repo.get_all_cached_tasks()
        
        # Convert cache models to Pydantic models
        tasks = []
        for cached_task in cached_tasks:
            task = NotionTask(
                page_id=cached_task.page_id,
                created_time=cached_task.notion_created_time,
                last_edited_time=cached_task.notion_last_edited_time,
                properties=TaskProperties(
                    task_name=cached_task.task_name,
                    status=cached_task.status,
                    priority=cached_task.priority,
                    effort_level=cached_task.effort_level,
                    description=cached_task.description,
                    due_date=cached_task.due_date,
                    task_type=cached_task.task_type or [],
                    assignee=cached_task.assignee or []
                )
            )
            tasks.append(task)
        
        return NotionTasksResponse(
            total_count=len(tasks),
            tasks=tasks
        )

    def query_tasks(self, status: Optional[str] = None, priority: Optional[str] = None) -> NotionTasksResponse:
        """Query tasks with filters from cache"""
        all_tasks = self.get_all_tasks()

        # Filter tasks
        filtered_tasks = all_tasks.tasks
        if status:
            filtered_tasks = [t for t in filtered_tasks if t.properties.status == status]
        if priority:
            filtered_tasks = [t for t in filtered_tasks if t.properties.priority == priority]

        return NotionTasksResponse(
            total_count=len(filtered_tasks),
            tasks=filtered_tasks
        )

    def get_tasks_created_today(self) -> NotionTasksResponse:
        """Get tasks that were created today from cache"""
        all_tasks = self.get_all_tasks()
        today = date.today()

        # Filter tasks created today
        tasks_created_today = [
            task for task in all_tasks.tasks
            if task.created_time.date() == today
        ]

        return NotionTasksResponse(
            total_count=len(tasks_created_today),
            tasks=tasks_created_today
        )

    def get_tasks_completed_today(self) -> NotionTasksResponse:
        """Get tasks that were completed today from cache"""
        cached_tasks = self.cache_repo.get_all_cached_tasks()
        today = date.today()

        # Filter tasks completed today (status = "Done" and last_edited_time is today)
        tasks_completed_today = []
        for cached_task in cached_tasks:
            # A task is considered completed today if:
            # 1. Status is "Done"
            # 2. Last edited time is today (assuming status changed to Done today)
            if (cached_task.status == "Done" and
                cached_task.notion_last_edited_time.date() == today):

                task = NotionTask(
                    page_id=cached_task.page_id,
                    created_time=cached_task.notion_created_time,
                    last_edited_time=cached_task.notion_last_edited_time,
                    properties=TaskProperties(
                        task_name=cached_task.task_name,
                        status=cached_task.status,
                        priority=cached_task.priority,
                        effort_level=cached_task.effort_level,
                        description=cached_task.description,
                        due_date=cached_task.due_date,
                        task_type=cached_task.task_type or [],
                        assignee=cached_task.assignee or []
                    )
                )
                tasks_completed_today.append(task)

        return NotionTasksResponse(
            total_count=len(tasks_completed_today),
            tasks=tasks_completed_today
        )

    # ============= Todos Operations =============

    def get_all_member_todos(self, status_filter: Optional[str] = None) -> TodosByMemberResponse:
        """Get all member todos from cache"""
        cached_todos = self.cache_repo.get_all_cached_todos()
        cached_members = self.cache_repo.get_all_cached_team_members()
        
        # Group todos by member
        member_todos_dict = {}
        for todo in cached_todos:
            # Apply status filter if provided
            if status_filter and todo.status != status_filter:
                continue
            
            if todo.member_name not in member_todos_dict:
                member_todos_dict[todo.member_name] = []
            member_todos_dict[todo.member_name].append(todo)
        
        # Build response
        members_with_todos = []
        members_with_tasks_count = 0
        
        for cached_member in cached_members:
            member_todos = member_todos_dict.get(cached_member.member_name, [])
            
            # Convert todos to Pydantic models
            todos = []
            status_counts = {}
            overdue_count = 0
            
            for cached_todo in member_todos:
                todo = NotionTodo(
                    id=cached_todo.todo_id,
                    url=cached_todo.url,
                    properties=TodoProperties(
                        name=cached_todo.task_name,
                        status=cached_todo.status,
                        deadline=cached_todo.deadline,
                        date_done=cached_todo.date_done,
                        is_overdue=cached_todo.is_overdue,
                        project_ids=cached_todo.project_ids or []
                    )
                )
                todos.append(todo)
                
                # Count stats
                status = cached_todo.status or "No Status"
                status_counts[status] = status_counts.get(status, 0) + 1
                if cached_todo.is_overdue:
                    overdue_count += 1
            
            member_with_todos = MemberWithTodos(
                member=MemberInfo(
                    name=cached_member.member_name,
                    position=cached_member.position,
                    status=cached_member.status,
                    tg_id=cached_member.tg_id,
                    start_date=cached_member.start_date
                ),
                total_tasks=len(todos),
                tasks_by_status=status_counts,
                overdue_count=overdue_count,
                todos=todos
            )
            members_with_todos.append(member_with_todos)
            
            if len(todos) > 0:
                members_with_tasks_count += 1
        
        return TodosByMemberResponse(
            total_members=len(members_with_todos),
            members_with_tasks=members_with_tasks_count,
            members=members_with_todos
        )

    def get_member_todos_by_name(self, member_name: str, status_filter: Optional[str] = None) -> MemberWithTodos:
        """Get todos for a specific member from cache"""
        all_members = self.get_all_member_todos(status_filter)
        
        # Find the specific member
        for member_with_todos in all_members.members:
            if member_with_todos.member.name.lower() == member_name.lower():
                return member_with_todos
        
        raise ValueError(f"Member '{member_name}' not found in cache")

    def get_overdue_todos(self) -> OverdueTodosResponse:
        """Get all overdue todos from cache"""
        cached_todos = self.cache_repo.get_overdue_todos()
        cached_members = {m.member_name: m for m in self.cache_repo.get_all_cached_team_members()}
        
        overdue_todos = []
        for cached_todo in cached_todos:
            member = cached_members.get(cached_todo.member_name)
            
            overdue_todo = OverdueTodo(
                member_name=cached_todo.member_name,
                member_position=member.position if member else None,
                todo=NotionTodo(
                    id=cached_todo.todo_id,
                    url=cached_todo.url,
                    properties=TodoProperties(
                        name=cached_todo.task_name,
                        status=cached_todo.status,
                        deadline=cached_todo.deadline,
                        date_done=cached_todo.date_done,
                        is_overdue=True,
                        project_ids=cached_todo.project_ids or []
                    )
                )
            )
            overdue_todos.append(overdue_todo)
        
        return OverdueTodosResponse(
            total_overdue=len(overdue_todos),
            overdue_todos=overdue_todos
        )

    def get_todo_statistics(self) -> TodoStatistics:
        """Get todo statistics from cache"""
        all_members = self.get_all_member_todos()

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

        return TodoStatistics(
            total_members=all_members.total_members,
            members_with_tasks=all_members.members_with_tasks,
            members_without_tasks=members_without_tasks,
            total_todos=total_todos,
            todos_by_status=status_counts,
            total_overdue=total_overdue,
            overdue_by_member=overdue_by_member
        )

    # ============= Employees with Projects Operations =============

    def get_all_employees_with_projects(self) -> EmployeesWithProjectsResponse:
        """Get all employees with their assigned projects from cache"""
        cached_projects = self.cache_repo.get_all_cached_projects()
        
        # Group projects by assignee
        employee_projects_dict = {}
        
        for cached_project in cached_projects:
            # Each project can have multiple assignees
            assignees = cached_project.assignees or []
            
            for assignee in assignees:
                if assignee not in employee_projects_dict:
                    employee_projects_dict[assignee] = []
                
                # Create EmployeeProject object
                employee_project = EmployeeProject(
                    page_id=cached_project.page_id,
                    project_name=cached_project.project_name,
                    status=cached_project.status,
                    health_status=cached_project.health_status,
                    health_color=cached_project.health_color,
                    priority=cached_project.priority,
                    priority_color=cached_project.priority_color,
                    task_count=cached_project.task_count,
                    url=cached_project.url,
                    created_time=cached_project.notion_created_time,
                    last_edited_time=cached_project.notion_last_edited_time
                )
                employee_projects_dict[assignee].append(employee_project)
        
        # Build response with employees
        employees_with_projects = []
        employees_with_projects_count = 0
        
        for employee_name, projects in employee_projects_dict.items():
            # Count projects by health color
            health_counts = {"red": 0, "yellow": 0, "green": 0, "not_set": 0}
            for project in projects:
                health_color = project.health_color
                if health_color == "red":
                    health_counts["red"] += 1
                elif health_color == "yellow":
                    health_counts["yellow"] += 1
                elif health_color == "green":
                    health_counts["green"] += 1
                else:
                    health_counts["not_set"] += 1
            
            employee_with_projects = EmployeeWithProjects(
                employee_name=employee_name,
                total_projects=len(projects),
                projects_by_health=health_counts,
                projects=projects
            )
            employees_with_projects.append(employee_with_projects)
            
            if len(projects) > 0:
                employees_with_projects_count += 1
        
        # Sort employees by name for consistency
        employees_with_projects.sort(key=lambda x: x.employee_name)
        
        return EmployeesWithProjectsResponse(
            total_employees=len(employees_with_projects),
            employees_with_projects=employees_with_projects_count,
            employees=employees_with_projects
        )

