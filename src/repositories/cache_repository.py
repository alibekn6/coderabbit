"""
Repository for cache database operations.
Handles CRUD operations for cached Notion data.
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional

from src.schemas.notion_cache import (
    CacheMetadata,
    CachedNotionProject,
    CachedNotionTask,
    CachedTeamMember,
    CachedNotionTodo
)


class CacheRepository:
    """Repository for managing cached Notion data"""

    def __init__(self, db: Session):
        self.db = db

    # ============= Cache Metadata Operations =============

    def get_cache_metadata(self, cache_type: str) -> Optional[CacheMetadata]:
        """Get cache metadata for a specific cache type"""
        return self.db.query(CacheMetadata).filter(
            CacheMetadata.cache_type == cache_type
        ).first()

    def update_cache_metadata(
        self,
        cache_type: str,
        total_records: int,
        update_duration_seconds: int,
        error_message: Optional[str] = None
    ) -> CacheMetadata:
        """Update or create cache metadata"""
        metadata = self.get_cache_metadata(cache_type)
        
        if metadata:
            metadata.last_updated = datetime.utcnow()
            metadata.is_updating = False
            metadata.total_records = total_records
            metadata.update_duration_seconds = update_duration_seconds
            metadata.error_message = error_message
        else:
            metadata = CacheMetadata(
                cache_type=cache_type,
                last_updated=datetime.utcnow(),
                is_updating=False,
                total_records=total_records,
                update_duration_seconds=update_duration_seconds,
                error_message=error_message
            )
            self.db.add(metadata)
        
        self.db.commit()
        self.db.refresh(metadata)
        return metadata

    def set_cache_updating(self, cache_type: str, is_updating: bool):
        """Set the updating status for a cache"""
        metadata = self.get_cache_metadata(cache_type)
        
        if metadata:
            metadata.is_updating = is_updating
        else:
            metadata = CacheMetadata(
                cache_type=cache_type,
                last_updated=datetime.utcnow(),
                is_updating=is_updating,
                total_records=0
            )
            self.db.add(metadata)
        
        self.db.commit()

    def is_cache_fresh(self, cache_type: str, max_age_minutes: int = 30) -> bool:
        """Check if cache is fresh (updated recently)"""
        metadata = self.get_cache_metadata(cache_type)
        
        if not metadata:
            return False
        
        age = datetime.utcnow() - metadata.last_updated
        return age < timedelta(minutes=max_age_minutes)

    # ============= Project Cache Operations =============

    def get_all_cached_projects(self) -> List[CachedNotionProject]:
        """Get all cached projects"""
        return self.db.query(CachedNotionProject).all()

    def clear_projects_cache(self):
        """Clear all cached projects"""
        self.db.query(CachedNotionProject).delete()
        self.db.commit()

    def bulk_insert_projects(self, projects: List[CachedNotionProject]):
        """Bulk insert projects"""
        self.db.bulk_save_objects(projects)
        self.db.commit()

    def upsert_project(self, project: CachedNotionProject):
        """Insert or update a single project"""
        existing = self.db.query(CachedNotionProject).filter(
            CachedNotionProject.page_id == project.page_id
        ).first()
        
        if existing:
            for key, value in project.__dict__.items():
                if not key.startswith('_'):
                    setattr(existing, key, value)
        else:
            self.db.add(project)
        
        self.db.commit()

    # ============= Task Cache Operations =============

    def get_all_cached_tasks(self) -> List[CachedNotionTask]:
        """Get all cached tasks"""
        return self.db.query(CachedNotionTask).all()

    def clear_tasks_cache(self):
        """Clear all cached tasks"""
        self.db.query(CachedNotionTask).delete()
        self.db.commit()

    def bulk_insert_tasks(self, tasks: List[CachedNotionTask]):
        """Bulk insert tasks"""
        self.db.bulk_save_objects(tasks)
        self.db.commit()

    # ============= Team Member Cache Operations =============

    def get_or_create_team_member(self, member_name: str, **kwargs) -> CachedTeamMember:
        """Get existing team member or create new one"""
        member = self.db.query(CachedTeamMember).filter(
            CachedTeamMember.member_name == member_name
        ).first()
        
        if not member:
            member = CachedTeamMember(member_name=member_name, **kwargs)
            self.db.add(member)
            self.db.commit()
            self.db.refresh(member)
        else:
            # Update fields if provided
            for key, value in kwargs.items():
                if hasattr(member, key):
                    setattr(member, key, value)
            self.db.commit()
            self.db.refresh(member)
        
        return member

    def get_all_cached_team_members(self) -> List[CachedTeamMember]:
        """Get all cached team members"""
        return self.db.query(CachedTeamMember).all()

    # ============= Todo Cache Operations =============

    def get_all_cached_todos(self) -> List[CachedNotionTodo]:
        """Get all cached todos"""
        return self.db.query(CachedNotionTodo).all()

    def get_todos_by_member(self, member_name: str) -> List[CachedNotionTodo]:
        """Get todos for a specific team member"""
        return self.db.query(CachedNotionTodo).filter(
            CachedNotionTodo.member_name == member_name
        ).all()

    def get_overdue_todos(self) -> List[CachedNotionTodo]:
        """Get all overdue todos"""
        return self.db.query(CachedNotionTodo).filter(
            CachedNotionTodo.is_overdue.is_(True)
        ).all()

    def clear_todos_cache(self):
        """Clear all cached todos"""
        self.db.query(CachedNotionTodo).delete()
        self.db.commit()

    def bulk_insert_todos(self, todos: List[CachedNotionTodo]):
        """Bulk insert todos"""
        self.db.bulk_save_objects(todos)
        self.db.commit()
