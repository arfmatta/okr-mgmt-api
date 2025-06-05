from fastapi import FastAPI
from app.routers import objectives, krs, activities, kr_description_router # Added kr_description_router

app = FastAPI(title="Objectives and Key Results API")

# Include Objectives Router
app.include_router(objectives.router, tags=["Objectives"])

# Include Key Results (KRs) Router
app.include_router(krs.router, tags=["Key Results (KRs)"]) # Main KR routes

# Include KR Description Management Router (also uses /krs prefix but for specific description endpoint)
app.include_router(kr_description_router.router, tags=["Key Results (KRs) - Description Management"])

# Include Activities Router
app.include_router(activities.router, tags=["Activities"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Objectives and Key Results API"}
