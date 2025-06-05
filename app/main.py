from fastapi import FastAPI
from app.routers import objectives, krs, activities, kr_description_router # Added kr_description_router

app = FastAPI(title="Objectives and Key Results API")

# Include Objectives Router
app.include_router(objectives.router, prefix="/objectives", tags=["Objectives"])

# Include Key Results (KRs) Router
app.include_router(krs.router, prefix="/krs", tags=["Key Results (KRs)"]) # Main KR routes

# Include KR Description Management Router (also uses /krs prefix but for specific description endpoint)
app.include_router(kr_description_router.router, prefix="/krs", tags=["Key Results (KRs) - Description Management"])

# Include Activities Router
app.include_router(activities.router, prefix="/activities", tags=["Activities"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Objectives and Key Results API"}
