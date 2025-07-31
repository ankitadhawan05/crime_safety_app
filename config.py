# config.py - Configuration and Environment Variables Handler
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class to handle environment variables"""
    
    # OpenRouteService Configuration
    OPENROUTESERVICE_API_KEY = os.getenv('OPENROUTESERVICE_API_KEY')
    OPENROUTESERVICE_URL = os.getenv('OPENROUTESERVICE_URL', 'https://api.openrouteservice.org/v2/directions')
    
    # OSRM Configuration
    OSRM_HOST = os.getenv('OSRM_HOST', 'localhost')
    OSRM_PORT = os.getenv('OSRM_PORT', '5000')
    
    # Database Configuration (if needed)
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # Secret Keys (if needed)
    SECRET_KEY = os.getenv('SECRET_KEY')
    
    # Deployment Detection
    IS_DEPLOYED = bool(
        os.getenv('STREAMLIT_SHARING') or 
        os.getenv('HEROKU') or 
        os.getenv('RAILWAY_ENVIRONMENT') or
        os.getenv('VERCEL') or
        os.getenv('NETLIFY')
    )
    
    @classmethod
    def get_routing_config(cls):
        """Get routing service configuration"""
        if cls.IS_DEPLOYED:
            return {
                'osrm': {
                    'host': 'router.project-osrm.org',
                    'port': '',
                    'protocol': 'https',
                    'base_url': 'https://router.project-osrm.org'
                },
                'openrouteservice': {
                    'base_url': cls.OPENROUTESERVICE_URL,
                    'api_key': cls.OPENROUTESERVICE_API_KEY
                }
            }
        else:
            return {
                'osrm': {
                    'host': cls.OSRM_HOST,
                    'port': cls.OSRM_PORT,
                    'protocol': 'http',
                    'base_url': f'http://{cls.OSRM_HOST}:{cls.OSRM_PORT}'
                },
                'openrouteservice': {
                    'base_url': cls.OPENROUTESERVICE_URL,
                    'api_key': cls.OPENROUTESERVICE_API_KEY
                }
            }
    
    @classmethod
    def validate_config(cls):
        """Validate that required environment variables are set"""
        missing_vars = []
        
        if not cls.OPENROUTESERVICE_API_KEY:
            missing_vars.append('OPENROUTESERVICE_API_KEY')
        
        if missing_vars:
            print(f"⚠️ Warning: Missing environment variables: {', '.join(missing_vars)}")
            print("Some features may not work properly.")
        
        return len(missing_vars) == 0

# Create a global config instance
config = Config()

# Validate configuration on import
config.validate_config()