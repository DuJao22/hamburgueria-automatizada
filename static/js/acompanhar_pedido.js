
document.addEventListener('DOMContentLoaded', function() {
    const orderIdInput = document.getElementById('orderIdInput');
    const searchBtn = document.getElementById('searchBtn');
    const trackingResult = document.getElementById('orderTrackingResult');
    const errorMessage = document.getElementById('errorMessage');
    const errorText = document.getElementById('errorText');

    // Verificar se há ID do pedido na URL
    const urlParams = new URLSearchParams(window.location.search);
    const orderIdFromUrl = urlParams.get('id');
    
    if (orderIdFromUrl) {
        orderIdInput.value = orderIdFromUrl;
        trackOrder(orderIdFromUrl);
    }

    searchBtn.addEventListener('click', handleSearch);
    orderIdInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            handleSearch();
        }
    });

    function handleSearch() {
        const orderId = orderIdInput.value.trim();
        
        if (!orderId) {
            showError('Por favor, digite o número do pedido');
            return;
        }

        trackOrder(orderId);
    }

    function trackOrder(orderId) {
        hideError();
        trackingResult.style.display = 'none';

        fetch(`/api/track-order/${orderId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Pedido não encontrado');
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    showError(data.error);
                } else {
                    displayOrderTracking(data);
                }
            })
            .catch(err => {
                console.error('Erro ao buscar pedido:', err);
                showError('Pedido não encontrado. Verifique o número e tente novamente.');
            });
    }

    function displayOrderTracking(order) {
        const statusLabels = {
            'pending': 'Pendente',
            'confirmed': 'Confirmado',
            'preparing': 'Em Preparo',
            'out_for_delivery': 'Saiu para Entrega',
            'delivered': 'Entregue',
            'cancelled': 'Cancelado'
        };

        const timelineSteps = [
            { status: 'pending', label: 'Pedido Recebido', icon: 'fa-check-circle' },
            { status: 'confirmed', label: 'Pedido Confirmado', icon: 'fa-clipboard-check' },
            { status: 'preparing', label: 'Em Preparo', icon: 'fa-box-open' },
            { status: 'out_for_delivery', label: 'Saiu para Entrega', icon: 'fa-truck' },
            { status: 'delivered', label: 'Entregue', icon: 'fa-check-double' }
        ];

        const currentStatusIndex = timelineSteps.findIndex(step => step.status === order.status);

        let timelineHTML = '';
        timelineSteps.forEach((step, index) => {
            let itemClass = '';
            if (index < currentStatusIndex) {
                itemClass = 'completed';
            } else if (index === currentStatusIndex) {
                itemClass = 'active';
            }

            const log = order.logs?.find(l => l.status === step.status);
            const dateText = log ? formatDate(log.created_at) : '';

            timelineHTML += `
                <div class="timeline-item ${itemClass}">
                    <div class="timeline-dot">
                        <i class="fas ${step.icon}"></i>
                    </div>
                    <div class="timeline-content">
                        <div class="timeline-title">${step.label}</div>
                        ${dateText ? `<div class="timeline-date">${dateText}</div>` : ''}
                    </div>
                </div>
            `;
        });

        let itemsHTML = '';
        if (order.items && order.items.length > 0) {
            itemsHTML = `
                <div class="order-items">
                    <h3><i class="fas fa-box"></i> Itens do Pedido</h3>
                    <div class="item-list">
                        ${order.items.map(item => `
                            <div class="item-row">
                                <div class="item-info">
                                    <div class="item-name">${item.name}</div>
                                    <div class="item-qty">Quantidade: ${item.quantity}</div>
                                </div>
                                <div class="item-price">R$ ${parseFloat(item.price * item.quantity).toFixed(2)}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        trackingResult.innerHTML = `
            <div class="order-header">
                <div class="order-number">Pedido #${order.id}</div>
                <div class="order-status status-${order.status}">${statusLabels[order.status] || order.status}</div>
            </div>

            <div class="timeline">
                ${timelineHTML}
            </div>

            <div class="order-details">
                <div class="detail-row">
                    <span class="detail-label"><i class="fas fa-calendar"></i> Data do Pedido:</span>
                    <span class="detail-value">${formatDateFull(order.created_at)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label"><i class="fas fa-map-marker-alt"></i> Endereço de Entrega:</span>
                    <span class="detail-value">${order.shipping_address || 'Não informado'}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label"><i class="fas fa-credit-card"></i> Pagamento:</span>
                    <span class="detail-value">${getPaymentLabel(order.payment_method)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label"><i class="fas fa-receipt"></i> Valor Total:</span>
                    <span class="detail-value">R$ ${parseFloat(order.total).toFixed(2)}</span>
                </div>
            </div>

            ${itemsHTML}
        `;

        trackingResult.style.display = 'block';
    }

    function showError(message) {
        errorText.textContent = message;
        errorMessage.style.display = 'block';
        trackingResult.style.display = 'none';
    }

    function hideError() {
        errorMessage.style.display = 'none';
    }

    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('pt-BR', { 
            day: '2-digit', 
            month: '2-digit', 
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    function formatDateFull(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('pt-BR', { 
            day: '2-digit', 
            month: 'long', 
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    function getPaymentLabel(method) {
        const labels = {
            'dinheiro': 'Dinheiro',
            'cartao': 'Cartão',
            'pix': 'PIX',
            'pending': 'Pendente'
        };
        return labels[method] || method;
    }
});
