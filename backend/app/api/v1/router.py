"""
API v1 路由聚合
===============
"""
from fastapi import APIRouter

from app.api.v1 import (
    auth,
    curriculum,
    evaluations,
    feedback,
    oauth,
    sight_reading,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(oauth.router)
api_router.include_router(users.router)
api_router.include_router(evaluations.router)
api_router.include_router(curriculum.router)
api_router.include_router(sight_reading.router)
api_router.include_router(feedback.router)
