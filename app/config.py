import os
import json
from typing import Dict, Optional
from pathlib import Path
from dotenv import load_dotenv
from .models import AgentConfig

# Cargar variables de entorno
load_dotenv()

def get_openai_api_key() -> Optional[str]:
    """Obtiene la API key de OpenAI desde variables de entorno"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY no encontrada en variables de entorno")
    return api_key

class ConfigManager:
    def __init__(self):
        self.agents_dir = Path("app/agents")
        self.agents: Dict[str, AgentConfig] = {}
        self.load_agents()
    
    def load_agents(self):
        """Carga todos los agentes desde archivos JSON"""
        self.agents.clear()
        
        if not self.agents_dir.exists():
            print(f"Directorio {self.agents_dir} no existe")
            return
        
        for json_file in self.agents_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    agent_data = json.load(f)
                
                agent = AgentConfig(**agent_data)
                self.agents[agent.id] = agent
                print(f"Agente cargado: {agent.id} ({agent.name})")
                
            except Exception as e:
                print(f"Error cargando {json_file}: {e}")
    
    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """Obtiene un agente por su ID"""
        return self.agents.get(agent_id)
    
    def get_all_agents(self) -> Dict[str, AgentConfig]:
        """Obtiene todos los agentes"""
        return self.agents
    
    def reload_agents(self):
        """Recarga todos los agentes"""
        self.load_agents()

# Instancia global del gestor de configuración
config_manager = ConfigManager() 