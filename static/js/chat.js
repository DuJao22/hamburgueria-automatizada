document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    const messagesContainer = document.getElementById('chatMessages');
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    const typingIndicator = document.getElementById('typingIndicator');
    const menuBtn = document.getElementById('menuBtn');
    const headerMenu = document.getElementById('headerMenu');
    const quickActions = document.querySelectorAll('.quick-action-btn');


    function formatTimestamp(timestamp) {
        if (!timestamp) return '';
        
        const date = new Date(timestamp);
        
        // Converter para horário de Brasília (UTC-3)
        const brasiliaOffset = -3 * 60; // -3 horas em minutos
        const localOffset = date.getTimezoneOffset(); // offset local em minutos
        const diff = brasiliaOffset - localOffset;
        
        const brasiliaTime = new Date(date.getTime() + diff * 60000);
        
        const hours = String(brasiliaTime.getHours()).padStart(2, '0');
        const minutes = String(brasiliaTime.getMinutes()).padStart(2, '0');
        
        return `${hours}:${minutes}`;
    }


    socket.on('connect', function() {
        console.log('Connected to chat server');
    });

    socket.on('load_messages', function(messages) {
        messages.forEach(msg => addMessage(msg.sender, msg.content, msg.created_at, true));
        scrollToBottom();
    });

    socket.on('message', function(data) {
        hideTyping();
        addMessage(data.sender, data.content, data.timestamp, false);
        scrollToBottom();
    });

    function addMessage(sender, content, timestamp, isHistorical = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const time = timestamp ? formatTimestamp(timestamp) : '';
        
        let displayContent = content;
        let shouldRedirect = false;
        
        if (sender === 'bot' && content.includes('[redirect:loja]')) {
            displayContent = content.replace('[redirect:loja]', '');
            if (!isHistorical) {
                shouldRedirect = true;
            }
        }
        
        messageDiv.innerHTML = `
            <div class="message-bubble">
                <div class="message-content">${escapeHtml(displayContent)}</div>
                <div class="message-time">${time}</div>
            </div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        
        if (shouldRedirect) {
            setTimeout(() => {
                window.location.href = '/loja';
            }, 2000);
        }
    }

    function sendMessage() {
        const content = messageInput.value.trim();
        if (!content) return;
        
        socket.emit('message', { content: content });
        messageInput.value = '';
        showTyping();
    }

    function showTyping() {
        typingIndicator.classList.add('show');
        scrollToBottom();
    }

    function hideTyping() {
        typingIndicator.classList.remove('show');
    }

    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        let html = div.innerHTML;
        
        // Converter markdown básico para HTML
        // Negrito: *texto* ou **texto**
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/g, '<strong>$1</strong>');
        
        // Itálico: _texto_
        html = html.replace(/_(.*?)_/g, '<em>$1</em>');
        
        // Quebras de linha
        html = html.replace(/\n/g, '<br>');
        
        // Emojis de lista
        html = html.replace(/^([•●○▪▫])/gm, '<span style="color: #667eea;">$1</span>');
        
        return html;
    }

    sendBtn.addEventListener('click', sendMessage);
    
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendMessage();
        }
    });

    messageInput.addEventListener('focus', function() {
        setTimeout(scrollToBottom, 300);
    });

    menuBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        headerMenu.classList.toggle('show');
    });

    document.addEventListener('click', function(e) {
        if (!headerMenu.contains(e.target)) {
            headerMenu.classList.remove('show');
        }
    });

    quickActions.forEach(btn => {
        btn.addEventListener('click', function() {
            const message = this.dataset.message;
            messageInput.value = message;
            sendMessage();
        });
    });

    updateCartBadge();
});

function updateCartBadge() {
    fetch('/api/cart')
        .then(response => response.json())
        .then(items => {
            const count = items.reduce((total, item) => total + item.quantity, 0);
            const badge = document.getElementById('cartBadge');
            if (badge) {
                badge.textContent = count;
                badge.style.display = count > 0 ? 'flex' : 'none';
            }
        })
        .catch(err => console.error('Error loading cart:', err));
}
