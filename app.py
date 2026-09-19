from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import logging
import os
from datetime import datetime

from services.llm_service import LLMService
from services.rag_service import RAGService
from services.translation import TranslationService
from services.tts_service import TTSService
from database.operations import DatabaseOperations
from models.recipe import Recipe, RecipeCreate, RecipeResponse
from models.user import User, UserContribution
from utils.file_processor import FileProcessor
from utils.validators import validate_recipe_input
from config.settings import Settings

# Initialize FastAPI app
app = FastAPI(
    title="Mana Ruchulu API",
    description="Telugu Recipe & Culinary Chatbot API",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=Settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
llm_service = LLMService()
rag_service = RAGService()
translation_service = TranslationService()
tts_service = TTSService()
db_operations = DatabaseOperations()
file_processor = FileProcessor()

# Security
security = HTTPBearer()

# Pydantic models for API
class ChatMessage(BaseModel):
    message: str
    language: str = "telugu"
    include_audio: bool = False

class ChatResponse(BaseModel):
    response: str
    telugu_response: Optional[str] = None
    audio_url: Optional[str] = None
    recipe_suggestions: Optional[List[Dict]] = None

class RecipeSearchRequest(BaseModel):
    query: str
    ingredients: Optional[List[str]] = None
    dietary_restrictions: Optional[List[str]] = None
    region: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await db_operations.initialize_database()
    await rag_service.initialize_vector_store()
    logging.info("Mana Ruchulu API started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await db_operations.close_connections()
    logging.info("Mana Ruchulu API shutdown complete")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat_with_bot(message: ChatMessage):
    try:
        # Get context from RAG
        relevant_recipes = await rag_service.search_recipes(
            message.message, 
            limit=3
        )
        
        # Generate response using LLM
        response = await llm_service.generate_response(
            message.message,
            context=relevant_recipes,
            language=message.language
        )
        
        # Translate to Telugu if needed
        telugu_response = None
        if message.language == "telugu":
            telugu_response = await translation_service.translate_to_telugu(response)
        
        # Generate audio if requested
        audio_url = None
        if message.include_audio:
            audio_url = await tts_service.generate_audio(
                telugu_response or response,
                language="te"
            )
        
        # Get recipe suggestions
        recipe_suggestions = await get_recipe_suggestions(message.message)
        
        return ChatResponse(
            response=response,
            telugu_response=telugu_response,
            audio_url=audio_url,
            recipe_suggestions=recipe_suggestions
        )
        
    except Exception as e:
        logging.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Recipe search endpoint
@app.post("/recipes/search")
async def search_recipes(search_request: RecipeSearchRequest):
    try:
        recipes = await rag_service.search_recipes(
            query=search_request.query,
            ingredients=search_request.ingredients,
            dietary_restrictions=search_request.dietary_restrictions,
            region=search_request.region,
            limit=10
        )
        return {"recipes": recipes}
        
    except Exception as e:
        logging.error(f"Recipe search error: {str(e)}")
        raise HTTPException(status_code=500, detail="Search failed")

# Recipe upload endpoint
@app.post("/recipes/upload")
async def upload_recipe(
    file: UploadFile = File(...),
    metadata: str = None
):
    try:
        # Validate file
        if not file_processor.validate_file(file):
            raise HTTPException(status_code=400, detail="Invalid file format")
        
        # Process file
        processed_content = await file_processor.process_file(file)
        
        # Extract recipe information using LLM
        recipe_data = await llm_service.extract_recipe_from_text(processed_content)
        
        # Validate extracted recipe
        validated_recipe = validate_recipe_input(recipe_data)
        
        # Save to database
        recipe_id = await db_operations.create_recipe(validated_recipe)
        
        # Add to vector store
        await rag_service.add_recipe_to_vector_store(validated_recipe)
        
        return {"message": "Recipe uploaded successfully", "recipe_id": recipe_id}
        
    except Exception as e:
        logging.error(f"Recipe upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="Upload failed")

# Get recipe by ID
@app.get("/recipes/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(recipe_id: str):
    try:
        recipe = await db_operations.get_recipe(recipe_id)
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        return recipe
        
    except Exception as e:
        logging.error(f"Get recipe error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recipe")

# Audio generation endpoint
@app.post("/audio/generate")
async def generate_audio(text: str, language: str = "te"):
    try:
        audio_file = await tts_service.generate_audio(text, language)
        return StreamingResponse(
            audio_file,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=recipe_audio.mp3"}
        )
        
    except Exception as e:
        logging.error(f"Audio generation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Audio generation failed")

# Admin endpoints
@app.get("/admin/recipes")
async def get_all_recipes_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Add authentication logic here
    try:
        recipes = await db_operations.get_all_recipes()
        return {"recipes": recipes}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve recipes")

@app.put("/admin/recipes/{recipe_id}/approve")
async def approve_recipe(recipe_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        await db_operations.approve_recipe(recipe_id)
        return {"message": "Recipe approved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to approve recipe")

# Helper function
async def get_recipe_suggestions(query: str) -> List[Dict]:
    """Get recipe suggestions based on query"""
    try:
        suggestions = await rag_service.get_similar_recipes(query, limit=5)
        return [{"id": r.id, "name": r.name, "cuisine": r.cuisine} for r in suggestions]
    except:
        return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)