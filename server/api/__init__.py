from fastapi import APIRouter

from server.api import activity, businesses, campaigns, comments, emails, participations, postcards, settings

api_router = APIRouter()
api_router.include_router(settings.router)
api_router.include_router(businesses.router)
api_router.include_router(campaigns.router)
api_router.include_router(participations.router)
api_router.include_router(emails.router)
api_router.include_router(comments.router)
api_router.include_router(activity.router)
api_router.include_router(postcards.router)
