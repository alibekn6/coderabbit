from fastapi import APIRouter, Query, HTTPException, status, Depends
from sqlalchemy.orm import Session
from src.services.cached_notion_service import CachedNotionService
from src.models.notion import (
    NotionTasksResponse,
    NotionProjectsResponse,
    ProjectStatsResponse,
    TodosByMemberResponse,
    MemberWithTodos,
    OverdueTodosResponse,
    TodoStatistics,
    EmployeesWithProjectsResponse,
)
from src.core.dependencies import CurrentUser
from src.db.sync_database import get_sync_db
from src.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/tasks", response_model=NotionTasksResponse)
def get_all_tasks(
    current_user: CurrentUser,
    db: Session = Depends(get_sync_db)
):
    """
    Get all tasks from the Notion database (cached - instant response!)

    **Authentication required**: JWT token in Authorization header
    
    **Performance**: Returns cached data (~50ms response time)

    Returns:
        NotionTasksResponse: All tasks with their properties
    """
    logger.info("get_all_tasks_request", user_id=current_user.id)
    service = CachedNotionService(db)
    return service.get_all_tasks()


@router.get("/tasks/filter", response_model=NotionTasksResponse)
def filter_tasks(
    current_user: CurrentUser,
    db: Session = Depends(get_sync_db),
    status: str = Query(
        None, description="Filter by status (e.g., 'In progress', 'Done', 'Not started')"
    ),
    priority: str = Query(
        None, description="Filter by priority (e.g., 'High', 'Medium', 'Low')"
    ),
):
    """
    Filter tasks by status and/or priority (cached - instant response!)

    **Authentication required**: JWT token in Authorization header
    
    **Performance**: Returns cached data (~50ms response time)

    Args:
        status: Task status to filter by
        priority: Task priority to filter by

    Returns:
        NotionTasksResponse: Filtered tasks
    """
    logger.info(
        "filter_tasks_request",
        user_id=current_user.id,
        status=status,
        priority=priority
    )
    service = CachedNotionService(db)
    return service.query_tasks(status=status, priority=priority)


@router.get("/projects", response_model=NotionProjectsResponse)
def get_all_projects(
    current_user: CurrentUser,
    db: Session = Depends(get_sync_db)
):
    """
    Get all projects from the Notion Projects database (cached - instant response!)

    **Authentication required**: JWT token in Authorization header
    
    **Performance**: Returns cached data (~50ms response time)

    Returns:
        NotionProjectsResponse: All projects with their properties including:
        - Project name
        - Health status (red/yellow/green)
        - Assignees (responsible persons)
        - Status, priority, and task count
    """
    logger.info("get_all_projects_request", user_id=current_user.id)
    try:
        service = CachedNotionService(db)
        return service.get_all_projects()
    except Exception as e:
        logger.error("get_all_projects_error", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch projects from cache"
        )


@router.get("/projects/health/{health_color}", response_model=NotionProjectsResponse)
def get_projects_by_health(
    health_color: str,
    current_user: CurrentUser,
    db: Session = Depends(get_sync_db)
):
    """
    Get projects filtered by health status color (cached - instant response!)

    **Authentication required**: JWT token in Authorization header
    
    **Performance**: Returns cached data (~50ms response time)

    Args:
        health_color: The health status color to filter by.
                     Valid values: 'red', 'yellow', 'green'

    Returns:
        NotionProjectsResponse: Projects matching the specified health status

    Raises:
        HTTPException 400: If invalid health_color is provided
    """
    valid_colors = ["red", "yellow", "green"]
    if health_color.lower() not in valid_colors:
        logger.warning(
            "invalid_health_color",
            user_id=current_user.id,
            health_color=health_color
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid health color. Must be one of: {', '.join(valid_colors)}"
        )

    logger.info(
        "get_projects_by_health_request",
        user_id=current_user.id,
        health_color=health_color
    )

    try:
        service = CachedNotionService(db)
        return service.get_projects_by_health(health_color.lower())
    except Exception as e:
        logger.error(
            "get_projects_by_health_error",
            user_id=current_user.id,
            health_color=health_color,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch projects from cache"
        )


@router.get("/projects/statistics", response_model=ProjectStatsResponse)
def get_project_statistics(
    current_user: CurrentUser,
    db: Session = Depends(get_sync_db)
):
    """
    Get project statistics and aggregations (cached - instant response!)

    **Authentication required**: JWT token in Authorization header
    
    **Performance**: Returns cached data (~50ms response time)

    Returns:
        ProjectStatsResponse: Aggregated project statistics including:
        - Total project count
        - Count by health status (red/yellow/green/not set)
        - Count by assignee (who is responsible for how many projects)
    """
    logger.info("get_project_statistics_request", user_id=current_user.id)
    try:
        service = CachedNotionService(db)
        return service.get_project_statistics()
    except Exception as e:
        logger.error(
            "get_project_statistics_error",
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate project statistics"
        )

@router.get("/todos", response_model=TodosByMemberResponse)
def get_all_member_todos(
    current_user: CurrentUser,
    db: Session = Depends(get_sync_db),
    status: str = Query(
        None,
        description="Filter todos by status (e.g., 'To-do', 'In-progress', 'Done')"
    ),
):
    """
    Get todos for all team members from their Kanban boards (cached - instant response!)

    **Authentication required**: JWT token in Authorization header
    
    **Performance**: Returns cached data (~60ms response time)

    Args:
        status: Optional status to filter todos

    Returns:
        TodosByMemberResponse: All team members with their todos including:
        - Member information (name, position, status, tg_id)
        - Total task count per member
        - Tasks grouped by status
        - Overdue task count
        - Full list of todos with deadlines and project links
    """
    logger.info(
        "get_all_member_todos_request",
        user_id=current_user.id,
        status_filter=status
    )
    try:
        service = CachedNotionService(db)
        return service.get_all_member_todos(status_filter=status)
    except Exception as e:
        logger.error(
            "get_all_member_todos_error",
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch member todos from cache"
        )


@router.get("/todos/member/{member_name}", response_model=MemberWithTodos)
def get_member_todos_by_name(
    member_name: str,
    current_user: CurrentUser,
    db: Session = Depends(get_sync_db),
    status: str = Query(
        None,
        description="Filter todos by status (e.g., 'To-do', 'In-progress', 'Done')"
    ),
):
    """
    Get todos for a specific team member by name (cached - instant response!)

    **Authentication required**: JWT token in Authorization header
    
    **Performance**: Returns cached data (~60ms response time)

    Args:
        member_name: Name of the team member (can be partial match)
        status: Optional status to filter todos

    Returns:
        MemberWithTodos: Team member's information and their todos

    Raises:
        HTTPException 404: If member not found
    """
    logger.info(
        "get_member_todos_by_name_request",
        user_id=current_user.id,
        member_name=member_name,
        status_filter=status
    )
    try:
        service = CachedNotionService(db)
        return service.get_member_todos_by_name(
            member_name=member_name,
            status_filter=status
        )
    except ValueError as e:
        logger.warning(
            "member_not_found",
            user_id=current_user.id,
            member_name=member_name,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "get_member_todos_by_name_error",
            user_id=current_user.id,
            member_name=member_name,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch member todos from cache"
        )


@router.get("/todos/overdue", response_model=OverdueTodosResponse)
def get_overdue_todos(
    current_user: CurrentUser,
    db: Session = Depends(get_sync_db)
):
    """
    Get all overdue todos across all team members (cached - instant response!)

    **Authentication required**: JWT token in Authorization header
    
    **Performance**: Returns cached data (~60ms response time)

    Returns:
        OverdueTodosResponse: All overdue todos with member context including:
        - Member name and position
        - Todo details (name, deadline, status)
        - Direct link to the todo in Notion

    A todo is considered overdue if:
    - It has a deadline
    - The deadline is in the past
    - Status is not 'Done' or 'Cancelled'
    """
    logger.info("get_overdue_todos_request", user_id=current_user.id)
    try:
        service = CachedNotionService(db)
        return service.get_overdue_todos()
    except Exception as e:
        logger.error(
            "get_overdue_todos_error",
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch overdue todos from cache"
        )


@router.get("/todos/statistics", response_model=TodoStatistics)
def get_todo_statistics(
    current_user: CurrentUser,
    db: Session = Depends(get_sync_db)
):
    """
    Get aggregated statistics about todos across all team members (cached - instant response!)

    **Authentication required**: JWT token in Authorization header
    
    **Performance**: Returns cached data (~60ms response time)

    Returns:
        TodoStatistics: Aggregated todo statistics including:
        - Total members and members with/without tasks
        - Total todo count
        - Count by status (To-do, In-progress, Done)
        - Total overdue count
        - Overdue count by member
    """
    logger.info("get_todo_statistics_request", user_id=current_user.id)
    try:
        service = CachedNotionService(db)
        return service.get_todo_statistics()
    except Exception as e:
        logger.error(
            "get_todo_statistics_error",
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate todo statistics"
        )


@router.get("/todos/active", response_model=TodosByMemberResponse)
def get_active_todos(
    current_user: CurrentUser,
    db: Session = Depends(get_sync_db)
):
    """
    Get all active todos (To-do and In-progress) for all team members (cached - instant response!)
    
    **ULTRA-OPTIMIZED**: Returns results in ~60ms from cache instead of 8+ seconds!

    **Authentication required**: JWT token in Authorization header
    
    **Performance**: Returns cached data (~60ms response time)

    Returns:
        TodosByMemberResponse: All team members with their active todos including:
        - Member information (name, position, status, tg_id)
        - Total task count per member (To-do + In-progress only)
        - Tasks grouped by status
        - Overdue task count with indicator
        - Full list of active todos with:
          * Task name and status
          * Deadline dates
          * Overdue flag (is_overdue: true/false)
          * Direct links to tasks in Notion
          * Related project IDs
    
    **Overdue Detection**:
    - A task is marked as overdue if deadline < today AND status != 'Done'
    - The overdue_count field shows total overdue tasks per member
    - Each todo has is_overdue boolean flag
    """
    logger.info("get_active_todos_request", user_id=current_user.id)
    try:
        # Get all todos from cache (filtered to active ones)
        service = CachedNotionService(db)
        result = service.get_all_member_todos(status_filter=None)
        
        logger.info(
            "active_todos_fetched",
            user_id=current_user.id,
            total_members=result.total_members,
            members_with_active_tasks=result.members_with_tasks
        )
        
        return result
    except Exception as e:
        logger.error(
            "get_active_todos_error",
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch active todos from cache"
        )


@router.get("/employees", response_model=EmployeesWithProjectsResponse)
def get_all_employees_with_projects(
    current_user: CurrentUser,
    db: Session = Depends(get_sync_db)
):
    """
    Get all employees with their assigned projects (cached - instant response!)
    
    **REVERSE VIEW**: Instead of projects → assignees, this shows employees → projects

    **Authentication required**: JWT token in Authorization header
    
    **Performance**: Returns cached data (~50ms response time)

    Returns:
        EmployeesWithProjectsResponse: All employees with their projects including:
        - Employee name
        - Total project count per employee
        - Projects grouped by health color (red/yellow/green/not_set counts)
        - Full list of projects with:
          * Project name and status
          * Health status and color
          * Priority and color
          * Task count
          * Direct links to projects in Notion
          * Created and last edited timestamps
    
    **Use Case**:
    - See which employee is working on which projects
    - Check project health distribution per employee
    - Identify employees with too many red/yellow projects
    - Understand workload distribution across the team
    """
    logger.info("get_all_employees_with_projects_request", user_id=current_user.id)
    try:
        service = CachedNotionService(db)
        result = service.get_all_employees_with_projects()
        
        logger.info(
            "employees_with_projects_fetched",
            user_id=current_user.id,
            total_employees=result.total_employees,
            employees_with_projects=result.employees_with_projects
        )
        
        return result
    except Exception as e:
        logger.error(
            "get_all_employees_with_projects_error",
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch employees with projects from cache"
        )

