"""Services package"""
from .cache import CacheService, cache_service
from .curriculum_service import CurriculumService, curriculum_service
from .evaluation_service import EvaluationResult, EvaluationService, evaluation_service
from .sight_reading_service import SightReadingService, sight_reading_service
from .storage import StorageService, storage_service
from .user_service import UserService

__all__ = [
    "UserService",
    "EvaluationService",
    "EvaluationResult",
    "evaluation_service",
    "StorageService",
    "storage_service",
    "CacheService",
    "cache_service",
    "CurriculumService",
    "curriculum_service",
    "SightReadingService",
    "sight_reading_service",
]
