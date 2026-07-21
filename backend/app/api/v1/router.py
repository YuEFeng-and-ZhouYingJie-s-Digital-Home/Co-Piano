"""
API v1 路由聚合
===============
"""
from fastapi import APIRouter

from app.api.v1 import auth, evaluations, oauth, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(oauth.router)
api_router.include_router(users.router)
api_router.include_router(evaluations.router)
