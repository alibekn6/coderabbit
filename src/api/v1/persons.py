"""
Person API endpoints.

This module contains API routes for Person CRUD operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.services.person_service import PersonService
from src.models.person import (
    PersonCreate,
    PersonUpdate,
    PersonResponse,
    PersonWithStats,
    PersonListResponse,
    PersonStatsListResponse
)
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/persons", response_model=PersonResponse, status_code=201)
async def create_person(
    data: PersonCreate, db: AsyncSession = Depends(get_db)
) -> PersonResponse:
    """
    Create a new person.

    Args:
        data: Person creation data
        db: Database session

    Returns:
        Created person

    Raises:
        HTTPException: If person already exists or validation fails
    """
    logger.info("create_person_request", notion_id=data.notion_id)

    try:
        service = PersonService(db)
        person = await service.create_person(data)
        logger.info("person_created", person_id=person.id)
        return person

    except ValueError as e:
        logger.warning("person_creation_failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error("person_creation_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/persons", response_model=PersonListResponse | PersonStatsListResponse)
async def list_persons(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    search: str = Query(None, description="Search term for name or email"),
    with_stats: bool = Query(False, description="Include activity statistics"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all persons with optional pagination and search.

    Args:
        skip: Number of records to skip
        limit: Maximum records to return
        search: Search term for name or email
        with_stats: Include activity statistics
        db: Database session

    Returns:
        List of persons
    """
    logger.info(
        "list_persons_request", skip=skip, limit=limit, search=search, with_stats=with_stats
    )

    try:
        service = PersonService(db)
        result = await service.list_persons(
            skip=skip, limit=limit, search=search, with_stats=with_stats
        )
        return result

    except Exception as e:
        logger.error("list_persons_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/persons/{person_id}", response_model=PersonResponse)
async def get_person(
    person_id: int, db: AsyncSession = Depends(get_db)
) -> PersonResponse:
    """
    Get a person by ID.

    Args:
        person_id: Person ID
        db: Database session

    Returns:
        Person details

    Raises:
        HTTPException: If person not found
    """
    logger.info("get_person_request", person_id=person_id)

    try:
        service = PersonService(db)
        person = await service.get_person(person_id)

        if not person:
            raise HTTPException(status_code=404, detail="Person not found")

        return person

    except HTTPException:
        raise

    except Exception as e:
        logger.error("get_person_error", person_id=person_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/persons/{person_id}/stats", response_model=PersonWithStats)
async def get_person_with_stats(
    person_id: int, db: AsyncSession = Depends(get_db)
) -> PersonWithStats:
    """
    Get a person with activity statistics.

    Args:
        person_id: Person ID
        db: Database session

    Returns:
        Person with activity statistics

    Raises:
        HTTPException: If person not found
    """
    logger.info("get_person_stats_request", person_id=person_id)

    try:
        service = PersonService(db)
        person = await service.get_person_with_stats(person_id)

        if not person:
            raise HTTPException(status_code=404, detail="Person not found")

        return person

    except HTTPException:
        raise

    except Exception as e:
        logger.error("get_person_stats_error", person_id=person_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/persons/by-notion/{notion_id}", response_model=PersonResponse)
async def get_person_by_notion_id(
    notion_id: str, db: AsyncSession = Depends(get_db)
) -> PersonResponse:
    """
    Get a person by Notion ID.

    Args:
        notion_id: Notion user ID
        db: Database session

    Returns:
        Person details

    Raises:
        HTTPException: If person not found
    """
    logger.info("get_person_by_notion_id_request", notion_id=notion_id)

    try:
        service = PersonService(db)
        person = await service.get_person_by_notion_id(notion_id)

        if not person:
            raise HTTPException(status_code=404, detail="Person not found")

        return person

    except HTTPException:
        raise

    except Exception as e:
        logger.error("get_person_by_notion_id_error", notion_id=notion_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/persons/{person_id}", response_model=PersonResponse)
async def update_person(
    person_id: int, data: PersonUpdate, db: AsyncSession = Depends(get_db)
) -> PersonResponse:
    """
    Update a person's information.

    Args:
        person_id: Person ID
        data: Update data
        db: Database session

    Returns:
        Updated person

    Raises:
        HTTPException: If person not found or validation fails
    """
    logger.info("update_person_request", person_id=person_id)

    try:
        service = PersonService(db)
        person = await service.update_person(person_id, data)

        if not person:
            raise HTTPException(status_code=404, detail="Person not found")

        logger.info("person_updated", person_id=person_id)
        return person

    except ValueError as e:
        logger.warning("person_update_failed", person_id=person_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))

    except HTTPException:
        raise

    except Exception as e:
        logger.error("update_person_error", person_id=person_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/persons/{person_id}", status_code=204)
async def delete_person(person_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete a person.

    Args:
        person_id: Person ID
        db: Database session

    Raises:
        HTTPException: If person not found
    """
    logger.info("delete_person_request", person_id=person_id)

    try:
        service = PersonService(db)
        deleted = await service.delete_person(person_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Person not found")

        logger.info("person_deleted", person_id=person_id)

    except HTTPException:
        raise

    except Exception as e:
        logger.error("delete_person_error", person_id=person_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")
