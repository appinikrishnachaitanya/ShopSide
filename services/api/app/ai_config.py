"""Google ADK model client configuration for Vertex AI and Developer API."""
import os
from google import genai
from fastapi import HTTPException

def configured_client():
    provider=os.getenv('AI_PROVIDER','vertex')
    if provider=='vertex':
        project=os.getenv('GOOGLE_CLOUD_PROJECT')
        location=os.getenv('GOOGLE_CLOUD_LOCATION','global')
        if project:
            # Standard Vertex AI uses Application Default Credentials, never API-key substitution.
            return genai.Client(vertexai=True,project=project,location=location)
        key=os.getenv('VERTEX_API_KEY') or os.getenv('GEMINI_API_KEY')
        if key:
            # Vertex AI express mode supports Google Cloud API keys without a project selector.
            return genai.Client(vertexai=True,api_key=key)
        raise HTTPException(503,'Configure Vertex AI project and ADC, or a Vertex AI express-mode API key')
    if provider=='developer':
        key=os.getenv('GEMINI_API_KEY')
        if not key:raise HTTPException(503,'Configure Gemini Developer API key')
        return genai.Client(api_key=key)
    raise HTTPException(503,'AI_PROVIDER must be vertex or developer')
