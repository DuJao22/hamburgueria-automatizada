document.addEventListener('DOMContentLoaded', function() {
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const sidebar = document.querySelector('.sidebar');
    const mobileOverlay = document.querySelector('.mobile-overlay');
    const notificationBtn = document.getElementById('notificationBtn');
    const notificationsDropdown = document.getElementById('notificationsDropdown');

    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
        });
    }

    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', function() {
            sidebar.classList.add('show');
            mobileOverlay.classList.add('show');
        });
    }

    if (mobileOverlay) {
        mobileOverlay.addEventListener('click', function() {
            sidebar.classList.remove('show');
            mobileOverlay.classList.remove('show');
        });
    }

    // Sistema de notificações
    if (notificationBtn && notificationsDropdown) {
        notificationBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            notificationsDropdown.classList.toggle('show');
            loadNotifications();
        });

        document.addEventListener('click', function(e) {
            if (!notificationsDropdown.contains(e.target) && e.target !== notificationBtn) {
                notificationsDropdown.classList.remove('show');
            }
        });
    }

    // Carregar notificações a cada minuto
    setInterval(checkNewNotifications, 60000);
    checkNewNotifications();
    
    // Carregar contagem de pedidos pendentes
    loadPendingOrdersCount();
    setInterval(loadPendingOrdersCount, 30000); // Atualizar a cada 30 segundos
});

function loadPendingOrdersCount() {
    fetch('/api/admin/orders?status=pending')
        .then(response => response.json())
        .then(orders => {
            const badge = document.getElementById('pendingOrdersBadge');
            if (badge) {
                badge.textContent = orders.length;
                badge.style.display = orders.length > 0 ? 'inline' : 'none';
            }
        })
        .catch(err => console.error('Error loading pending orders:', err));
}

function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value || 0);
}

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}

function formatDateShort(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('pt-BR', {
        day: '2-digit',
        month: '2-digit'
    }).format(date);
}

function getStatusClass(status) {
    const classes = {
        'pending': 'status-pending',
        'confirmed': 'status-confirmed',
        'processing': 'status-processing',
        'shipped': 'status-shipped',
        'delivered': 'status-delivered',
        'cancelled': 'status-cancelled'
    };
    return classes[status] || 'status-pending';
}

function getStatusLabel(status) {
    const labels = {
        'pending': 'Pendente',
        'confirmed': 'Confirmado',
        'processing': 'Em Preparo',
        'shipped': 'Enviado',
        'delivered': 'Entregue',
        'cancelled': 'Cancelado'
    };
    return labels[status] || status;
}

window.loadNotifications = function() {
    fetch('/api/admin/notifications')
        .then(response => response.json())
        .then(notifications => {
            const notificationsList = document.getElementById('notificationsList');

            if (notifications.length === 0) {
                notificationsList.innerHTML = `
                    <div class="no-notifications">
                        <i class="fas fa-bell-slash"></i>
                        <p>Nenhuma notificação</p>
                    </div>
                `;
                return;
            }

            notificationsList.innerHTML = notifications.map(notif => `
                <div class="notification-item ${notif.read ? '' : 'unread'}" onclick="viewNotification('${notif.id}', '${notif.link}')">
                    <div class="notification-content">
                        <div class="notification-title">${notif.title}</div>
                        <div class="notification-message">${notif.message}</div>
                        <div class="notification-time">${getTimeAgo(notif.created_at)}</div>
                    </div>
                </div>
            `).join('');
        })
        .catch(err => console.error('Erro ao carregar notificações:', err));
}

function checkNewNotifications() {
    fetch('/api/admin/notifications/count')
        .then(response => response.json())
        .then(data => {
            const badge = document.getElementById('notificationBadge');
            if (data.count > 0) {
                badge.textContent = data.count;
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
            }
        })
        .catch(err => console.error('Erro ao verificar notificações:', err));
}

function viewNotification(notifId, link) {
    fetch(`/api/admin/notifications/${notifId}/read`, { method: 'POST' })
        .then(() => {
            if (link) {
                window.location.href = link;
            }
        });
}

window.clearAllNotifications = function() {
    if (!confirm('Deseja realmente limpar todas as notificações?')) {
        return;
    }
    
    fetch('/api/admin/notifications/clear', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            // Limpar visualmente a lista de notificações
            const notificationsList = document.getElementById('notificationsList');
            if (notificationsList) {
                notificationsList.innerHTML = '<div class="empty-notifications">Nenhuma notificação</div>';
            }
            
            // Atualizar badge
            const badge = document.getElementById('notificationBadge');
            if (badge) {
                badge.style.display = 'none';
            }
            
            // Fechar dropdown após limpar
            const notificationsDropdown = document.getElementById('notificationsDropdown');
            if (notificationsDropdown) {
                notificationsDropdown.classList.remove('show');
            }
        })
        .catch(err => {
            console.error('Erro ao limpar notificações:', err);
            alert('Erro ao limpar notificações. Tente novamente.');
        });
}

function getTimeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffInMinutes = Math.floor((now - date) / 60000);

    if (diffInMinutes < 1) return 'Agora';
    if (diffInMinutes < 60) return `${diffInMinutes}min atrás`;

    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) return `${diffInHours}h atrás`;

    const diffInDays = Math.floor(diffInHours / 24);
    return `${diffInDays}d atrás`;
}