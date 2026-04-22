from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from ..models.folder import Folder
from ..models.file import File
from ..schemas.folder import FolderCreate, FolderUpdate, FolderTree, FolderStats


class FolderService:
    """Service class for folder operations"""

    @staticmethod
    async def create_folder(
        db: AsyncSession, folder_data: FolderCreate, created_by: int
    ) -> Folder:
        """Create a new folder"""

        # Validate parent folder exists if parent_id is provided
        if folder_data.parent_id:
            parent_result = await db.execute(
                select(Folder).where(Folder.id == folder_data.parent_id)
            )
            parent_folder = parent_result.scalar_one_or_none()
            if not parent_folder:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent folder not found",
                )

        # Check for duplicate folder names in the same parent
        existing_query = select(Folder).where(
            and_(
                Folder.name == folder_data.name,
                Folder.parent_id == folder_data.parent_id,
            )
        )
        existing_result = await db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Folder with this name already exists in the parent directory",
            )

        # Create the folder
        db_folder = Folder(
            name=folder_data.name,
            description=folder_data.description,
            parent_id=folder_data.parent_id,
            created_by=created_by,
            path="",  # Will be calculated after creation
        )

        db.add(db_folder)
        await db.flush()  # Get the ID without committing

        # Calculate and set the path
        db_folder.update_path()

        await db.commit()
        await db.refresh(db_folder)

        return db_folder

    @staticmethod
    async def get_folder_by_id(db: AsyncSession, folder_id: int) -> Optional[Folder]:
        """Get folder by ID"""
        result = await db.execute(
            select(Folder)
            .options(selectinload(Folder.files))
            .where(Folder.id == folder_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_folders(
        db: AsyncSession,
        parent_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Folder]:
        """Get folders with optional parent filter"""
        query = select(Folder).options(selectinload(Folder.files))

        if parent_id is not None:
            query = query.where(Folder.parent_id == parent_id)

        query = query.offset(skip).limit(limit).order_by(Folder.name)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_root_folders(db: AsyncSession) -> List[Folder]:
        """Get all root folders (folders without parent)"""
        result = await db.execute(
            select(Folder)
            .options(selectinload(Folder.files))
            .where(Folder.parent_id.is_(None))
            .order_by(Folder.name)
        )
        return result.scalars().all()

    @staticmethod
    async def get_folder_tree(
        db: AsyncSession, parent_id: Optional[int] = None
    ) -> List[FolderTree]:
        """Get hierarchical folder tree"""

        async def build_tree_node(folder: Folder) -> FolderTree:
            # Get file count for this folder
            file_count_result = await db.execute(
                select(func.count(File.id)).where(File.folder_id == folder.id)
            )
            file_count = file_count_result.scalar() or 0

            # Get children
            children_result = await db.execute(
                select(Folder)
                .where(Folder.parent_id == folder.id)
                .order_by(Folder.name)
            )
            children = children_result.scalars().all()

            # Build child nodes recursively
            child_nodes = []
            for child in children:
                child_node = await build_tree_node(child)
                child_nodes.append(child_node)

            return FolderTree(
                id=folder.id,
                name=folder.name,
                description=folder.description,
                path=folder.path,
                parent_id=folder.parent_id,
                created_by=folder.created_by,
                created_at=folder.created_at,
                updated_at=folder.updated_at,
                file_count=file_count,
                children=child_nodes,
            )

        # Get root folders or children of specified parent
        if parent_id is None:
            folders = await FolderService.get_root_folders(db)
        else:
            result = await db.execute(
                select(Folder)
                .where(Folder.parent_id == parent_id)
                .order_by(Folder.name)
            )
            folders = result.scalars().all()

        # Build tree nodes
        tree_nodes = []
        for folder in folders:
            node = await build_tree_node(folder)
            tree_nodes.append(node)

        return tree_nodes

    @staticmethod
    async def update_folder(
        db: AsyncSession, folder_id: int, folder_update: FolderUpdate
    ) -> Optional[Folder]:
        """Update folder"""
        folder = await FolderService.get_folder_by_id(db, folder_id)
        if not folder:
            return None

        # Check for duplicate names if name is being changed
        if folder_update.name and folder_update.name != folder.name:
            existing_query = select(Folder).where(
                and_(
                    Folder.name == folder_update.name,
                    Folder.parent_id == folder.parent_id,
                    Folder.id != folder_id,
                )
            )
            existing_result = await db.execute(existing_query)
            if existing_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Folder with this name already exists in the parent directory",
                )

        # Update fields
        if folder_update.name is not None:
            folder.name = folder_update.name
        if folder_update.description is not None:
            folder.description = folder_update.description

        # Update path if name changed
        if folder_update.name and folder_update.name != folder.name:
            folder.update_path()
            folder.update_descendants_paths()

        await db.commit()
        await db.refresh(folder)

        return folder

    @staticmethod
    async def move_folder(
        db: AsyncSession, folder_id: int, new_parent_id: Optional[int]
    ) -> Optional[Folder]:
        """Move folder to a new parent"""
        folder = await FolderService.get_folder_by_id(db, folder_id)
        if not folder:
            return None

        # Validate new parent exists if provided
        if new_parent_id:
            parent_result = await db.execute(
                select(Folder).where(Folder.id == new_parent_id)
            )
            new_parent = parent_result.scalar_one_or_none()
            if not new_parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="New parent folder not found",
                )

            # Check for circular reference
            if await FolderService._would_create_circular_reference(
                db, folder_id, new_parent_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot move folder: would create circular reference",
                )

        # Check for duplicate names in new parent
        existing_query = select(Folder).where(
            and_(
                Folder.name == folder.name,
                Folder.parent_id == new_parent_id,
                Folder.id != folder_id,
            )
        )
        existing_result = await db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Folder with this name already exists in the destination",
            )

        # Update parent and paths
        folder.parent_id = new_parent_id
        folder.update_path()
        folder.update_descendants_paths()

        await db.commit()
        await db.refresh(folder)

        return folder

    @staticmethod
    async def delete_folder(
        db: AsyncSession, folder_id: int, recursive: bool = False
    ) -> bool:
        """Delete folder (optionally recursive)"""
        folder = await FolderService.get_folder_by_id(db, folder_id)
        if not folder:
            return False

        # Check if folder has children
        children_result = await db.execute(
            select(func.count(Folder.id)).where(Folder.parent_id == folder_id)
        )
        children_count = children_result.scalar() or 0

        # Check if folder has files
        files_result = await db.execute(
            select(func.count(File.id)).where(File.folder_id == folder_id)
        )
        files_count = files_result.scalar() or 0

        if not recursive and (children_count > 0 or files_count > 0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete folder: contains files or subfolders. Use recursive=true to force delete.",
            )

        if recursive:
            # Delete all descendant folders and files
            await FolderService._delete_folder_recursive(db, folder)

        await db.delete(folder)
        await db.commit()

        return True

    @staticmethod
    async def get_folder_stats(
        db: AsyncSession, folder_id: Optional[int] = None
    ) -> FolderStats:
        """Get folder statistics"""
        if folder_id:
            # Stats for specific folder and its descendants
            folder = await FolderService.get_folder_by_id(db, folder_id)
            if not folder:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found"
                )

            # Get all descendant folder IDs
            descendant_ids = [folder.id]
            descendants = folder.get_descendants()
            descendant_ids.extend([d.id for d in descendants])

            # Count folders
            total_folders = len(descendant_ids)

            # Count files and total size
            files_result = await db.execute(
                select(func.count(File.id), func.sum(File.file_size)).where(
                    File.folder_id.in_(descendant_ids)
                )
            )
            files_count, total_size = files_result.first()

            # Calculate depth
            depth = len(folder.get_ancestors()) + 1

        else:
            # Global stats
            folders_result = await db.execute(select(func.count(Folder.id)))
            total_folders = folders_result.scalar() or 0

            files_result = await db.execute(
                select(func.count(File.id), func.sum(File.file_size))
            )
            files_count, total_size = files_result.first()

            # Calculate maximum depth
            max_depth_result = await db.execute(
                select(
                    func.max(
                        func.length(Folder.path)
                        - func.length(func.replace(Folder.path, "/", ""))
                    )
                )
            )
            depth = max_depth_result.scalar() or 0

        return FolderStats(
            total_folders=total_folders,
            total_files=files_count or 0,
            total_size=total_size or 0,
            depth=depth,
        )

    @staticmethod
    async def _would_create_circular_reference(
        db: AsyncSession, folder_id: int, new_parent_id: int
    ) -> bool:
        """Check if moving folder would create circular reference"""
        current_id = new_parent_id

        while current_id:
            if current_id == folder_id:
                return True

            parent_result = await db.execute(
                select(Folder.parent_id).where(Folder.id == current_id)
            )
            current_id = parent_result.scalar()

        return False

    @staticmethod
    async def _delete_folder_recursive(db: AsyncSession, folder: Folder):
        """Recursively delete folder and all its contents"""
        # Delete all files in this folder
        files_result = await db.execute(select(File).where(File.folder_id == folder.id))
        files = files_result.scalars().all()
        for file in files:
            await db.delete(file)

        # Delete all child folders recursively
        children_result = await db.execute(
            select(Folder).where(Folder.parent_id == folder.id)
        )
        children = children_result.scalars().all()
        for child in children:
            await FolderService._delete_folder_recursive(db, child)
            await db.delete(child)
