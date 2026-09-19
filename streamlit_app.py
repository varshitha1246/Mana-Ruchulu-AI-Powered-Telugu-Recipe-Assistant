import streamlit as st
import requests
import json
import asyncio
import pandas as pd
from datetime import datetime
import base64
from typing import Dict, List, Optional
import os
import io
import logging

# Import custom components
from components.chat_interface import ChatInterface
from components.recipe_upload import RecipeUpload
from components.admin_panel import AdminPanel

# Configure page
st.set_page_config(
    page_title="Mana Ruchulu - మన రుచులు",
    page_icon="🍛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #FF6B35, #F7931E);
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        color: white;
        margin-bottom: 20px;
    }
    
    .recipe-card {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #FF6B35;
        margin: 10px 0;
    }
    
    .ingredient-tag {
        background: #e3f2fd;
        padding: 5px 10px;
        border-radius: 15px;
        margin: 2px;
        display: inline-block;
        font-size: 12px;
    }
    
    .chat-message {
        padding: 10px;
        border-radius: 10px;
        margin: 10px 0;
    }
    
    .user-message {
        background: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    
    .bot-message {
        background: #fff3e0;
        border-left: 4px solid #ff9800;
    }
    
    .telugu-text {
        font-family: 'Noto Sans Telugu', sans-serif;
        font-size: 16px;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

class ManaRuchuluApp:
    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.chat_interface = ChatInterface(self.api_base_url)
        self.recipe_upload = RecipeUpload(self.api_base_url)
        self.admin_panel = AdminPanel(self.api_base_url)
        
        # Initialize session state
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        if 'user_recipes' not in st.session_state:
            st.session_state.user_recipes = []
        if 'selected_language' not in st.session_state:
            st.session_state.selected_language = 'telugu'
        if 'audio_enabled' not in st.session_state:
            st.session_state.audio_enabled = False
    
    def render_header(self):
        """Render main header"""
        st.markdown("""
        <div class="main-header">
            <h1>🍛 Mana Ruchulu - మన రుచులు</h1>
            <p>Traditional Telugu Recipe & Culinary Assistant</p>
            <p>తెలుగు వంటకాల సహాయకుడు</p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_sidebar(self):
        """Render sidebar with navigation and settings"""
        with st.sidebar:
            st.header("Navigation")
            
            # Language selection
            language_options = {
                'English': 'english',
                'తెలుగు': 'telugu',
                'Mixed': 'mixed'
            }
            
            selected_lang = st.selectbox(
                "Select Language / భాష ఎంచుకోండి",
                options=list(language_options.keys()),
                index=1
            )
            st.session_state.selected_language = language_options[selected_lang]
            
            # Audio settings
            st.session_state.audio_enabled = st.checkbox(
                "Enable Audio Response / ఆడియో ప్రతిస్పందన",
                value=st.session_state.audio_enabled
            )
            
            st.divider()
            
            # Navigation menu
            menu_options = [
                "🏠 Home / హోమ్",
                "💬 Chat / చాట్",
                "🔍 Search Recipes / వంటకాలు వెతకండి",
                "📤 Upload Recipe / వంటకం అప్‌లోడ్ చేయండి",
                "📊 My Recipes / నా వంటకాలు",
                "⚙️ Admin Panel / అడ్మిన్ ప్యానెల్"
            ]
            
            selected_menu = st.radio(
                "Choose Option / ఎంపిక చేయండి",
                options=menu_options
            )
            
            st.divider()
            
            # Quick recipe suggestions
            st.subheader("Popular Recipes / ప్రసిద్ధ వంటకాలు")
            popular_recipes = [
                "Gutti Vankaya Curry",
                "Pesarattu",
                "Hyderabadi Biryani",
                "Pulusu",
                "Pappu Charu",
                "Gongura Mutton"
            ]
            
            for recipe in popular_recipes:
                if st.button(recipe, key=f"popular_{recipe}"):
                    st.session_state.chat_history.append({
                        "user": f"Tell me how to make {recipe}",
                        "timestamp": datetime.now()
                    })
                    st.rerun()
        
        return selected_menu
    
    def render_home_page(self):
        """Render home page with featured content"""
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("""
            ### Welcome to Mana Ruchulu! / మన రుచులకు స్వాగతం!
            
            Your AI-powered Telugu culinary companion that helps you:
            - Discover traditional recipes from Andhra Pradesh & Telangana
            - Get cooking tips and techniques
            - Upload and share your family recipes
            - Learn about nutritional benefits of Telugu cuisine
            
            **మీ AI-శక్తితో కూడిన తెలుగు వంట సహాయకుడు:**
            - ఆంధ్రప్రదేశ్ & తెలంగాణ సాంప్రదాయ వంటకాలను కనుగొనండి
            - వంట చిట్కాలు మరియు పద్ధతులను తెలుసుకోండి
            - మీ కుటుంబ వంటకాలను అప్‌లోడ్ చేసి పంచుకోండి
            - తెలుగు వంటల పోషక విలువలను తెలుసుకోండి
            """)
            
            # Featured recipes
            st.subheader("Featured Today / నేటి ప్రత్యేకం")
            
            featured_recipes = [
                {
                    "name": "Gongura Pappu",
                    "telugu_name": "గోంగూర పప్పు",
                    "description": "Tangy lentil curry with sorrel leaves",
                    "time": "30 mins",
                    "difficulty": "Easy"
                },
                {
                    "name": "Kodi Koora",
                    "telugu_name": "కోడి కూర",
                    "description": "Spicy Andhra chicken curry",
                    "time": "45 mins",
                    "difficulty": "Medium"
                },
                {
                    "name": "Bobbatlu",
                    "telugu_name": "బొబ్బట్లు",
                    "description": "Traditional sweet stuffed flatbread",
                    "time": "60 mins",
                    "difficulty": "Hard"
                }
            ]
            
            for recipe in featured_recipes:
                with st.container():
                    st.markdown(f"""
                    <div class="recipe-card">
                        <h4>{recipe['name']} - {recipe['telugu_name']}</h4>
                        <p>{recipe['description']}</p>
                        <div>
                            <span class="ingredient-tag">⏰ {recipe['time']}</span>
                            <span class="ingredient-tag">📊 {recipe['difficulty']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"Get Recipe for {recipe['name']}", key=f"featured_{recipe['name']}"):
                        st.session_state.chat_history.append({
                            "user": f"How do I make {recipe['name']}? Please provide detailed recipe.",
                            "timestamp": datetime.now()
                        })
                        st.rerun()
    
    def render_search_page(self):
        """Render recipe search page"""
        st.header("Recipe Search / వంటక వెతకండి")
        
        # Search form
        with st.form("recipe_search_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                search_query = st.text_input(
                    "Search for recipes / వంటకాలు వెతకండి",
                    placeholder="Enter dish name, ingredient, or cuisine type..."
                )
                
                ingredients = st.text_input(
                    "Specific Ingredients / నిర్దిష్ట పదార్థాలు",
                    placeholder="tomato, onion, chicken (comma separated)"
                )
            
            with col2:
                dietary_restrictions = st.multiselect(
                    "Dietary Restrictions / ఆహార పరిమితులు",
                    ["Vegetarian", "Vegan", "Gluten-Free", "Diabetic-Friendly", "Low-Sodium"]
                )
                
                region = st.selectbox(
                    "Region / ప్రాంతం",
                    ["Any", "Coastal Andhra", "Rayalaseema", "Telangana", "Hyderabad"],
                    index=0
                )
            
            search_submitted = st.form_submit_button("Search Recipes / వెతకండి")
        
        # Display search results
        if search_submitted and search_query:
            with st.spinner("Searching for recipes... / వంటకాలు వెతుకుతున్నాం..."):
                results = self.search_recipes(
                    search_query,
                    ingredients.split(',') if ingredients else None,
                    dietary_restrictions,
                    region if region != "Any" else None
                )
                
                if results:
                    st.subheader(f"Found {len(results)} recipes / {len(results)} వంటకాలు దొరికాయి")
                    
                    for i, recipe in enumerate(results):
                        with st.expander(f"{recipe.get('name', 'Unknown Recipe')} - Score: {recipe.get('similarity_score', 0):.2f}"):
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                st.write(f"**Cuisine:** {recipe.get('cuisine', 'Unknown')}")
                                st.write(f"**Region:** {recipe.get('region', 'Unknown')}")
                                
                                if recipe.get('prep_time'):
                                    st.write(f"**Prep Time:** {recipe['prep_time']} minutes")
                                if recipe.get('cook_time'):
                                    st.write(f"**Cook Time:** {recipe['cook_time']} minutes")
                            
                            with col2:
                                if st.button(f"Get Full Recipe", key=f"recipe_{i}"):
                                    st.session_state.chat_history.append({
                                        "user": f"Give me the complete recipe for {recipe.get('name')}",
                                        "timestamp": datetime.now()
                                    })
                                    st.switch_page("pages/chat.py")
                else:
                    st.info("No recipes found. Try different search terms. / వంటకాలు దొరకలేదు. వేరే పదాలతో ప్రయత్నించండి.")
    
    def search_recipes(self, query: str, ingredients: List[str] = None, dietary_restrictions: List[str] = None, region: str = None) -> List[Dict]:
        """Search recipes via API"""
        try:
            search_data = {
                "query": query,
                "ingredients": ingredients,
                "dietary_restrictions": dietary_restrictions,
                "region": region
            }
            
            response = requests.post(
                f"{self.api_base_url}/recipes/search",
                json=search_data,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get('recipes', [])
            else:
                st.error(f"Search failed: {response.status_code}")
                return []
                
        except Exception as e:
            st.error(f"Error searching recipes: {str(e)}")
            return []
    
    def run(self):
        """Main application runner"""
        self.render_header()
        selected_menu = self.render_sidebar()
        
        # Route to appropriate page based on selection
        if "Home" in selected_menu:
            self.render_home_page()
        elif "Chat" in selected_menu:
            self.chat_interface.render()
        elif "Search" in selected_menu:
            self.render_search_page()
        elif "Upload" in selected_menu:
            self.recipe_upload.render()
        elif "My Recipes" in selected_menu:
            self.render_my_recipes()
        elif "Admin" in selected_menu:
            self.admin_panel.render()
    
    def render_my_recipes(self):
        """Render user's contributed recipes"""
        st.header("My Recipes / నా వంటకాలు")
        
        if st.session_state.user_recipes:
            for i, recipe in enumerate(st.session_state.user_recipes):
                with st.expander(f"{recipe.get('name', f'Recipe {i+1}')}"):
                    st.json(recipe)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button(f"Edit", key=f"edit_{i}"):
                            st.info("Edit functionality coming soon!")
                    with col2:
                        if st.button(f"Share", key=f"share_{i}"):
                            st.info("Share functionality coming soon!")
                    with col3:
                        if st.button(f"Delete", key=f"delete_{i}"):
                            st.session_state.user_recipes.pop(i)
                            st.rerun()
        else:
            st.info("You haven't uploaded any recipes yet. / మీరు ఇంకా వంటకాలు అప్‌లోడ్ చేయలేదు.")
            if st.button("Upload Your First Recipe / మీ మొదటి వంటకం అప్‌లోడ్ చేయండి"):
                st.switch_page("pages/upload.py")

# Initialize and run the app
if __name__ == "__main__":
    app = ManaRuchuluApp()
    app.run()