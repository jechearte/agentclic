(function() {
    'use strict';
    
    // Verificar si el widget ya fue cargado
    if (window.EmbeddableChatbot) {
        return;
    }
    
    class EmbeddableChatbot {
        constructor() {
            this.agentId = null;
            this.config = null;
            this.conversationId = null;
            this.previousResponseId = null; // Para mantener el contexto de OpenAI
            this.isOpen = false;
            this.isInitialized = false;
            this.apiBase = null; // Se determinará desde el script src
            
            this.init();
        }
        
        async init() {
            // Buscar el script tag que incluye este widget
            const scripts = document.querySelectorAll('script[data-agent-id]');
            const widgetScript = scripts[scripts.length - 1]; // El último script debería ser este
            
            if (!widgetScript) {
                console.error('EmbeddableChatbot: No se encontró data-agent-id en el script tag');
                return;
            }
            
            this.agentId = widgetScript.getAttribute('data-agent-id');
            
            if (!this.agentId) {
                console.error('EmbeddableChatbot: data-agent-id es requerido');
                return;
            }
            
            // Extraer la URL base del src del script
            const scriptSrc = widgetScript.src;
            if (scriptSrc) {
                // Extraer la URL base (todo antes de /widget.js)
                this.apiBase = scriptSrc.replace('/widget.js', '');
                console.log(`EmbeddableChatbot: API base detectada desde script: ${this.apiBase}`);
            } else {
                // Fallback a window.location.origin si no se puede detectar
                this.apiBase = window.location.origin;
                console.warn('EmbeddableChatbot: No se pudo detectar URL del script, usando window.location.origin');
            }
            
            // Cargar configuración del agente primero
            const shouldContinue = await this.loadConfig();
            
            // Solo crear el widget si la configuración permite continuar
            if (!shouldContinue) {
                console.log('EmbeddableChatbot: Inicialización cancelada - dominio no autorizado');
                return;
            }
            
            // Cargar previous_response_id del localStorage si existe
            this.loadPreviousResponseId();
            
            // Generar conversation_id único para esta sesión
            this.generateConversationId();
            
            // Crear el widget cuando el DOM esté listo Y la configuración esté cargada
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.createWidget());
            } else {
                this.createWidget();
            }
        }
        
        async loadConfig() {
            try {
                console.log(`EmbeddableChatbot: Cargando configuración para agente ${this.agentId} desde ${this.apiBase}/public-config/${this.agentId}`);
                const response = await fetch(`${this.apiBase}/public-config/${this.agentId}`);
                if (!response.ok) {
                    throw new Error(`Error ${response.status}: ${response.statusText}`);
                }
                this.config = await response.json();
                console.log('EmbeddableChatbot: Configuración cargada exitosamente:', this.config);
                
                // Verificar si el dominio actual está permitido
                if (!this.isDomainAllowed()) {
                    console.warn('EmbeddableChatbot: Dominio no autorizado. Widget no se mostrará.');
                    return false; // Retornar false para indicar que no debe continuar
                }
                
                return true; // Dominio permitido, continuar
                
            } catch (error) {
                console.error('EmbeddableChatbot: Error cargando configuración:', error);
                console.log('EmbeddableChatbot: Usando configuración por defecto');
                this.config = this.getDefaultConfig();
                return true; // Con configuración por defecto, permitir continuar
            }
        }
        
        isDomainAllowed() {
            // Si no hay dominios configurados, permitir todos
            if (!this.config.allowed_domains || this.config.allowed_domains.length === 0) {
                console.log('EmbeddableChatbot: No hay restricciones de dominio configuradas');
                return true;
            }
            
            const currentDomain = window.location.host;
            const isAllowed = this.config.allowed_domains.includes(currentDomain);
            
            console.log(`EmbeddableChatbot: Verificando dominio "${currentDomain}" contra lista permitida:`, this.config.allowed_domains);
            console.log(`EmbeddableChatbot: Dominio ${isAllowed ? 'PERMITIDO' : 'BLOQUEADO'}`);
            
            return isAllowed;
        }
        
        getDefaultConfig() {
            return {
                id: this.agentId,
                name: 'Asistente Virtual',
                styles: {
                    primary_color: '#007bff',
                    secondary_color: '#6c757d',
                    border_radius: '12px',
                    position: 'bottom-right',
                    widget_size: 'medium',
                    font_family: 'Arial, sans-serif'
                },
                messages: {
                    welcome: '¡Hola! ¿En qué puedo ayudarte?',
                    placeholder: 'Escribe tu mensaje...',
                    error: 'Lo siento, ha ocurrido un error. Inténtalo de nuevo.'
                }
            };
        }
        
        loadPreviousResponseId() {
            try {
                const storageKey = `chatbot_response_id_${this.agentId}`;
                this.previousResponseId = localStorage.getItem(storageKey);
                console.log(`EmbeddableChatbot: Previous response ID cargado: ${this.previousResponseId}`);
            } catch (error) {
                console.warn('EmbeddableChatbot: Error accediendo localStorage:', error);
            }
        }
        
        savePreviousResponseId(responseId) {
            try {
                const storageKey = `chatbot_response_id_${this.agentId}`;
                localStorage.setItem(storageKey, responseId);
                this.previousResponseId = responseId;
                console.log(`EmbeddableChatbot: Response ID guardado: ${responseId}`);
            } catch (error) {
                console.warn('EmbeddableChatbot: Error guardando en localStorage:', error);
            }
        }
        
        clearConversationHistory() {
            try {
                const storageKey = `chatbot_response_id_${this.agentId}`;
                localStorage.removeItem(storageKey);
                this.previousResponseId = null;
                console.log('EmbeddableChatbot: Historial de conversación limpiado');
            } catch (error) {
                console.warn('EmbeddableChatbot: Error limpiando localStorage:', error);
            }
        }
        
        generateConversationId() {
            // Generar ID único: timestamp + random + agentId
            const timestamp = Date.now();
            const random = Math.random().toString(36).substr(2, 9);
            this.conversationId = `conv_${timestamp}_${random}_${this.agentId}`;
            console.log(`EmbeddableChatbot: Conversation ID generado: ${this.conversationId}`);
        }
        
        createWidget() {
            if (this.isInitialized) return;
            
            console.log('EmbeddableChatbot: Creando widget con configuración:', this.config);
            
            // Crear contenedor principal
            this.container = document.createElement('div');
            this.container.id = 'embeddable-chatbot-' + this.agentId;
            this.container.innerHTML = this.getWidgetHTML();
            
            // Añadir estilos
            this.addStyles();
            
            // Añadir al DOM
            document.body.appendChild(this.container);
            
            // Añadir event listeners
            this.addEventListeners();
            
            this.isInitialized = true;
            console.log('EmbeddableChatbot: Widget creado exitosamente');
        }
        
        getWidgetHTML() {
            return `
                <div class="chatbot-toggle">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 2C6.48 2 2 6.48 2 12C2 13.54 2.38 14.99 3.06 16.26L2 22L7.74 20.94C9.01 21.62 10.46 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM12 20C10.74 20 9.54 19.68 8.5 19.1L8.19 18.93L4.42 19.86L5.35 16.09L5.18 15.78C4.5 14.74 4.18 13.54 4.18 12.28C4.18 7.58 7.9 3.86 12.6 3.86C17.3 3.86 21.02 7.58 21.02 12.28C21.02 16.98 17.3 20.7 12.6 20.7L12 20Z" fill="white"/>
                    </svg>
                </div>
                
                <div class="chatbot-window" style="display: none;">
                    <div class="chatbot-header">
                        <span class="chatbot-title">${this.config.name}</span>
                        <div class="chatbot-header-buttons">
                            <button class="chatbot-clear" title="Limpiar conversación">
                                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                                    <path d="M2 4h12M5 4V2a1 1 0 011-1h4a1 1 0 011 1v2m3 0v10a2 2 0 01-2 2H4a2 2 0 01-2-2V4z" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
                                </svg>
                            </button>
                            <button class="chatbot-close">
                                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                                    <path d="M12 4L4 12M4 4L12 12" stroke="white" stroke-width="2" stroke-linecap="round"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                    
                    <div class="chatbot-messages">
                        <div class="chatbot-message bot-message">
                            <div class="message-content">${this.config.messages.welcome}</div>
                        </div>
                    </div>
                    
                    <div class="chatbot-input-container">
                        <input type="text" class="chatbot-input" placeholder="${this.config.messages.placeholder}">
                        <button class="chatbot-send">
                            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                                <path d="M15 1L1 8L4 9L6 14L15 1Z" fill="currentColor"/>
                            </svg>
                        </button>
                    </div>
                    
                    <div class="chatbot-loading" style="display: none;">
                        <div class="loading-dots">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                    </div>
                </div>
            `;
        }
        
        addStyles() {
            const style = document.createElement('style');
            style.textContent = this.getWidgetCSS();
            document.head.appendChild(style);
        }
        
        getWidgetCSS() {
            const position = this.config.styles.position === 'bottom-left' ? 'left: 20px;' : 'right: 20px;';
            const size = this.config.styles.widget_size === 'large' ? '400px' : '350px';
            
            return `
                #embeddable-chatbot-${this.agentId} {
                    position: fixed;
                    bottom: 20px;
                    ${position}
                    z-index: 10000;
                    font-family: ${this.config.styles.font_family};
                }
                
                #embeddable-chatbot-${this.agentId} .chatbot-toggle {
                    width: 60px;
                    height: 60px;
                    background-color: ${this.config.styles.primary_color};
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    transition: all 0.3s ease;
                }
                
                #embeddable-chatbot-${this.agentId} .chatbot-toggle:hover {
                    transform: scale(1.1);
                    box-shadow: 0 6px 20px rgba(0,0,0,0.2);
                }
                
                #embeddable-chatbot-${this.agentId} .chatbot-window {
                    width: ${size};
                    height: 500px;
                    background: white;
                    border-radius: ${this.config.styles.border_radius};
                    box-shadow: 0 8px 30px rgba(0,0,0,0.12);
                    display: flex;
                    flex-direction: column;
                    position: absolute;
                    bottom: 20px;
                    right: 0;
                    overflow: hidden;
                }
                
                #embeddable-chatbot-${this.agentId} .chatbot-header {
                    background-color: ${this.config.styles.primary_color};
                    color: white;
                    padding: 16px 20px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                
                #embeddable-chatbot-${this.agentId} .chatbot-title {
                    font-weight: 600;
                    font-size: 16px;
                }
                
                #embeddable-chatbot-${this.agentId} .chatbot-header-buttons {
                    display: flex;
                    gap: 8px;
                }
                
                #embeddable-chatbot-${this.agentId} .chatbot-close,
                #embeddable-chatbot-${this.agentId} .chatbot-clear {
                    background: none;
                    border: none;
                    color: white;
                    cursor: pointer;
                    padding: 4px;
                    border-radius: 4px;
                    transition: background-color 0.2s;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                
                #embeddable-chatbot-${this.agentId} .chatbot-close:hover,
                #embeddable-chatbot-${this.agentId} .chatbot-clear:hover {
                    background-color: rgba(255,255,255,0.1);
                }
                
                #embeddable-chatbot-${this.agentId} .chatbot-messages {
                    flex: 1;
                    padding: 20px;
                    overflow-y: auto;
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }
                
                #embeddable-chatbot-${this.agentId} .chatbot-message {
                    display: flex;
                    max-width: 80%;
                }
                
                #embeddable-chatbot-${this.agentId} .bot-message {
                    align-self: flex-start;
                }
                
                #embeddable-chatbot-${this.agentId} .user-message {
                    align-self: flex-end;
                }
                
                #embeddable-chatbot-${this.agentId} .message-content {
                    padding: 12px 16px;
                    border-radius: 18px;
                    font-size: 14px;
                    line-height: 1.4;
                }
                
                #embeddable-chatbot-${this.agentId} .bot-message .message-content {
                    background-color: #f1f3f5;
                    color: #333;
                }
                
                #embeddable-chatbot-${this.agentId} .user-message .message-content {
                    background-color: ${this.config.styles.primary_color};
                    color: white;
                }
                
                #embeddable-chatbot-${this.agentId} .chatbot-input-container {
                    padding: 16px 20px;
                    border-top: 1px solid #e9ecef;
                    display: flex;
                    gap: 8px;
                    align-items: center;
                }
                
                #embeddable-chatbot-${this.agentId} .chatbot-input {
                    flex: 1;
                    border: 1px solid #dee2e6;
                    border-radius: 24px;
                    padding: 12px 16px;
                    font-size: 14px;
                    outline: none;
                    transition: border-color 0.2s;
                }
                
                #embeddable-chatbot-${this.agentId} .chatbot-input:focus {
                    border-color: ${this.config.styles.primary_color};
                }
                
                #embeddable-chatbot-${this.agentId} .chatbot-send {
                    width: 40px;
                    height: 40px;
                    background-color: ${this.config.styles.primary_color};
                    color: white;
                    border: none;
                    border-radius: 50%;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: background-color 0.2s;
                }
                
                #embeddable-chatbot-${this.agentId} .chatbot-send:hover {
                    background-color: ${this.config.styles.secondary_color};
                }
                
                #embeddable-chatbot-${this.agentId} .chatbot-send:disabled {
                    background-color: #dee2e6;
                    cursor: not-allowed;
                }
                
                #embeddable-chatbot-${this.agentId} .chatbot-loading {
                    padding: 20px;
                    text-align: center;
                }
                
                #embeddable-chatbot-${this.agentId} .loading-dots {
                    display: inline-flex;
                    gap: 4px;
                }
                
                #embeddable-chatbot-${this.agentId} .loading-dots span {
                    width: 8px;
                    height: 8px;
                    background-color: ${this.config.styles.primary_color};
                    border-radius: 50%;
                    animation: loading-bounce 1.4s ease-in-out infinite both;
                }
                
                #embeddable-chatbot-${this.agentId} .loading-dots span:nth-child(1) { animation-delay: -0.32s; }
                #embeddable-chatbot-${this.agentId} .loading-dots span:nth-child(2) { animation-delay: -0.16s; }
                
                @keyframes loading-bounce {
                    0%, 80%, 100% { transform: scale(0); }
                    40% { transform: scale(1); }
                }
                
                @media (max-width: 480px) {
                    #embeddable-chatbot-${this.agentId} .chatbot-window {
                        width: calc(100vw - 40px);
                        height: 60vh;
                        bottom: 70px;
                        left: 20px;
                        right: 20px;
                    }
                }
            `;
        }
        
        addEventListeners() {
            const toggle = this.container.querySelector('.chatbot-toggle');
            const closeBtn = this.container.querySelector('.chatbot-close');
            const clearBtn = this.container.querySelector('.chatbot-clear');
            const window = this.container.querySelector('.chatbot-window');
            const input = this.container.querySelector('.chatbot-input');
            const sendBtn = this.container.querySelector('.chatbot-send');
            
            toggle.addEventListener('click', () => this.toggleChat());
            closeBtn.addEventListener('click', () => this.closeChat());
            clearBtn.addEventListener('click', () => this.clearConversation());
            sendBtn.addEventListener('click', () => this.sendMessage());
            
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.sendMessage();
                }
            });
        }
        
        clearConversation() {
            // Confirmar con el usuario
            if (confirm('¿Estás seguro de que quieres limpiar la conversación? Esto eliminará todo el historial.')) {
                // Limpiar historial de localStorage
                this.clearConversationHistory();
                
                // Generar nuevo conversation_id para la nueva conversación
                this.generateConversationId();
                
                // Limpiar mensajes del UI
                const messagesContainer = this.container.querySelector('.chatbot-messages');
                messagesContainer.innerHTML = `
                    <div class="chatbot-message bot-message">
                        <div class="message-content">${this.config.messages.welcome}</div>
                    </div>
                `;
                
                console.log('EmbeddableChatbot: Conversación limpiada');
            }
        }
        
        toggleChat() {
            const window = this.container.querySelector('.chatbot-window');
            const toggle = this.container.querySelector('.chatbot-toggle');
            
            if (this.isOpen) {
                this.closeChat();
            } else {
                window.style.display = 'flex';
                toggle.style.display = 'none';
                this.isOpen = true;
            }
        }
        
        closeChat() {
            const window = this.container.querySelector('.chatbot-window');
            const toggle = this.container.querySelector('.chatbot-toggle');
            
            window.style.display = 'none';
            toggle.style.display = 'flex';
            this.isOpen = false;
        }
        
        async sendMessage() {
            const input = this.container.querySelector('.chatbot-input');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Limpiar input
            input.value = '';
            
            // Añadir mensaje del usuario
            this.addMessage(message, 'user');
            
            // Mostrar loading
            this.showLoading(true);
            
            // Deshabilitar input y botón
            this.setInputEnabled(false);
            
            try {
                // Preparar el body del request incluyendo previous_response_id si existe
                const requestBody = {
                    message: message,
                    conversation_id: this.conversationId
                };
                
                // Añadir previous_response_id si existe (para OpenAI context)
                if (this.previousResponseId) {
                    requestBody.previous_response_id = this.previousResponseId;
                }
                
                const response = await fetch(`${this.apiBase}/chat/${this.agentId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(requestBody)
                });
                
                if (!response.ok) {
                    throw new Error(`Error ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                
                // Actualizar conversation_id si viene en la respuesta
                if (data.conversation_id) {
                    this.conversationId = data.conversation_id;
                }
                
                // Guardar response_id si viene en la respuesta (para OpenAI context)
                if (data.response_id) {
                    this.savePreviousResponseId(data.response_id);
                }
                
                // Añadir respuesta del bot
                this.addMessage(data.response, 'bot');
                
            } catch (error) {
                console.error('Error enviando mensaje:', error);
                this.addMessage(this.config.messages.error, 'bot');
            } finally {
                this.showLoading(false);
                this.setInputEnabled(true);
                input.focus();
            }
        }
        
        addMessage(content, type) {
            const messagesContainer = this.container.querySelector('.chatbot-messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `chatbot-message ${type}-message`;
            messageDiv.innerHTML = `<div class="message-content">${content}</div>`;
            
            messagesContainer.appendChild(messageDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
        
        showLoading(show) {
            const loading = this.container.querySelector('.chatbot-loading');
            loading.style.display = show ? 'block' : 'none';
        }
        
        setInputEnabled(enabled) {
            const input = this.container.querySelector('.chatbot-input');
            const sendBtn = this.container.querySelector('.chatbot-send');
            
            input.disabled = !enabled;
            sendBtn.disabled = !enabled;
        }
    }
    
    // Crear instancia del widget
    window.EmbeddableChatbot = new EmbeddableChatbot();
})(); 