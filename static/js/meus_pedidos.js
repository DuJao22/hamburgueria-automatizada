document.addEventListener('DOMContentLoaded', function() {
    const ordersList = document.getElementById('ordersList');
    const filterBtns = document.querySelectorAll('.filter-btn');
    const modal = document.getElementById('orderDetailsModal');
    const closeModal = document.getElementById('closeModal');

    let allOrders = [];
    let currentFilter = 'all';

    checkLoginAndLoadOrders();

    filterBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            filterBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentFilter = this.dataset.status;
            renderOrders(filterOrders(allOrders, currentFilter));
        });
    });

    closeModal.addEventListener('click', () => {
        modal.classList.remove('show');
    });

    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.classList.remove('show');
        }
    });

    function checkLoginAndLoadOrders() {
        // Carregar pedidos diretamente - o backend vai verificar
        loadOrders();
    }

    function loadOrders() {
        fetch('/api/customer/orders', {
            credentials: 'include', // Garantir que cookies de sessão sejam enviados
            headers: {
                'Cache-Control': 'no-cache'
            }
        })
            .then(response => {
                console.log('Orders response status:', response.status);
                if (response.status === 401) {
                    console.warn('Unauthorized - redirecting to login');
                    sessionStorage.setItem('redirectAfterLogin', window.location.pathname);
                    window.location.href = '/login';
                    return Promise.reject('Not authenticated');
                }
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Orders loaded:', data ? data.length : 0);
                if (data && !data.error) {
                    allOrders = data;
                    renderOrders(filterOrders(data, currentFilter));
                } else if (data && data.redirect) {
                    console.warn('Redirect required:', data.redirect);
                    window.location.href = data.redirect;
                } else if (data && data.error) {
                    console.error('Error in data:', data.error);
                    showEmptyState(data.error);
                }
            })
            .catch(err => {
                if (err !== 'Not authenticated') {
                    console.error('Error loading orders:', err);
                    showEmptyState('Erro ao carregar pedidos');
                }
            });
    }

    function filterOrders(orders, status) {
        if (status === 'all') return orders;
        return orders.filter(order => order.status === status);
    }

    function renderOrders(orders) {
        if (orders.length === 0) {
            showEmptyState();
            return;
        }

        ordersList.innerHTML = orders.map(order => `
            <div class="order-card" onclick="showOrderDetails(${order.id})">
                <div class="order-card-header">
                    <div class="order-number">Pedido #${order.id}</div>
                    <div class="status-badge ${order.status}">${getStatusLabel(order.status)}</div>
                </div>
                <div class="order-items-preview">
                    ${order.item_count} ${order.item_count === 1 ? 'item' : 'itens'}
                </div>
                <div class="order-card-footer">
                    <div class="order-date">
                        <i class="fas fa-calendar"></i>
                        ${formatDate(order.created_at)}
                    </div>
                    <div class="order-total">R$ ${parseFloat(order.total).toFixed(2)}</div>
                </div>
            </div>
        `).join('');
    }

    window.showOrderDetails = function(orderId) {
        const order = allOrders.find(o => o.id === orderId);
        if (!order) return;

        document.getElementById('modalOrderNumber').textContent = orderId;
        document.getElementById('modalOrderStatus').className = `order-status-badge status-badge ${order.status}`;
        document.getElementById('modalOrderStatus').textContent = getStatusLabel(order.status);
        document.getElementById('modalOrderAddress').textContent = order.shipping_address || 'Endereço não informado';
        document.getElementById('modalOrderPayment').textContent = getPaymentLabel(order.payment_method);
        document.getElementById('modalSubtotal').textContent = `R$ ${parseFloat(order.subtotal || order.total).toFixed(2)}`;
        document.getElementById('modalShipping').textContent = `R$ ${parseFloat(order.shipping || 0).toFixed(2)}`;
        document.getElementById('modalTotal').textContent = `R$ ${parseFloat(order.total).toFixed(2)}`;
        document.getElementById('modalOrderDate').textContent = formatDateFull(order.created_at);

        fetch(`/api/customer/orders/${orderId}/items`)
            .then(response => response.json())
            .then(items => {
                document.getElementById('modalOrderItems').innerHTML = items.map(item => `
                    <div class="modal-item">
                        <div class="modal-item-info">
                            <div class="modal-item-name">${item.name}</div>
                            <div class="modal-item-qty">Quantidade: ${item.quantity}</div>
                        </div>
                        <div class="modal-item-price">R$ ${parseFloat(item.price * item.quantity).toFixed(2)}</div>
                    </div>
                `).join('');
            })
            .catch(err => console.error('Error loading order items:', err));

        modal.classList.add('show');
    };

    function showEmptyState(message = null) {
        ordersList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-box-open"></i>
                <h3>${message || 'Nenhum pedido encontrado'}</h3>
                <p>${message ? 'Tente novamente mais tarde.' : 'Você ainda não fez nenhum pedido.'}</p>
                ${!message ? '<a href="/loja" class="btn btn-primary"><i class="fas fa-shopping-cart"></i> Ir às Compras</a>' : ''}
            </div>
        `;
    }

    function getStatusLabel(status) {
        const labels = {
            'pending': 'Pendente',
            'confirmed': 'Confirmado',
            'preparing': 'Preparando',
            'processing': 'Em Preparo',
            'shipped': 'Enviado',
            'out_for_delivery': 'Saiu para Entrega',
            'delivered': 'Entregue',
            'cancelled': 'Cancelado'
        };
        return labels[status] || status;
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

    function formatDate(dateString) {
        if (!dateString) return 'Data não disponível';

        try {
            const date = new Date(dateString);
            if (isNaN(date.getTime())) {
                return 'Data inválida';
            }
            return date.toLocaleDateString('pt-BR', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (e) {
            console.error('Erro ao formatar data:', e);
            return 'Data inválida';
        }
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
});