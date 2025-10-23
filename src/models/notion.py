from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class TaskProperties(BaseModel):
    """Task properties from Notion database"""
    task_name: str
    status: Optional[str] = None
    priority: Optional[str] = None
    effort_level: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None
    task_type: List[str] = []
    assignee: List[str] = []


class NotionTask(BaseModel):
    """Complete task information from Notion"""
    page_id: str
    created_time: datetime
    last_edited_time: datetime
    properties: TaskProperties


class NotionTasksResponse(BaseModel):
    """Response containing all tasks"""
    total_count: int
    tasks: List[NotionTask]


class ProjectProperties(BaseModel):
    """Project properties from Notion database"""
    project_name: str
    health_status: Optional[str] = None
    health_color: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    priority_color: Optional[str] = None
    assignees: List[str] = []
    task_count: int = 0


class NotionProject(BaseModel):
    """Complete project information from Notion"""
    page_id: str
    created_time: datetime
    last_edited_time: datetime
    url: str
    properties: ProjectProperties


class NotionProjectsResponse(BaseModel):
    """Response containing all projects"""
    total_count: int
    projects: List[NotionProject]


class ProjectStatusSummary(BaseModel):
    """Summary of project counts by status"""
    red: int = 0
    yellow: int = 0
    green: int = 0
    not_set: int = 0


class ProjectStatsResponse(BaseModel):
    """Project statistics response"""
    total_projects: int
    status_summary: ProjectStatusSummary
    projects_by_assignee: dict[str, int]


# ============= TODO / TEAM MEMBER SCHEMAS =============

class TodoProperties(BaseModel):
    """Todo properties from team member's Kanban board"""
    name: str
    status: Optional[str] = None
    deadline: Optional[str] = None
    date_done: Optional[str] = None
    is_overdue: bool = False
    project_ids: List[str] = []


class NotionTodo(BaseModel):
    """Complete todo information from Notion"""
    id: str
    url: str
    properties: TodoProperties


class MemberInfo(BaseModel):
    """Team member information"""
    name: str
    position: Optional[str] = None
    status: Optional[str] = None
    tg_id: Optional[str] = None
    start_date: Optional[str] = None


class MemberWithTodos(BaseModel):
    """Team member with their todos"""
    member: MemberInfo
    total_tasks: int
    tasks_by_status: dict[str, int]
    overdue_count: int
    todos: List[NotionTodo]


class TodosByMemberResponse(BaseModel):
    """Response containing todos grouped by member"""
    total_members: int
    members_with_tasks: int
    members: List[MemberWithTodos]


class OverdueTodo(BaseModel):
    """Overdue todo with member context"""
    member_name: str
    member_position: Optional[str] = None
    todo: NotionTodo


class OverdueTodosResponse(BaseModel):
    """Response containing all overdue todos"""
    total_overdue: int
    overdue_todos: List[OverdueTodo]


class TodoStatistics(BaseModel):
    """Statistics about todos across all members"""
    total_members: int
    members_with_tasks: int
    members_without_tasks: int
    total_todos: int
    todos_by_status: dict[str, int]
    total_overdue: int
    overdue_by_member: dict[str, int]


# ============= EMPLOYEE-CENTRIC SCHEMAS =============

class EmployeeProject(BaseModel):
    """Project information from employee's perspective"""
    page_id: str
    project_name: str
    status: Optional[str] = None
    health_status: Optional[str] = None
    health_color: Optional[str] = None
    priority: Optional[str] = None
    priority_color: Optional[str] = None
    task_count: int = 0
    url: str
    created_time: datetime
    last_edited_time: datetime


class EmployeeWithProjects(BaseModel):
    """Employee with their assigned projects"""
    employee_name: str
    total_projects: int
    projects_by_health: dict[str, int]  # {"red": 2, "yellow": 1, "green": 3, "not_set": 0}
    projects: List[EmployeeProject]


class EmployeesWithProjectsResponse(BaseModel):
    """Response containing employees grouped with their projects"""
    total_employees: int
    employees_with_projects: int
    employees: List[EmployeeWithProjects]
