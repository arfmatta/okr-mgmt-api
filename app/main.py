from fastapi import FastAPI
from app.routers import objectives, krs, activities # Added activities

app = FastAPI(title="Objectives and Key Results API")

# Include Objectives Router
app.include_router(objectives.router, prefix="/objectives", tags=["Objectives"])

# Include Key Results (KRs) Router
app.include_router(krs.router, prefix="/krs", tags=["Key Results (KRs)"])

# Include Activities Router
app.include_router(activities.router, prefix="/activities", tags=["Activities"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Objectives and Key Results API"}
