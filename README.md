# Embeddable Chatbot 🤖

Una herramienta para crear y embeber chatbots personalizables en cualquier sitio web mediante un simple fragmento de código JavaScript.

## 🚀 Características

- **Widget embebible**: Añade un chatbot a cualquier web con una línea de código
- **Múltiples agentes**: Crea diferentes chatbots con estilos y configuraciones únicas
- **Configuración por archivos**: Gestión simple mediante archivos JSON
- **Proxy de chat**: Intermediario entre tu web y tu API de chatbot
- **Responsive**: Funciona perfectamente en desktop y móvil
- **Fácil personalización**: Estilos, colores, posición y mensajes configurables

## 📁 Estructura del Proyecto

```
embed_chatbot/
├── app/
│   ├── main.py              # Aplicación FastAPI principal
│   ├── models.py            # Modelos Pydantic
│   ├── config.py            # Gestión de configuraciones
│   ├── agents/              # Configuraciones de agentes
│   │   ├── agent1.json
│   │   └── agent2.json
│   └── static/
│       └── widget.js        # Widget JavaScript embebible
├── requirements.txt
├── Dockerfile
└── README.md
```

## 🛠️ Instalación y Desarrollo

### Prerrequisitos
- Python 3.11+
- pip

### Instalación local

1. **Clonar el repositorio**
```bash
git clone <tu-repo>
cd embed_chatbot
```

2. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

3. **Ejecutar la aplicación**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. **Abrir en el navegador**
```
http://localhost:8000
```

## 🎯 Uso Rápido

### 1. Configurar un Agente

Crea o edita un archivo en `app/agents/` (ej. `mi-agente.json`):

```json
{
  "id": "mi-agente",
  "name": "Mi Asistente",
  "chat_endpoint": "https://tu-api-chatbot.com/chat",
  "styles": {
    "primary_color": "#007bff",
    "secondary_color": "#6c757d",
    "border_radius": "12px",
    "position": "bottom-right",
    "widget_size": "medium",
    "font_family": "Arial, sans-serif"
  },
  "messages": {
    "welcome": "¡Hola! ¿En qué puedo ayudarte?",
    "placeholder": "Escribe tu mensaje...",
    "error": "Lo siento, ha ocurrido un error."
  },
  "enabled": true
}
```

### 2. Embeber en tu Web

Añade este código en tu sitio web (WordPress, HTML, etc.):

```html
<script src="https://tu-dominio.run.app/widget.js" data-agent-id="mi-agente"></script>
```

¡Y ya está! El chatbot aparecerá automáticamente en tu web.

## 📋 Endpoints de la API

### Endpoints principales:

- `GET /` - Health check y estado de la aplicación
- `GET /widget.js` - Script JavaScript del widget
- `GET /config/{agent_id}` - Configuración de un agente específico
- `POST /chat/{agent_id}` - Proxy para enviar mensajes al chatbot
- `GET /agents` - Lista todos los agentes disponibles
- `POST /reload-config` - Recarga las configuraciones (útil en desarrollo)

### Ejemplo de uso de la API:

```javascript
// Obtener configuración de un agente
fetch('https://tu-dominio.run.app/config/agent1')

// Enviar mensaje al chatbot
fetch('https://tu-dominio.run.app/chat/agent1', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: "Hola, necesito ayuda",
    conversation_id: "opcional"
  })
})
```

## 🎨 Personalización

### Estilos Disponibles

```json
{
  "styles": {
    "primary_color": "#007bff",        // Color principal del widget
    "secondary_color": "#6c757d",      // Color secundario
    "border_radius": "12px",           // Radio de bordes
    "position": "bottom-right",        // Posición: "bottom-right" o "bottom-left"
    "widget_size": "medium",           // Tamaño: "medium" o "large"
    "font_family": "Arial, sans-serif" // Fuente tipográfica
  }
}
```

### Mensajes Personalizables

```json
{
  "messages": {
    "welcome": "Mensaje de bienvenida personalizado",
    "placeholder": "Texto del input personalizado",
    "error": "Mensaje de error personalizado"
  }
}
```

## 🚀 Deploy en Cloud Run

### 1. Build de la imagen Docker

```bash
docker build -t chatbot-embed .
```

### 2. Tag para Google Container Registry

```bash
docker tag chatbot-embed gcr.io/TU-PROJECT-ID/chatbot-embed
```

### 3. Push a GCR

```bash
docker push gcr.io/TU-PROJECT-ID/chatbot-embed
```

### 4. Deploy a Cloud Run

```bash
gcloud run deploy chatbot-embed \
  --image gcr.io/TU-PROJECT-ID/chatbot-embed \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

## 🔧 Configuración de tu API de Chatbot

Tu API debe aceptar peticiones POST con este formato:

```json
{
  "message": "Mensaje del usuario",
  "conversation_id": "opcional"
}
```

Y devolver respuestas en uno de estos formatos:

```json
// Formato simple
"Respuesta del chatbot"

// Formato con conversation_id
{
  "response": "Respuesta del chatbot",
  "conversation_id": "id-de-conversacion"
}

// Otros formatos soportados
{
  "message": "Respuesta del chatbot"
}
```

## 📱 Características del Widget

- **Responsive**: Se adapta automáticamente a móviles
- **Animaciones suaves**: Transiciones CSS elegantes
- **Indicador de carga**: Puntos animados mientras espera respuesta
- **Scroll automático**: Los mensajes nuevos aparecen automáticamente
- **Persistencia**: Mantiene la conversación mientras esté abierto el widget
- **CORS habilitado**: Funciona desde cualquier dominio

## 🐛 Troubleshooting

### Problema: Widget no aparece
- Verifica que el `data-agent-id` sea correcto
- Revisa la consola del navegador para errores
- Confirma que el agente esté habilitado (`"enabled": true`)

### Problema: Error en chat
- Verifica que tu API de chatbot esté funcionando
- Revisa que el `chat_endpoint` en la configuración sea correcto
- Confirma que tu API acepte peticiones POST con el formato requerido

### Problema: Estilos no se aplican
- Recarga la configuración con `POST /reload-config`
- Verifica que la sintaxis JSON sea correcta
- Revisa que los colores usen formato hexadecimal (#000000)

## 📄 Licencia

MIT License - Siéntete libre de usar y modificar según necesites.

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Feel free to:

1. Hacer fork del proyecto
2. Crear una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Crear un Pull Request

---

**¿Necesitas ayuda?** Abre un issue en el repositorio o contacta al equipo de desarrollo. 