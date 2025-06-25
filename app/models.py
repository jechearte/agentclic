from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Union
from enum import Enum


class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    previous_response_id: Optional[str] = None  # Para contexto de OpenAI


class ChatResponse(BaseModel):
    response: str
    conversation_id: Optional[str] = None
    response_id: Optional[str] = None  # ID de respuesta de OpenAI para contexto


class AgentStyles(BaseModel):
    primary_color: str = "#007bff"
    secondary_color: str = "#6c757d"
    border_radius: str = "12px"
    position: str = "bottom-right"
    widget_size: str = "medium"
    font_family: str = "Arial, sans-serif"


class AgentMessages(BaseModel):
    welcome: str = "¡Hola! ¿En qué puedo ayudarte?"
    placeholder: str = "Escribe tu mensaje..."
    error: str = "Lo siento, ha ocurrido un error. Inténtalo de nuevo."


class PublicAgentConfig(BaseModel):
    """Configuración pública del agente (sin información confidencial)"""
    id: str
    name: str
    type: str  # Como string para evitar importar el enum
    styles: AgentStyles
    messages: AgentMessages
    enabled: bool = True
    allowed_domains: List[str] = []


class AgentType(str, Enum):
    OPENAI = "openai"
    N8N = "n8n"
    CUSTOM = "custom"


class CustomBackendConfig(BaseModel):
    """Configuración para backends personalizados"""
    headers: Dict[str, str] = {}
    body_structure: Dict[str, Any] = {}
    response_path: str = "response"  # Ruta para extraer la respuesta del JSON


class OpenAIConfig(BaseModel):
    """Configuración específica para OpenAI Responses API"""
    api_key: Optional[str] = None  # Opcional, se usa OPENAI_API_KEY del .env si no se especifica
    model: str = "gpt-4.1-mini"
    instructions: str = "Eres un asistente virtual útil y amigable."
    max_output_tokens: int = 2000
    temperature: float = 0.3
    top_p: float = 1.0
    tools: List[Dict[str, Any]] = []  # Tools configurables para OpenAI


class N8NConfig(BaseModel):
    """Configuración específica para workflows de n8n"""
    webhook_url: str


class AgentConfig(BaseModel):
    id: str
    name: str
    type: AgentType
    styles: AgentStyles
    messages: AgentMessages
    enabled: bool = True
    allowed_domains: List[str] = []
    
    # Campos opcionales según el tipo
    chat_endpoint: Optional[str] = None  # Solo para type=custom
    custom_config: Optional[CustomBackendConfig] = None  # Solo para type=custom
    openai_config: Optional[OpenAIConfig] = None  # Solo para type=openai
    n8n_config: Optional[N8NConfig] = None  # Solo para type=n8n
    
    def to_public_config(self) -> PublicAgentConfig:
        """Convierte la configuración completa a configuración pública"""
        return PublicAgentConfig(
            id=self.id,
            name=self.name,
            type=self.type.value,
            styles=self.styles,
            messages=self.messages,
            enabled=self.enabled,
            allowed_domains=self.allowed_domains
        ) 