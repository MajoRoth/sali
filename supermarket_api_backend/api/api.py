from fastapi import APIRouter

from api.endpoints import analytics, chains, health, products, stores

api_router = APIRouter()
api_router.include_router(chains.router, prefix="/chains", tags=["chains"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(stores.router, prefix="/stores", tags=["stores"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
