import httpx
import re
import os
import json
from typing import Dict, Any
from pinecone import Pinecone
from .models import AgentConfig, ChatMessage, ChatResponse
from .config import get_openai_api_key


class ChatService:
    """Servicio para manejar comunicación con diferentes backends"""
    
    @staticmethod
    def _get_pinecone_client():
        """Obtiene cliente de Pinecone configurado"""
        print(f"[Pinecone] Intentando obtener cliente...")
        api_key = os.getenv('PINECONE_API_KEY')
        if not api_key:
            print(f"[Pinecone] ERROR: PINECONE_API_KEY no encontrada en variables de entorno")
            raise ValueError("PINECONE_API_KEY no encontrada en variables de entorno")
        print(f"[Pinecone] API key encontrada, creando cliente...")
        try:
            client = Pinecone(api_key=api_key)
            print(f"[Pinecone] Cliente creado exitosamente")
            return client
        except Exception as e:
            print(f"[Pinecone] ERROR al crear cliente: {str(e)}")
            raise
    
    @staticmethod
    async def _generate_embedding(text: str):
        """Genera embedding usando Azure OpenAI"""
        print(f"[Embeddings] Generando embedding para: '{text}'")
        
        # Configuración del endpoint
        endpoint = "https://oai-swe-chatbotllm-dev.openai.azure.com/openai/deployments/3large-swe-ChatbotLLM-dev/embeddings"
        api_version = "2025-01-01-preview"
        
        # URL completa
        url = f"{endpoint}?api-version={api_version}"
        
        # Obtener API key
        api_key = get_openai_api_key()
        if not api_key:
            print(f"[Embeddings] ERROR: No se pudo obtener API key de OpenAI")
            raise ValueError("API key de OpenAI no encontrada")
        
        # Headers
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json"
        }
        
        # Body
        body = {
            "input": text
        }
        
        print(f"[Embeddings] Enviando petición a Azure OpenAI...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=body, timeout=30.0)
                response.raise_for_status()
                
                data = response.json()
                embedding = data['data'][0]['embedding']
                
                print(f"[Embeddings] Embedding generado exitosamente (dimensión: {len(embedding)})")
                return embedding
                
        except Exception as e:
            print(f"[Embeddings] ERROR generando embedding: {type(e).__name__}: {str(e)}")
            import traceback
            print(f"[Embeddings] Traceback completo:")
            traceback.print_exc()
            raise
    
    @staticmethod
    async def _search_pinecone(index_name: str, query: str, k: int = 20):
        """Realiza búsqueda semántica en Pinecone"""
        print(f"[Pinecone] Iniciando búsqueda en índice '{index_name}' con query: '{query}'")
        try:
            # Generar embedding del query
            print(f"[Pinecone] Generando embedding para la query...")
            query_vector = await ChatService._generate_embedding(query)
            
            print(f"[Pinecone] Obteniendo cliente...")
            pc = ChatService._get_pinecone_client()
            
            print(f"[Pinecone] Conectando al índice '{index_name}'...")
            index = pc.Index(index_name)
            
            print(f"[Pinecone] Ejecutando query con k={k} usando vector generado...")
            # Realizar búsqueda usando el vector generado
            results = index.query(
                vector=query_vector,  # Usar el vector generado
                top_k=k,
                include_metadata=True,
                include_values=False
            )
            
            print(f"[Pinecone] Query ejecutada, procesando resultados...")
            print(f"[Pinecone] Respuesta cruda de Pinecone: {results}")
            
            # Formatear resultados
            formatted_results = []
            matches = results.get('matches', [])
            print(f"[Pinecone] Encontrados {len(matches)} matches")
            
            for i, match in enumerate(matches):
                result_data = {
                    'id': match.get('id', ''),
                    'score': match.get('score', 0),
                    'metadata': match.get('metadata', {})
                }
                formatted_results.append(result_data)
                print(f"[Pinecone] Match {i+1}: ID={result_data['id']}, Score={result_data['score']}")
            
            print(f"[Pinecone] Búsqueda completada exitosamente con {len(formatted_results)} resultados")
            return formatted_results
            
        except Exception as e:
            print(f"[Pinecone] ERROR en búsqueda: {type(e).__name__}: {str(e)}")
            import traceback
            print(f"[Pinecone] Traceback completo:")
            traceback.print_exc()
            return []
    
    @staticmethod
    async def _process_openai_response_with_tools(client, url, headers, body, agent):
        """Procesa respuestas de OpenAI que pueden contener function_calls recursivamente"""
        max_iterations = 5  # Evitar loops infinitos
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            print(f"[OpenAI] Iteración {iteration} de procesamiento de tools...")
            
            response = await client.post(url, headers=headers, json=body, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            
            # Verificar si hay nuevas function_calls
            function_calls_to_process = []
            for output_item in data.get("output", []):
                if output_item.get("type") == "function_call":
                    function_name = output_item.get("name", "unknown")
                    print(f"[OpenAI] 🔧 LLM quiere usar la tool (iteración {iteration}): '{function_name}'")
                    if function_name == "semantic_search":
                        arguments = output_item.get("arguments", {})
                        query = arguments.get("query", "")
                        print(f"[OpenAI] 🔍 Query solicitada (iteración {iteration}): '{query}'")
                    function_calls_to_process.append(output_item)
            
            # Si no hay más function_calls, retornar la respuesta final
            if not function_calls_to_process:
                print(f"[OpenAI] Procesamiento completado en {iteration} iteración(es)")
                return data
            
            # Procesar las nuevas function_calls
            print(f"[OpenAI] Procesando {len(function_calls_to_process)} function_calls en iteración {iteration}...")
            
            function_outputs = []
            for function_call in function_calls_to_process:
                call_id = function_call.get("call_id")
                function_name = function_call.get("name")
                arguments_str = function_call.get("arguments", "{}")
                
                if function_name == "semantic_search" and agent.openai_config.pinecone_index:
                    print(f"[OpenAI-Recursivo] 📝 Arguments string: {arguments_str}")
                    try:
                        arguments = json.loads(arguments_str)
                        query = arguments.get("query", "")
                    except json.JSONDecodeError as e:
                        print(f"[OpenAI-Recursivo] ❌ Error parseando arguments: {e}")
                        query = ""
                    print(f"[OpenAI-Recursivo] 🔍 Procesando semantic_search (iteración {iteration}) con query: '{query}'")
                    print(f"[OpenAI-Recursivo] 📋 Call ID: {call_id}")
                    print(f"[OpenAI-Recursivo] 🎯 Índice Pinecone: {agent.openai_config.pinecone_index}")
                    
                    # Realizar búsqueda en Pinecone
                    print(f"[OpenAI-Recursivo] 🚀 Iniciando búsqueda en Pinecone (iteración {iteration})...")
                    search_results = await ChatService._search_pinecone(
                        agent.openai_config.pinecone_index, 
                        query, 
                        k=20
                    )
                    
                    # Extraer solo los metadatos de los resultados
                    metadata_only = []
                    for result in search_results:
                        metadata = result.get('metadata', {})
                        if metadata:  # Solo añadir si hay metadatos
                            metadata_only.append(metadata)
                    
                    # Formatear resultados para OpenAI (solo metadatos)
                    result_output = {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps(metadata_only, ensure_ascii=False)
                    }
                    function_outputs.append(result_output)
            
            # Preparar para la siguiente iteración
            if function_outputs:
                current_response_id = data.get("id")
                body = {
                    "model": agent.openai_config.model,
                    "input": function_outputs,
                    "previous_response_id": current_response_id,
                    "text": {
                        "format": {
                            "type": "text"
                        }
                    },
                    "reasoning": {},
                    "tools": body["tools"],
                    "max_output_tokens": agent.openai_config.max_output_tokens,
                    "store": True
                }
                
                # Solo añadir temperature y top_p si el modelo NO es o4-mini
                if agent.openai_config.model != "o4-mini":
                    body["temperature"] = agent.openai_config.temperature
                    body["top_p"] = agent.openai_config.top_p
                print(f"[OpenAI] Preparando iteración {iteration + 1} con previous_response_id: {current_response_id}")
            else:
                # No hay function_outputs para procesar, retornar respuesta actual
                return data
        
        print(f"[OpenAI] ADVERTENCIA: Se alcanzó el máximo de iteraciones ({max_iterations})")
        return data
    
    @staticmethod
    def _convert_markdown_to_html(text: str) -> str:
        """Convierte markdown básico a HTML"""
        # 1. Convertir enlaces markdown [texto](url) a enlaces HTML
        markdown_link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        
        def replace_link(match):
            link_text = match.group(1)
            url = match.group(2)
            # Asegurar que la URL tenga protocolo
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{link_text}</a>'
        
        text = re.sub(markdown_link_pattern, replace_link, text)
        
        # 2. Convertir negritas **texto** a <strong>texto</strong>
        text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
        
        # 3. Convertir cursivas *texto* a <em>texto</em>
        text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
        
        # 4. Convertir listas con soporte para anidación
        lines = text.split('\n')
        processed_lines = []
        list_stack = []  # Para manejar listas anidadas
        
        for line in lines:
            # Detectar el nivel de indentación
            stripped_line = line.strip()
            indent_level = (len(line) - len(line.lstrip())) // 2  # Asumiendo 2 espacios por nivel
            
            if stripped_line.startswith('- '):
                # Es un elemento de lista
                list_item = stripped_line[2:].strip()  # Remover "- "
                
                # Manejar niveles de anidación
                while len(list_stack) > indent_level:
                    processed_lines.append('</ul>')
                    list_stack.pop()
                
                if len(list_stack) == indent_level:
                    # Mismo nivel, continúa la lista actual
                    pass
                else:
                    # Nuevo nivel de anidación
                    processed_lines.append('<ul>')
                    list_stack.append(indent_level)
                
                processed_lines.append(f'<li>{list_item}</li>')
                
            elif stripped_line:
                # No es un elemento de lista, cerrar todas las listas abiertas
                while list_stack:
                    processed_lines.append('</ul>')
                    list_stack.pop()
                
                # Añadir línea normal si no está vacía
                processed_lines.append(stripped_line)
            else:
                # Línea vacía - preservar como separador de párrafos
                if not list_stack:  # Solo añadir líneas vacías fuera de listas
                    processed_lines.append('')
        
        # Cerrar listas que quedaron abiertas
        while list_stack:
            processed_lines.append('</ul>')
            list_stack.pop()
        
        # 5. Procesar líneas para crear HTML con saltos apropiados
        result_parts = []
        for i, line in enumerate(processed_lines):
            if line == '':
                # Línea vacía = separador de párrafos
                if result_parts and not result_parts[-1].endswith('<br><br>'):
                    result_parts.append('<br><br>')
            elif line.startswith('<ul>') or line.startswith('</ul>') or line.startswith('<li>'):
                # Elementos de lista - añadir sin <br>
                result_parts.append(line)
            else:
                # Texto normal - añadir con <br> si no es el primer elemento
                if result_parts and not result_parts[-1].endswith(('<ul>', '</ul>', '<br>', '<br><br>')):
                    result_parts.append('<br>')
                result_parts.append(line)
        
        text = ''.join(result_parts)
        
        # 6. Limpiar múltiples <br> seguidos y espacios
        text = re.sub(r'(<br>\s*){3,}', '<br><br>', text)
        text = re.sub(r'<br></ul>', '</ul>', text)  # Limpiar <br> antes de </ul>
        text = re.sub(r'<ul><br>', '<ul>', text)    # Limpiar <br> después de <ul>
        
        return text
    
    @staticmethod
    async def send_message(agent: AgentConfig, message: ChatMessage) -> ChatResponse:
        """Envía mensaje según el tipo de agente"""
        if agent.type == "openai":
            response = await ChatService._send_to_openai(agent, message)
        elif agent.type == "n8n":
            response = await ChatService._send_to_n8n(agent, message)
        elif agent.type == "custom":
            response = await ChatService._send_to_custom(agent, message)
        else:
            raise ValueError(f"Tipo de agente no soportado: {agent.type}")
        
        # Convertir enlaces markdown a HTML en la respuesta
        response.response = ChatService._convert_markdown_to_html(response.response)
        
        return response
    
    @staticmethod
    async def _send_to_openai(agent: AgentConfig, message: ChatMessage) -> ChatResponse:
        """Envía mensaje a OpenAI Responses API"""
        print(f"[OpenAI] 🚀 Iniciando _send_to_openai")
        print(f"[OpenAI] 👤 Mensaje del usuario: '{message.message}'")
        
        if not agent.openai_config:
            print(f"[OpenAI] ❌ ERROR: Configuración de OpenAI faltante")
            raise ValueError("Configuración de OpenAI faltante")
        
        print(f"[OpenAI] ✅ Configuración de OpenAI encontrada")
        print(f"[OpenAI] 🔧 Pinecone index configurado: {agent.openai_config.pinecone_index}")
        
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
            "max_output_tokens": agent.openai_config.max_output_tokens,
            "store": True
        }
        
        # Solo añadir temperature y top_p si el modelo NO es o4-mini
        if agent.openai_config.model != "o4-mini":
            body["temperature"] = agent.openai_config.temperature
            body["top_p"] = agent.openai_config.top_p
            print(f"[OpenAI] Añadiendo temperature y top_p para modelo: {agent.openai_config.model}")
        else:
            print(f"[OpenAI] Omitiendo temperature y top_p para modelo o4-mini")
        
        # Añadir tool de semantic_search si está configurado Pinecone
        if agent.openai_config.pinecone_index:
            semantic_search_tool = {
                "type": "function",
                "name": "semantic_search",
                "description": "Permite realizar búsquedas semánticas en un índice de Pinecone",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Término de búsqueda"
                        }
                    },
                    "required": ["query"]
                }
            }
            # Añadir la tool al body (copiando las tools existentes + la nueva)
            body["tools"] = body["tools"] + [semantic_search_tool]
            print(f"[OpenAI] Añadiendo tool semantic_search para índice: {agent.openai_config.pinecone_index}")

        # Añadir include si el agente tiene la tool file_search
        if agent.openai_config.tools:
            for tool in agent.openai_config.tools:
                if isinstance(tool, dict) and tool.get("type") == "file_search":
                    body["include"] = ["file_search_call.results"]
                    print(f"[OpenAI] Añadiendo include file_search_call.results al body")
                    break
        
        # Añadir previous_response_id si está disponible para mantener contexto
        if message.previous_response_id:
            body["previous_response_id"] = message.previous_response_id
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=body, timeout=30.0)
            response.raise_for_status()
            
            data = response.json()
            
            # Verificar si hay function_calls que necesiten procesarse
            function_calls_to_process = []
            for output_item in data.get("output", []):
                if output_item.get("type") == "function_call":
                    function_name = output_item.get("name", "unknown")
                    print(f"[OpenAI] 🔧 LLM quiere usar la tool: '{function_name}'")
                    print(f"[OpenAI] Output item: {output_item}")
                    if function_name == "semantic_search":
                        arguments_str = output_item.get("arguments", "{}")
                        print(f"[OpenAI] 📝 Arguments string: {arguments_str}")
                        try:
                            arguments = json.loads(arguments_str)
                            query = arguments.get("query", "")
                            print(f"[OpenAI] 🔍 Query solicitada: '{query}'")
                        except json.JSONDecodeError as e:
                            print(f"[OpenAI] ❌ Error parseando arguments: {e}")
                            query = ""
                    function_calls_to_process.append(output_item)
            
            # Si hay function_calls, procesarlas y hacer una segunda petición
            if function_calls_to_process:
                print(f"[OpenAI] ✅ Procesando {len(function_calls_to_process)} function_calls...")
                
                # Procesar cada function_call
                function_outputs = []
                for function_call in function_calls_to_process:
                    call_id = function_call.get("call_id")
                    function_name = function_call.get("name")
                    arguments_str = function_call.get("arguments", "{}")
                    
                    if function_name == "semantic_search" and agent.openai_config.pinecone_index:
                        print(f"[OpenAI] 📝 Arguments string: {arguments_str}")
                        try:
                            arguments = json.loads(arguments_str)
                            query = arguments.get("query", "")
                        except json.JSONDecodeError as e:
                            print(f"[OpenAI] ❌ Error parseando arguments: {e}")
                            query = ""
                        print(f"[OpenAI] 🔍 Procesando function_call semantic_search con query: '{query}'")
                        print(f"[OpenAI] 📋 Call ID: {call_id}")
                        print(f"[OpenAI] 🎯 Índice Pinecone: {agent.openai_config.pinecone_index}")
                        
                        # Realizar búsqueda en Pinecone
                        print(f"[OpenAI] 🚀 Iniciando búsqueda en Pinecone...")
                        search_results = await ChatService._search_pinecone(
                            agent.openai_config.pinecone_index, 
                            query, 
                            k=20
                        )
                        
                        # Extraer solo los metadatos de los resultados
                        metadata_only = []
                        for result in search_results:
                            metadata = result.get('metadata', {})
                            if metadata:  # Solo añadir si hay metadatos
                                metadata_only.append(metadata)
                        
                        # Formatear resultados para OpenAI (solo metadatos)
                        result_output = {
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": json.dumps(metadata_only, ensure_ascii=False)
                        }
                        function_outputs.append(result_output)
                
                # Hacer segunda petición a OpenAI con los resultados de las function_calls
                if function_outputs:
                    # Extraer response_id de la primera petición
                    first_response_id = data.get("id")
                    
                    # Crear nuevo body solo con los resultados de las function_calls
                    second_body = {
                        "model": agent.openai_config.model,
                        "input": function_outputs,  # Solo los resultados, no concatenar
                        "previous_response_id": first_response_id,  # ID de la primera respuesta
                        "text": {
                            "format": {
                                "type": "text"
                            }
                        },
                        "reasoning": {},
                        "tools": body["tools"],  # Mantener las tools por si quiere usarlas otra vez
                        "max_output_tokens": agent.openai_config.max_output_tokens,
                        "store": True
                    }
                    
                    # Solo añadir temperature y top_p si el modelo NO es o4-mini
                    if agent.openai_config.model != "o4-mini":
                        second_body["temperature"] = agent.openai_config.temperature
                        second_body["top_p"] = agent.openai_config.top_p
                    
                    print(f"[OpenAI] Enviando segunda petición con resultados de function_calls...")
                    print(f"[OpenAI] Usando previous_response_id: {first_response_id}")
                    
                    # Procesar peticiones adicionales en caso de que OpenAI quiera usar tools múltiples veces
                    data = await ChatService._process_openai_response_with_tools(
                        client, url, headers, second_body, agent
                    )
            
            # DEBUG: Imprimir información específica de file_search_call
            for output_item in data.get("output", []):
                if output_item.get("type") == "file_search_call":
                    print(f"\n[OpenAI] FILE SEARCH CALL:")
                    print("-" * 40)
                    
                    # Imprimir queries utilizadas
                    queries = output_item.get("queries", [])
                    print(f"Queries utilizadas ({len(queries)}):")
                    for i, query in enumerate(queries, 1):
                        print(f"  {i}. {query}")
                    
                    # Imprimir resultados obtenidos
                    results = output_item.get("results", [])
                    print(f"\nResultados obtenidos ({len(results)}):")
                    for i, result in enumerate(results, 1):
                        filename = result.get("filename", "N/A")
                        score = result.get("score", 0)
                        full_text = result.get("text", "")
                        print(f"  {i}. Archivo: {filename}")
                        print(f"     Score: {score:.4f}")
                        print(f"     Texto completo:")
                        print(f"     {full_text}")
                        print("-" * 20)
                    
                    print("-" * 40)
            
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
                else:
                    print(f"[OpenAI] Respuesta: {chat_response}")
                    
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