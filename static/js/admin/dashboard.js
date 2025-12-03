document.addEventListener('DOMContentLoaded', function() {
    loadDashboardData();
    loadNewOrders();
    
    // Atualizar novos pedidos a cada 30 segundos
    setInterval(loadNewOrders, 30000);
    
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            loadDashboardData();
        });
    });
});

let salesChart, ordersStatusChart, topProductsChart;

function loadDashboardData() {
    fetch('/api/admin/dashboard')
        .then(response => response.json())
        .then(data => {
            document.getElementById('totalOrders').textContent = data.total_orders;
            document.getElementById('totalRevenue').textContent = formatCurrency(data.total_revenue);
            document.getElementById('totalCustomers').textContent = data.total_customers;
            document.getElementById('pendingOrders').textContent = data.pending_orders;
            document.getElementById('abandonedCarts').textContent = data.abandoned_carts;
            document.getElementById('totalProducts').textContent = data.total_products;
            
            const pendingBadge = document.getElementById('pendingBadge');
            if (data.pending_orders > 0) {
                pendingBadge.style.display = 'inline';
            } else {
                pendingBadge.style.display = 'none';
            }
            
            renderSalesChart(data.sales_by_day);
            renderOrdersStatusChart(data.orders_by_status);
            renderTopProductsChart(data.top_products);
            renderRecentOrders(data.recent_orders);
        })
        .catch(err => console.error('Error loading dashboard:', err));
}

function renderSalesChart(salesData) {
    const ctx = document.getElementById('salesChart').getContext('2d');
    
    const labels = salesData.map(s => formatDateShort(s.date)).reverse();
    const values = salesData.map(s => s.total).reverse();
    
    if (salesChart) salesChart.destroy();
    
    salesChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Vendas',
                data: values,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#667eea',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return formatCurrency(context.parsed.y);
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    }
                }
            }
        }
    });
}

function renderOrdersStatusChart(statusData) {
    const ctx = document.getElementById('ordersStatusChart').getContext('2d');
    
    const colors = {
        'pending': '#f59e0b',
        'confirmed': '#3b82f6',
        'processing': '#8b5cf6',
        'shipped': '#06b6d4',
        'delivered': '#10b981',
        'cancelled': '#ef4444'
    };
    
    const labels = statusData.map(s => getStatusLabel(s.status));
    const values = statusData.map(s => s.count);
    const bgColors = statusData.map(s => colors[s.status] || '#999');
    
    if (ordersStatusChart) ordersStatusChart.destroy();
    
    ordersStatusChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: bgColors,
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { boxWidth: 12, padding: 15 }
                }
            }
        }
    });
}

function renderTopProductsChart(productsData) {
    const ctx = document.getElementById('topProductsChart').getContext('2d');
    
    const labels = productsData.map(p => p.name.substring(0, 15) + (p.name.length > 15 ? '...' : ''));
    const values = productsData.map(p => p.total_sold);
    
    if (topProductsChart) topProductsChart.destroy();
    
    topProductsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Vendidos',
                data: values,
                backgroundColor: 'rgba(102, 126, 234, 0.8)',
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: { beginAtZero: true }
            }
        }
    });
}

function loadNewOrders() {
    fetch('/api/admin/new-orders')
        .then(response => response.json())
        .then(orders => {
            const newOrdersList = document.getElementById('newOrdersList');
            
            if (orders.length === 0) {
                newOrdersList.innerHTML = `
                    <div style="text-align: center; padding: 20px; opacity: 0.8;">
                        <i class="fas fa-inbox" style="font-size: 30px; margin-bottom: 10px;"></i>
                        <p>Nenhum pedido novo no momento</p>
                    </div>
                `;
                return;
            }
            
            newOrdersList.innerHTML = orders.map(order => `
                <div class="new-order-item" onclick="window.location.href='/admin/pedidos'">
                    <div class="new-order-header">
                        <span class="new-order-number">Pedido #${order.id}</span>
                        <span class="new-order-time">${getTimeAgo(order.created_at)}</span>
                    </div>
                    <div class="new-order-customer">
                        <i class="fas fa-user"></i> ${order.customer_name || 'Cliente'}
                    </div>
                    <div class="new-order-value">
                        <i class="fas fa-dollar-sign"></i> ${formatCurrency(order.total)}
                    </div>
                </div>
            `).join('');
        })
        .catch(err => console.error('Erro ao carregar novos pedidos:', err));
}

function getTimeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffInMinutes = Math.floor((now - date) / 60000);
    
    if (diffInMinutes < 1) return 'Agora';
    if (diffInMinutes < 60) return `${diffInMinutes}min atrás`;
    
    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) return `${diffInHours}h atrás`;
    
    return formatDateShort(dateString);
}

function renderRecentOrders(orders) {
    const tbody = document.getElementById('recentOrdersTable');
    
    tbody.innerHTML = orders.map(order => `
        <tr>
            <td>#${order.id}</td>
            <td>${order.customer_name || 'Cliente'}</td>
            <td>${formatCurrency(order.total)}</td>
            <td><span class="status-badge ${getStatusClass(order.status)}">${getStatusLabel(order.status)}</span></td>
            <td>${formatDateShort(order.created_at)}</td>
        </tr>
    `).join('');
}
