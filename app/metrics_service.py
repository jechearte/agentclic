import csv
import threading
from datetime import datetime
from pathlib import Path

class MetricsService:
    def __init__(self):
        self.csv_file = Path("app/metrics/messages.csv")
        self.csv_file.parent.mkdir(exist_ok=True)
        self._lock = threading.Lock()
        
        # Crear archivo con headers si no existe
        if not self.csv_file.exists():
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['fecha_hora', 'agente', 'conversation_id'])
    
    def record_message(self, agent_id: str, conversation_id: str):
        """Añade una fila al CSV por cada mensaje"""
        with self._lock:
            with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Formato: YYYY-MM-DD HH:MM:SS
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                writer.writerow([timestamp, agent_id, conversation_id])

# Instancia global
metrics_service = MetricsService() 