from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Importe o CORSMiddleware
from app.routers import objectives, krs, activities, auth # Added kr_description_router

app = FastAPI(title="Objectives and Key Results API")

# Configure o middleware CORS
# Em produção, substitua "*" pelos domínios permitidos do seu frontend
origins = [
    "http://localhost",
    "http://localhost:8080", # Exemplo: se seu frontend roda na porta 8080
    "http://localhost:3000", # Exemplo: se seu frontend roda na porta 3000
    "http://localhost:4200", # Exemplo: se seu frontend roda na porta 4200
    "*" # Permite qualquer origem (use com cautela em produção)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Permite todos os métodos (GET, POST, PUT, DELETE, OPTIONS, etc.)
    allow_headers=["*"], # Permite todos os cabeçalhos
)

# Include Auth Router
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Include Objectives Router
app.include_router(objectives.router, prefix="/objectives", tags=["Objectives"])

# Include Key Results (KRs) Router
app.include_router(krs.router, prefix="/krs", tags=["Key Results (KRs)"]) # Main KR routes

# Include Activities Router
app.include_router(activities.router, prefix="/activities", tags=["Activities"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Objectives and Key Results API"}
