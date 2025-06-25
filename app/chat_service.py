import httpx
from typing import Dict, Any
from .models import AgentConfig, ChatMessage, ChatResponse
from .config import get_openai_api_key


class ChatService:
    """Servicio para manejar comunicación con diferentes backends"""
    
    @staticmethod
    async def send_message(agent: AgentConfig, message: ChatMessage) -> ChatResponse:
        """Envía mensaje según el tipo de agente"""
        if agent.type == "openai":
            return await ChatService._send_to_openai(agent, message)
        elif agent.type == "n8n":
            return await ChatService._send_to_n8n(agent, message)
        elif agent.type == "custom":
            return await ChatService._send_to_custom(agent, message)
        else:
            raise ValueError(f"Tipo de agente no soportado: {agent.type}")
    
    @staticmethod
    async def _send_to_openai(agent: AgentConfig, message: ChatMessage) -> ChatResponse:
        """Envía mensaje a OpenAI Responses API"""
        if not agent.openai_config:
            raise ValueError("Configuración de OpenAI faltante")
        
        # Configuración para la nueva Responses API
        url = "https://oai-swe-chatbotllm-dev.openai.azure.com/openai/v1/responses?api-version=preview"
        
        # Usar API key desde variables de entorno o desde configuración
        api_key = agent.openai_config.api_key or get_openai_api_key()
        
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json"
        }
        
        # Estructura de body para Responses API
        body = {
            "model": agent.openai_config.model,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": agent.openai_config.instructions
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": message.message
                        }
                    ]
                }
            ],
            "text": {
                "format": {
                    "type": "text"
                }
            },
            "reasoning": {},
            "tools": agent.openai_config.tools,
            "temperature": agent.openai_config.temperature,
            "max_output_tokens": agent.openai_config.max_output_tokens,
            "top_p": agent.openai_config.top_p,
            "store": True
        }
        
        # Añadir previous_response_id si está disponible para mantener contexto
        if message.previous_response_id:
            body["previous_response_id"] = message.previous_response_id
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=body, timeout=30.0)
            response.raise_for_status()
            
            data = response.json()
            
            # Extraer respuesta de la nueva estructura de Responses API
            # Buscar el mensaje del asistente en el array output
            try:
                chat_response = None
                
                # Buscar en output el elemento que sea un mensaje del asistente
                for output_item in data.get("output", []):
                    if output_item.get("type") == "message" and output_item.get("role") == "assistant":
                        # Encontrar el contenido de texto
                        content_items = output_item.get("content", [])
                        for content_item in content_items:
                            if content_item.get("type") == "output_text":
                                chat_response = content_item.get("text", "")
                                break
                        if chat_response:
                            break
                
                # Si no se encontró respuesta, usar fallback
                if not chat_response:
                    chat_response = f"Error al procesar respuesta: No se encontró mensaje del asistente"
                    
            except (KeyError, IndexError, TypeError) as e:
                # Fallback en caso de estructura diferente
                chat_response = f"Error al procesar respuesta: {str(e)}"
            
            # Extraer response_id para futuras peticiones
            response_id = data.get("id")
            
            return ChatResponse(
                response=chat_response,
                conversation_id=message.conversation_id,
                response_id=response_id
            )
    
    @staticmethod
    async def _send_to_n8n(agent: AgentConfig, message: ChatMessage) -> ChatResponse:
        """Envía mensaje a workflow de n8n"""
        if not agent.n8n_config:
            raise ValueError("Configuración de n8n faltante")
        
        # Estructura de body para n8n
        body = {
            "action": "sendMessage",
            "sessionId": message.conversation_id,
            "chatInput": message.message
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                agent.n8n_config.webhook_url, 
                headers=headers, 
                json=body, 
                timeout=30.0
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extraer respuesta de n8n (soporta tanto array como objeto)
            try:
                chat_response = ""
                
                if isinstance(data, list) and len(data) > 0:
                    # Formato array: [{"output": "mensaje"}]
                    chat_response = data[0].get("output", "")
                elif isinstance(data, dict):
                    # Formato objeto: {"output": "mensaje"}
                    chat_response = data.get("output", "")
                    
                    # Si no hay 'output', buscar otras claves comunes
                    if not chat_response:
                        possible_keys = ["response", "message", "text", "result"]
                        for key in possible_keys:
                            if key in data:
                                chat_response = data[key]
                                break
                
                # Validar que se obtuvo una respuesta válida
                if not chat_response:
                    chat_response = f"Error: No se encontró respuesta en los datos de n8n"
                    
            except (KeyError, IndexError, TypeError) as e:
                chat_response = f"Error al procesar respuesta de n8n: {str(e)}"
            
            return ChatResponse(
                response=chat_response,
                conversation_id=message.conversation_id
            )
    
    @staticmethod
    async def _send_to_custom(agent: AgentConfig, message: ChatMessage) -> ChatResponse:
        """Envía mensaje a backend personalizado"""
        if not agent.chat_endpoint or not agent.custom_config:
            raise ValueError("Configuración de backend personalizado faltante")
        
        # Usar configuración personalizada
        headers = agent.custom_config.headers
        
        # Construir body usando la estructura configurada
        body = ChatService._build_custom_body(
            agent.custom_config.body_structure, 
            message
        )
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                agent.chat_endpoint, 
                headers=headers, 
                json=body, 
                timeout=30.0
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extraer respuesta usando la ruta configurada
            chat_response = ChatService._extract_response(
                data, 
                agent.custom_config.response_path
            )
            
            conversation_id = data.get("conversation_id", message.conversation_id)
            
            return ChatResponse(
                response=chat_response,
                conversation_id=conversation_id
            )
    
    @staticmethod
    def _build_custom_body(structure: Dict[str, Any], message: ChatMessage) -> Dict[str, Any]:
        """Construye el body usando la estructura configurada"""
        body = {}
        
        for key, value in structure.items():
            if value == "{message}":
                body[key] = message.message
            elif value == "{conversation_id}":
                body[key] = message.conversation_id
            else:
                body[key] = value
        
        return body
    
    @staticmethod
    def _extract_response(data: Dict[str, Any], path: str) -> str:
        """Extrae la respuesta usando la ruta configurada"""
        keys = path.split(".")
        result = data
        
        for key in keys:
            if isinstance(result, dict) and key in result:
                result = result[key]
            else:
                return str(data)  # Fallback
        
        return str(result) 