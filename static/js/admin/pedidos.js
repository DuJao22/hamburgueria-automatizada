document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('orderModal');
    const closeBtn = document.getElementById('closeOrderModal');
    const statusTabs = document.querySelectorAll('.status-tab');
    const updateStatusBtn = document.getElementById('updateStatusBtn');

    let orders = [];
    let currentOrder = null;

    loadOrders();

    closeBtn.addEventListener('click', () => closeModal());
    modal.addEventListener('click', function(e) {
        if (e.target === modal) closeModal();
    });

    statusTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            statusTabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            filterOrders(this.dataset.status);
        });
    });

    updateStatusBtn.addEventListener('click', updateOrderStatus);

    function loadOrders(status = '') {
        const url = status ? `/api/admin/orders?status=${status}` : '/api/admin/orders';

        fetch(url)
            .then(response => response.json())
            .then(data => {
                orders = data;
                renderOrders(data);
                updateStatusCounts();
            })
            .catch(err => console.error('Error loading orders:', err));
    }

    function filterOrders(status) {
        if (status) {
            const filtered = orders.filter(o => o.status === status);
            renderOrders(filtered);
        } else {
            renderOrders(orders);
        }
    }

    function renderOrders(data) {
        const tbody = document.getElementById('ordersTableBody');

        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 40px; color: #999;">Nenhum pedido encontrado</td></tr>';
            return;
        }

        tbody.innerHTML = data.map(order => `
            <tr>
                <td><strong>#${order.id}</strong></td>
                <td>
                    <div>${order.customer_name || 'Cliente'}</div>
                    <small style="color: #999;">${order.customer_phone || ''}</small>
                </td>
                <td>-</td>
                <td><strong>${formatCurrency(order.total)}</strong></td>
                <td><span class="status-badge ${getStatusClass(order.status)}">${getStatusLabel(order.status)}</span></td>
                <td>${formatDateShort(order.created_at)}</td>
                <td>
                    <button class="btn btn-secondary" onclick="viewOrder(${order.id})" style="padding: 8px 12px;">
                        <i class="fas fa-eye"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    }

    function updateStatusCounts() {
        const pending = orders.filter(o => o.status === 'pending').length;
        const processing = orders.filter(o => o.status === 'processing').length;
        const shipped = orders.filter(o => o.status === 'shipped').length;

        document.getElementById('pendingCount').textContent = pending;
        document.getElementById('processingCount').textContent = processing;
        document.getElementById('shippedCount').textContent = shipped;
    }

    window.viewOrder = function(id) {
        currentOrder = orders.find(o => o.id === id);
        if (!currentOrder) return;

        showOrderDetails(currentOrder);

        modal.classList.add('show');
    };

    function showOrderDetails(order) {
        document.getElementById('orderNumber').textContent = order.id;

        const customerInfo = document.getElementById('customerInfo');
        const paymentLabel = {
            'pending': 'Pendente',
            'dinheiro': 'Dinheiro',
            'cartao': 'Cartão',
            'pix': 'PIX'
        }[order.payment_method] || order.payment_method;

        const paymentBadge = `<span class="order-badge payment-${order.payment_method || 'pending'}">${paymentLabel}</span>`;

        customerInfo.innerHTML = `
            <div class="info-row">
                <span class="info-label">Nome:</span>
                <span class="info-value">${order.customer_name || 'Cliente Anônimo'}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Telefone:</span>
                <span class="info-value">${order.customer_phone || 'Não informado'}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Endereço:</span>
                <span class="info-value">
                    <div class="address-box">${order.shipping_address || 'Não informado'}</div>
                </span>
            </div>
            <div class="info-row">
                <span class="info-label">Pagamento:</span>
                <span class="info-value">${paymentBadge}</span>
            </div>
            ${order.notes ? `
            <div class="info-row">
                <span class="info-label">Observações:</span>
                <span class="info-value">
                    <div class="order-notes">${order.notes}</div>
                </span>
            </div>` : ''}
        `;

        fetch(`/api/admin/orders/${order.id}/items`)
            .then(res => res.json())
            .then(items => {
                const tbody = document.getElementById('orderItemsBody');
                tbody.innerHTML = items.map(item => `
                    <tr>
                        <td>
                            <div class="product-info">
                                ${item.image_url ?
                                    `<img src="${item.image_url}" alt="${item.name}" class="product-image">` :
                                    `<div class="product-image"><i class="fas fa-box"></i></div>`
                                }
                                <span class="product-name">${item.name}</span>
                            </div>
                        </td>
                        <td><strong>${item.quantity}</strong></td>
                        <td>${formatCurrency(item.price)}</td>
                        <td><strong>${formatCurrency(item.quantity * item.price)}</strong></td>
                    </tr>
                `).join('');
            });

        const summary = document.getElementById('orderSummary');
        summary.innerHTML = `
            <div class="summary-row">
                <span class="summary-label">Subtotal:</span>
                <span class="summary-value">${formatCurrency(order.subtotal)}</span>
            </div>
            <div class="summary-row">
                <span class="summary-label">Frete:</span>
                <span class="summary-value">${formatCurrency(order.shipping)}</span>
            </div>
            ${order.discount > 0 ? `
            <div class="summary-row">
                <span class="summary-label">Desconto:</span>
                <span class="summary-value">-${formatCurrency(order.discount)}</span>
            </div>` : ''}
            <div class="summary-row total">
                <span class="summary-label">Total:</span>
                <span class="summary-value">${formatCurrency(order.total)}</span>
            </div>
        `;

        document.getElementById('newStatus').value = order.status;

        document.getElementById('orderModal').classList.add('show');
    }

    function closeModal() {
        modal.classList.remove('show');
        currentOrder = null;
    }

    function updateOrderStatus() {
        if (!currentOrder) return;

        const newStatus = document.getElementById('newStatus').value;
        const notes = document.getElementById('statusNotes').value;

        fetch('/api/admin/orders', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: currentOrder.id,
                status: newStatus,
                notes: notes
            })
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                closeModal();
                loadOrders();
            }
        })
        .catch(err => console.error('Error updating status:', err));
    }
});