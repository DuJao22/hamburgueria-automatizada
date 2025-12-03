document.addEventListener('DOMContentLoaded', function() {
    const reportTabs = document.querySelectorAll('.report-tab');
    const applyDateRange = document.getElementById('applyDateRange');
    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');
    
    const today = new Date();
    const thirtyDaysAgo = new Date(today.getTime() - (30 * 24 * 60 * 60 * 1000));
    
    startDate.value = thirtyDaysAgo.toISOString().split('T')[0];
    endDate.value = today.toISOString().split('T')[0];

    let dailySalesChart, categorySalesChart, newCustomersChart, topProductsReportChart;

    loadSalesReport();

    reportTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            reportTabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            document.querySelectorAll('.report-content').forEach(c => c.style.display = 'none');
            
            const reportId = this.dataset.report + 'Report';
            document.getElementById(reportId).style.display = 'block';
            
            switch(this.dataset.report) {
                case 'sales': loadSalesReport(); break;
                case 'customers': loadCustomersReport(); break;
                case 'products': loadProductsReport(); break;
                case 'abandoned': loadAbandonedReport(); break;
            }
        });
    });

    applyDateRange.addEventListener('click', function() {
        const activeTab = document.querySelector('.report-tab.active');
        if (activeTab) {
            activeTab.click();
        }
    });

    function loadSalesReport() {
        const start = startDate.value;
        const end = endDate.value;
        
        fetch(`/api/admin/reports/sales?start_date=${start}&end_date=${end}`)
            .then(response => response.json())
            .then(data => {
                const totalSales = data.daily_sales.reduce((sum, d) => sum + d.revenue, 0);
                const totalOrders = data.daily_sales.reduce((sum, d) => sum + d.orders, 0);
                const avgTicket = totalOrders > 0 ? totalSales / totalOrders : 0;
                
                document.getElementById('totalSales').textContent = formatCurrency(totalSales);
                document.getElementById('totalOrdersReport').textContent = totalOrders;
                document.getElementById('avgTicket').textContent = formatCurrency(avgTicket);
                
                renderDailySalesChart(data.daily_sales);
                renderCategorySalesChart(data.category_sales);
            })
            .catch(err => console.error('Error loading sales report:', err));
    }

    function loadCustomersReport() {
        fetch('/api/admin/reports/customers')
            .then(response => response.json())
            .then(data => {
                const totalNew = data.new_customers_by_day.reduce((sum, d) => sum + d.count, 0);
                document.getElementById('newCustomers').textContent = totalNew;
                
                renderNewCustomersChart(data.new_customers_by_day);
                renderTopCustomersTable(data.top_customers);
            })
            .catch(err => console.error('Error loading customers report:', err));
    }

    function loadProductsReport() {
        fetch('/api/admin/dashboard')
            .then(response => response.json())
            .then(data => {
                renderTopProductsReportChart(data.top_products);
            })
            .catch(err => console.error('Error loading products report:', err));
    }

    function loadAbandonedReport() {
        fetch('/api/admin/reports/abandoned-carts')
            .then(response => response.json())
            .then(data => {
                document.getElementById('abandonedCount').textContent = data.length;
                
                const totalValue = data.reduce((sum, c) => sum + (c.cart_value || 0), 0);
                document.getElementById('abandonedValue').textContent = formatCurrency(totalValue);
                
                renderAbandonedTable(data);
            })
            .catch(err => console.error('Error loading abandoned carts:', err));
    }

    function renderDailySalesChart(data) {
        const ctx = document.getElementById('dailySalesChart').getContext('2d');
        
        const labels = data.map(d => formatDateShort(d.date));
        const revenues = data.map(d => d.revenue);
        const orders = data.map(d => d.orders);
        
        if (dailySalesChart) dailySalesChart.destroy();
        
        dailySalesChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Receita',
                        data: revenues,
                        backgroundColor: 'rgba(102, 126, 234, 0.8)',
                        borderRadius: 6,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Pedidos',
                        data: orders,
                        type: 'line',
                        borderColor: '#10b981',
                        backgroundColor: 'transparent',
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        type: 'linear',
                        position: 'left',
                        ticks: {
                            callback: value => formatCurrency(value)
                        }
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });
    }

    function renderCategorySalesChart(data) {
        const ctx = document.getElementById('categorySalesChart').getContext('2d');
        
        const labels = data.map(c => c.name || 'Sem categoria');
        const values = data.map(c => c.revenue);
        
        const colors = ['#667eea', '#764ba2', '#10b981', '#f59e0b', '#ef4444', '#06b6d4'];
        
        if (categorySalesChart) categorySalesChart.destroy();
        
        categorySalesChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors.slice(0, data.length),
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    function renderNewCustomersChart(data) {
        const ctx = document.getElementById('newCustomersChart').getContext('2d');
        
        const labels = data.map(d => formatDateShort(d.date));
        const values = data.map(d => d.count);
        
        if (newCustomersChart) newCustomersChart.destroy();
        
        newCustomersChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Novos Clientes',
                    data: values,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } }
            }
        });
    }

    function renderTopCustomersTable(data) {
        const tbody = document.getElementById('topCustomersTable');
        
        tbody.innerHTML = data.map(c => `
            <tr>
                <td>${c.name}</td>
                <td>${c.phone || '-'}</td>
                <td>${c.orders}</td>
                <td>${formatCurrency(c.total_spent)}</td>
            </tr>
        `).join('') || '<tr><td colspan="4">Nenhum cliente</td></tr>';
    }

    function renderTopProductsReportChart(data) {
        const ctx = document.getElementById('topProductsReportChart').getContext('2d');
        
        const labels = data.map(p => p.name);
        const values = data.map(p => p.revenue);
        
        if (topProductsReportChart) topProductsReportChart.destroy();
        
        topProductsReportChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Receita',
                    data: values,
                    backgroundColor: 'rgba(102, 126, 234, 0.8)',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: { legend: { display: false } },
                scales: {
                    x: {
                        ticks: {
                            callback: value => formatCurrency(value)
                        }
                    }
                }
            }
        });
    }

    function renderAbandonedTable(data) {
        const tbody = document.getElementById('abandonedCartsTable');
        
        tbody.innerHTML = data.map(c => `
            <tr>
                <td>${c.customer_name}</td>
                <td>${c.item_count}</td>
                <td>${formatCurrency(c.cart_value)}</td>
                <td>${formatDate(c.last_activity)}</td>
                <td>
                    <button class="btn btn-secondary" style="padding: 6px 10px; font-size: 12px;">
                        <i class="fas fa-bell"></i> Notificar
                    </button>
                </td>
            </tr>
        `).join('') || '<tr><td colspan="5">Nenhum carrinho abandonado</td></tr>';
    }
});
