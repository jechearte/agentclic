# Embeddable Chatbot 🤖 🤖

Una herramienta para crear y embeber chatbots personalizables en cualquier sitio web mediante un simple fragmento de código JavaScript. Soporta múltiples tipos de agentes: OpenAI, N8N y backends personalizados.

## 🚀 Características

- **Widget embebible**: Añade un chatbot a cualquier web con una línea de código
- **Múltiples tipos de agentes**: OpenAI, N8N workflows y backends personalizados
- **Configuración por archivos**: Gestión simple mediante archivos JSON
- **Variables de entorno**: Credenciales seguras sin hardcodear
- **Proxy de chat**: Intermediario entre tu web y diferentes APIs de chatbot
- **Responsive**: Funciona perfectamente en desktop y móvil
- **Fácil personalización**: Estilos, colores, posición y mensajes configurables

## 📁 Estructura del Proyecto

```
embed_chatbot/
├── app/
│   ├── main.py              # Aplicación FastAPI principal
│   ├── models.py            # Modelos Pydantic
│   ├── config.py            # Gestión de configuraciones y variables de entorno
│   ├── chat_service.py      # Servicio para diferentes tipos de agentes
│   ├── agents/              # Configuraciones de agentes
│   │   ├── openai-agent.json    # Agente OpenAI
│   │   ├── n8n-agent.json       # Agente N8N
│   │   └── custom-agent.json    # Agente personalizado
│   └── static/
│       └── widget.js        # Widget JavaScript embebible
├── .env                     # Variables de entorno (no incluido en repo)
├── .env.example            # Ejemplo de variables de entorno
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

3. **Configurar variables de entorno**
```bash
cp .env.example .env
# Editar .env y añadir tu OPENAI_API_KEY
```

4. **Ejecutar la aplicación**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. **Abrir en el navegador**
```
http://localhost:8000
```

## 🔧 Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

```env
# API Key de OpenAI (obligatoria para agentes tipo 'openai')
# Obtén tu API key desde: https://platform.openai.com/api-keys
OPENAI_API_KEY=tu_api_key_de_openai_aqui

# Puerto del servidor (opcional, por defecto 8000)
# PORT=8000

# Modo debug (opcional, por defecto false)
# DEBUG=false
```

## 🤖 Tipos de Agentes

Embeddable Chatbot 🤖 soporta 3 tipos diferentes de agentes, cada uno con su configuración específica:

### 1. Agente OpenAI (`type: "openai"`)

Para chatbots que usan la API de OpenAI (Azure OpenAI Responses API).

```json
{
  "id": "mi-agente-openai",
  "name": "Asistente OpenAI",
  "type": "openai",
  "styles": { /* estilos del widget */ },
  "messages": { /* mensajes personalizados */ },
  "enabled": true,
  "allowed_domains": ["midominio.com"],
  "openai_config": {
    "model": "gpt-4.1-mini",
    "instructions": "Eres un asistente virtual útil y amigable.",
    "max_output_tokens": 2000,
    "temperature": 0.3,
    "top_p": 1.0,
    "tools": [
      {
        "type": "file_search",
        "vector_store_ids": ["vs_tu_vector_store_id"]
      }
    ]
  }
}
```

**Nota**: La API key se toma automáticamente de la variable de entorno `OPENAI_API_KEY`.

### 2. Agente N8N (`type: "n8n"`)

Para workflows de N8N que manejan las conversaciones.

```json
{
  "id": "mi-agente-n8n",
  "name": "Asistente N8N",
  "type": "n8n",
  "styles": { /* estilos del widget */ },
  "messages": { /* mensajes personalizados */ },
  "enabled": true,
  "allowed_domains": ["midominio.com"],
  "n8n_config": {
    "webhook_url": "https://tu-n8n-instance.com/webhook/tu-webhook-id"
  }
}
```

**Formato de petición a N8N**:
```json
{
  "action": "sendMessage",
  "sessionId": "conversation_id",
  "chatInput": "mensaje_del_usuario"
}
```

**Respuesta esperada de N8N**:
```json
[{"output": "respuesta_del_bot"}]
// o
{"output": "respuesta_del_bot"}
```

### 3. Agente Personalizado (`type: "custom"`) [WORK IN PROGRESS]

Para backends completamente personalizados con máxima flexibilidad.

```json
{
  "id": "mi-agente-custom",
  "name": "Asistente Personalizado",
  "type": "custom",
  "styles": { /* estilos del widget */ },
  "messages": { /* mensajes personalizados */ },
  "enabled": true,
  "allowed_domains": ["midominio.com"],
  "chat_endpoint": "https://tu-api.com/chat",
  "custom_config": {
    "headers": {
      "Authorization": "Bearer tu-token",
      "Content-Type": "application/json",
      "X-API-Key": "tu-api-key"
    },
    "body_structure": {
      "message": "{message}",
      "session_id": "{conversation_id}",
      "user_id": "usuario_123"
    },
    "response_path": "data.response"
  }
}
```

**Placeholders disponibles en `body_structure`**:
- `{message}`: El mensaje del usuario
- `{conversation_id}`: ID único de la conversación

**`response_path`**: Ruta para extraer la respuesta del JSON (ej: `"data.response"` extrae `response` de `{"data": {"response": "texto"}}`)

## 🎯 Uso Rápido

### 1. Configurar un Agente

Crea o edita un archivo en `app/agents/` según el tipo de agente que necesites (ver sección anterior).

### 2. Embeber en tu Web

Añade este código en tu sitio web (WordPress, HTML, etc.):

```html
<script src="https://tu-dominio.com/widget.js" data-agent-id="tu-agente-id"></script>
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
// Obtener configuración pública de un agente (sin credenciales)
fetch('https://tu-dominio.com/public-config/agent1')

// Obtener configuración completa (solo para uso interno)
fetch('https://tu-dominio.com/config/agent1')

// Enviar mensaje al chatbot
fetch('https://tu-dominio.com/chat/agent1', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: "Hola, necesito ayuda",
    conversation_id: "opcional",
    previous_response_id: "opcional-para-contexto"
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

## 🔧 Configuración de Endpoints Externos

### Para Agentes Personalizados (Custom)

Tu API debe aceptar peticiones POST con el formato que hayas configurado en `body_structure`, y devolver respuestas que coincidan con el `response_path` configurado.

**Ejemplo de configuración**:
```json
{
  "body_structure": {
    "message": "{message}",
    "session_id": "{conversation_id}"
  },
  "response_path": "data.response"
}
```

**Petición enviada**:
```json
{
  "message": "Mensaje del usuario", 
  "session_id": "conv_123456"
}
```

**Respuesta esperada**:
```json
{
  "data": {
    "response": "Respuesta del chatbot"
  }
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