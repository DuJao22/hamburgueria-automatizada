document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchCustomers');
    const modal = document.getElementById('customerModal');
    const closeBtn = document.getElementById('closeCustomerModal');
    
    let customers = [];

    loadCustomers();

    searchInput.addEventListener('input', function() {
        const term = this.value.toLowerCase();
        const filtered = customers.filter(c => 
            c.name.toLowerCase().includes(term) || 
            (c.phone && c.phone.includes(term))
        );
        renderCustomers(filtered);
    });

    closeBtn.addEventListener('click', () => modal.classList.remove('show'));
    modal.addEventListener('click', function(e) {
        if (e.target === modal) modal.classList.remove('show');
    });

    function loadCustomers() {
        fetch('/api/admin/customers')
            .then(response => response.json())
            .then(data => {
                customers = data;
                document.getElementById('totalCustomers').textContent = data.length;
                renderCustomers(data);
            })
            .catch(err => console.error('Error loading customers:', err));
    }

    function renderCustomers(data) {
        const tbody = document.getElementById('customersTableBody');
        
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 40px; color: #999;">Nenhum cliente encontrado</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.map(customer => `
            <tr>
                <td><strong>${customer.name}</strong></td>
                <td>${customer.phone || '-'}</td>
                <td>${customer.city || '-'}</td>
                <td>${customer.order_count}</td>
                <td>${formatCurrency(customer.total_spent)}</td>
                <td>${formatDateShort(customer.created_at)}</td>
                <td>
                    <button class="btn btn-secondary" onclick="viewCustomer(${customer.id})" style="padding: 8px 12px;">
                        <i class="fas fa-eye"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    }

    window.viewCustomer = function(id) {
        const customer = customers.find(c => c.id === id);
        if (!customer) return;
        
        let address = '-';
        try {
            if (customer.address) {
                const addr = typeof customer.address === 'string' ? JSON.parse(customer.address) : customer.address;
                address = `${addr.logradouro || ''}, ${customer.number || ''} - ${addr.bairro || ''}, ${addr.localidade || ''} - ${addr.uf || ''}`;
            }
        } catch(e) {
            address = customer.address || '-';
        }
        
        document.getElementById('customerDetails').innerHTML = `
            <div class="customer-profile">
                <div class="profile-header">
                    <div class="profile-avatar">
                        <i class="fas fa-user"></i>
                    </div>
                    <div class="profile-info">
                        <h2>${customer.name}</h2>
                        <p>${customer.phone || 'Sem telefone'}</p>
                    </div>
                </div>
                
                <div class="profile-stats">
                    <div class="profile-stat">
                        <span class="stat-value">${customer.order_count}</span>
                        <span class="stat-label">Pedidos</span>
                    </div>
                    <div class="profile-stat">
                        <span class="stat-value">${formatCurrency(customer.total_spent)}</span>
                        <span class="stat-label">Total Gasto</span>
                    </div>
                </div>
                
                <div class="profile-section">
                    <h3>Informações</h3>
                    <div class="info-grid">
                        <div class="info-item">
                            <label>Email</label>
                            <span>${customer.email || '-'}</span>
                        </div>
                        <div class="info-item">
                            <label>CEP</label>
                            <span>${customer.cep || '-'}</span>
                        </div>
                        <div class="info-item">
                            <label>Endereço</label>
                            <span>${address}</span>
                        </div>
                        <div class="info-item">
                            <label>Cadastro</label>
                            <span>${formatDate(customer.created_at)}</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <style>
                .customer-profile { padding: 25px; }
                .profile-header { display: flex; align-items: center; gap: 20px; margin-bottom: 25px; }
                .profile-avatar { width: 80px; height: 80px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 32px; }
                .profile-info h2 { margin-bottom: 5px; }
                .profile-info p { color: #666; }
                .profile-stats { display: flex; gap: 30px; padding: 20px; background: #f5f5f5; border-radius: 12px; margin-bottom: 25px; }
                .profile-stat { text-align: center; }
                .profile-stat .stat-value { display: block; font-size: 24px; font-weight: 700; color: #667eea; }
                .profile-stat .stat-label { font-size: 13px; color: #666; }
                .profile-section h3 { margin-bottom: 15px; font-size: 16px; }
                .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
                .info-item label { display: block; font-size: 12px; color: #999; margin-bottom: 5px; }
                .info-item span { font-size: 14px; color: #333; }
            </style>
        `;
        
        modal.classList.add('show');
    };
});
