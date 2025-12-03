document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchConversations');
    const conversationsItems = document.getElementById('conversationsItems');
    const conversationContent = document.getElementById('conversationContent');
    const noConversation = document.querySelector('.no-conversation-selected');
    
    let conversations = [];

    loadConversations();

    searchInput.addEventListener('input', function() {
        const term = this.value.toLowerCase();
        const filtered = conversations.filter(c => 
            (c.customer_name && c.customer_name.toLowerCase().includes(term)) || 
            (c.customer_phone && c.customer_phone.includes(term))
        );
        renderConversations(filtered);
    });

    function loadConversations() {
        fetch('/api/admin/conversations')
            .then(response => response.json())
            .then(data => {
                conversations = data;
                renderConversations(data);
            })
            .catch(err => console.error('Error loading conversations:', err));
    }

    function renderConversations(data) {
        if (data.length === 0) {
            conversationsItems.innerHTML = '<div style="padding: 30px; text-align: center; color: #999;">Nenhuma conversa encontrada</div>';
            return;
        }
        
        conversationsItems.innerHTML = data.map(conv => `
            <div class="conversation-item" onclick="viewConversation(${conv.id})" data-id="${conv.id}">
                <div class="conversation-avatar">
                    <i class="fas fa-user"></i>
                </div>
                <div class="conversation-info">
                    <h4>${conv.customer_name || 'Visitante'}</h4>
                    <p>${conv.customer_phone || conv.session_id?.substring(0, 10) || 'Sem identificação'}...</p>
                </div>
                <div class="conversation-meta">
                    <span class="time">${formatDateShort(conv.updated_at)}</span>
                    ${conv.message_count > 0 ? `<span class="count">${conv.message_count}</span>` : ''}
                </div>
            </div>
        `).join('');
    }

    window.viewConversation = function(id) {
        const conv = conversations.find(c => c.id === id);
        if (!conv) return;
        
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.toggle('active', item.dataset.id == id);
        });
        
        document.getElementById('customerName').textContent = conv.customer_name || 'Visitante';
        document.getElementById('customerPhone').textContent = conv.customer_phone || '';
        
        fetch(`/api/admin/conversations/${id}/messages`)
            .then(response => response.json())
            .then(messages => {
                const container = document.getElementById('messagesContainer');
                
                container.innerHTML = messages.map(msg => `
                    <div class="message ${msg.sender}">
                        <div class="message-bubble">
                            ${escapeHtml(msg.content)}
                        </div>
                        <div class="message-time">${formatTime(msg.created_at)}</div>
                    </div>
                `).join('');
                
                container.scrollTop = container.scrollHeight;
            });
        
        noConversation.style.display = 'none';
        conversationContent.style.display = 'flex';
    };

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML.replace(/\n/g, '<br>');
    }

    function formatTime(dateString) {
        if (!dateString) return '';
        
        const date = new Date(dateString);
        
        // Converter para horário de Brasília (UTC-3)
        const brasiliaOffset = -3 * 60;
        const localOffset = date.getTimezoneOffset();
        const diff = brasiliaOffset - localOffset;
        
        const brasiliaTime = new Date(date.getTime() + diff * 60000);
        
        const hours = String(brasiliaTime.getHours()).padStart(2, '0');
        const minutes = String(brasiliaTime.getMinutes()).padStart(2, '0');
        
        return `${hours}:${minutes}`;
    }
});
