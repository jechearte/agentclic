from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import httpx
import json
from pathlib import Path
from .config import config_manager
from .models import ChatMessage, ChatResponse, PublicAgentConfig
from .chat_service import ChatService
from .metrics_service import metrics_service

app = FastAPI(
    title="Embeddable Chatbot API",
    description="API para widgets de chatbot embebibles",
    version="1.0.0"
)

# Configurar CORS para permitir embeds desde cualquier dominio
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def root():
    """Endpoint de health check"""
    agents = config_manager.get_all_agents()
    return {
        "message": "Embeddable Chatbot API funcionando",
        "agents_loaded": len(agents),
        "agents": [
            {
                "id": agent.id,
                "name": agent.name,
                "type": agent.type.value,
                "enabled": agent.enabled
            }
            for agent in agents.values()
        ]
    }


@app.get("/widget.js", response_class=PlainTextResponse)
async def get_widget_script():
    """Sirve el script JavaScript del widget embebible"""
    try:
        with open("app/static/widget.js", "r", encoding="utf-8") as f:
            script_content = f.read()
        return script_content
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Widget script no encontrado")


@app.get("/test", response_class=HTMLResponse)
async def get_test_page():
    """Sirve la página de prueba del widget con selector de agentes"""
    try:
        with open("test.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return html_content
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Página de prueba no encontrada")


@app.get("/test/{agent_id}", response_class=HTMLResponse)
async def get_test_page_with_agent(agent_id: str):
    """Sirve la página de prueba del widget con un agente específico (página en blanco)"""
    # Verificar que el agente existe y está habilitado
    agent = config_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_id}' no encontrado")
    
    if not agent.enabled:
        raise HTTPException(status_code=403, detail=f"Agente '{agent_id}' está deshabilitado")
    
    try:
        # Crear HTML en blanco con el agente específico
        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test - {agent.name}</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            background: white;
            font-family: Arial, sans-serif;
        }}
    </style>
</head>
<body>
    <!-- Página completamente blanca para pruebas del widget -->
    
    <!-- Widget del chatbot -->
    <script src="/widget.js" data-agent-id="{agent_id}"></script>
</body>
</html>"""
        
        return html_content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando página de prueba: {str(e)}")


@app.get("/public-config/{agent_id}", response_model=PublicAgentConfig)
async def get_public_agent_config(agent_id: str):
    """Obtiene solo la configuración pública de un agente (sin información confidencial)"""
    agent = config_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_id}' no encontrado")
    
    if not agent.enabled:
        raise HTTPException(status_code=403, detail=f"Agente '{agent_id}' está deshabilitado")
    
    return agent.to_public_config()


@app.get("/config/{agent_id}")
async def get_agent_config(agent_id: str):
    """Obtiene la configuración completa de un agente específico (INCLUYE INFORMACIÓN CONFIDENCIAL)"""
    agent = config_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_id}' no encontrado")
    
    if not agent.enabled:
        raise HTTPException(status_code=403, detail=f"Agente '{agent_id}' está deshabilitado")
    
    return agent


@app.post("/chat/{agent_id}")
async def proxy_chat(agent_id: str, message: ChatMessage):
    """Proxy para enviar mensajes según el tipo de agente"""
    agent = config_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_id}' no encontrado")
    
    if not agent.enabled:
        raise HTTPException(status_code=403, detail=f"Agente '{agent_id}' está deshabilitado")
    
    # Registrar mensaje en métricas ANTES de procesarlo
    if message.conversation_id:
        metrics_service.record_message(agent_id, message.conversation_id)
    
    try:
        return await ChatService.send_message(agent, message)
        
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Timeout al contactar con el chatbot")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Error del chatbot: {e.response.status_code}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@app.get("/agents")
async def list_agents():
    """Lista todos los agentes disponibles con su tipo"""
    agents = config_manager.get_all_agents()
    return {
        "agents": [
            {
                "id": agent.id,
                "name": agent.name,
                "type": agent.type.value,
                "enabled": agent.enabled
            }
            for agent in agents.values()
        ]
    }


@app.post("/reload-config")
async def reload_configuration():
    """Recarga las configuraciones de agentes (útil para desarrollo)"""
    config_manager.reload_agents()
    agents = config_manager.get_all_agents()
    return {
        "message": "Configuraciones recargadas",
        "agents_loaded": len(agents),
        "agents": list(agents.keys())
    }


@app.get("/metrics/download")
async def download_metrics():
    """Descarga el archivo CSV con todas las métricas"""
    csv_file = Path("app/metrics/messages.csv")
    
    if not csv_file.exists():
        raise HTTPException(status_code=404, detail="Archivo de métricas no encontrado")
    
    return FileResponse(
        path=csv_file,
        filename="chatbot_metrics.csv",
        media_type="text/csv"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 