document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('productModal');
    const addBtn = document.getElementById('addProductBtn');
    const closeBtn = document.getElementById('closeModal');
    const cancelBtn = document.getElementById('cancelBtn');
    const form = document.getElementById('productForm');
    const searchInput = document.getElementById('searchProducts');
    const categoryFilter = document.getElementById('categoryFilter');
    const statusFilter = document.getElementById('statusFilter');
    
    let products = [];
    let categories = [];

    loadProducts();
    loadCategories();

    addBtn.addEventListener('click', () => openModal());
    closeBtn.addEventListener('click', () => closeModal());
    cancelBtn.addEventListener('click', () => closeModal());
    
    modal.addEventListener('click', function(e) {
        if (e.target === modal) closeModal();
    });

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        saveProduct();
    });

    searchInput.addEventListener('input', filterProducts);
    categoryFilter.addEventListener('change', filterProducts);
    statusFilter.addEventListener('change', filterProducts);

    function loadProducts() {
        fetch('/api/admin/products')
            .then(response => response.json())
            .then(data => {
                products = data;
                renderProducts(data);
            })
            .catch(err => console.error('Error loading products:', err));
    }

    function loadCategories() {
        fetch('/api/admin/categories')
            .then(response => response.json())
            .then(data => {
                categories = data;
                renderCategoryOptions();
            })
            .catch(err => console.error('Error loading categories:', err));
    }

    function renderCategoryOptions() {
        const options = categories.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
        categoryFilter.innerHTML = '<option value="">Todas Categorias</option>' + options;
        document.getElementById('productCategory').innerHTML = '<option value="">Selecione...</option>' + options;
    }

    function renderProducts(data) {
        const tbody = document.getElementById('productsTableBody');
        
        tbody.innerHTML = data.map(product => `
            <tr>
                <td>
                    <img src="${product.image_url || 'https://via.placeholder.com/50x50?text=P'}" 
                         alt="${product.name}" 
                         style="width: 50px; height: 50px; object-fit: cover; border-radius: 8px;">
                </td>
                <td><strong>${product.name}</strong></td>
                <td>${product.category_name || '-'}</td>
                <td>${formatCurrency(product.price)}</td>
                <td>${product.stock}</td>
                <td>
                    <span class="status-badge ${product.active ? 'status-delivered' : 'status-cancelled'}">
                        ${product.active ? 'Ativo' : 'Inativo'}
                    </span>
                </td>
                <td>
                    <button class="btn btn-secondary" onclick="editProduct(${product.id})" style="padding: 8px 12px;">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-secondary" onclick="deleteProduct(${product.id})" style="padding: 8px 12px; color: #ef4444;">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    }

    function filterProducts() {
        let filtered = products;
        
        const search = searchInput.value.toLowerCase();
        if (search) {
            filtered = filtered.filter(p => p.name.toLowerCase().includes(search));
        }
        
        const category = categoryFilter.value;
        if (category) {
            filtered = filtered.filter(p => p.category_id == category);
        }
        
        const status = statusFilter.value;
        if (status !== '') {
            filtered = filtered.filter(p => p.active == status);
        }
        
        renderProducts(filtered);
    }

    function openModal(product = null) {
        document.getElementById('modalTitle').textContent = product ? 'Editar Produto' : 'Novo Produto';
        document.getElementById('productId').value = product ? product.id : '';
        document.getElementById('productName').value = product ? product.name : '';
        document.getElementById('productPrice').value = product ? product.price : '';
        document.getElementById('productDescription').value = product ? product.description || '' : '';
        document.getElementById('productCategory').value = product ? product.category_id || '' : '';
        document.getElementById('productStock').value = product ? product.stock : 0;
        document.getElementById('productImage').value = product ? product.image_url || '' : '';
        document.getElementById('productActive').checked = product ? product.active : true;
        
        modal.classList.add('show');
    }

    function closeModal() {
        modal.classList.remove('show');
        form.reset();
    }

    function saveProduct() {
        const id = document.getElementById('productId').value;
        const data = {
            name: document.getElementById('productName').value,
            price: parseFloat(document.getElementById('productPrice').value),
            description: document.getElementById('productDescription').value,
            category_id: document.getElementById('productCategory').value || null,
            stock: parseInt(document.getElementById('productStock').value) || 0,
            image_url: document.getElementById('productImage').value,
            active: document.getElementById('productActive').checked ? 1 : 0
        };
        
        if (id) data.id = parseInt(id);
        
        fetch('/api/admin/products', {
            method: id ? 'PUT' : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                closeModal();
                loadProducts();
            }
        })
        .catch(err => console.error('Error saving product:', err));
    }

    window.editProduct = function(id) {
        const product = products.find(p => p.id === id);
        if (product) openModal(product);
    };

    window.deleteProduct = function(id) {
        if (confirm('Deseja realmente excluir este produto?')) {
            fetch(`/api/admin/products?id=${id}`, { method: 'DELETE' })
                .then(response => response.json())
                .then(result => {
                    if (result.success) loadProducts();
                })
                .catch(err => console.error('Error deleting product:', err));
        }
    };
});
