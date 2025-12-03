document.addEventListener('DOMContentLoaded', function() {
    const searchToggle = document.getElementById('searchToggle');
    const searchBar = document.getElementById('searchBar');
    const searchInput = document.getElementById('searchInput');
    const clearSearch = document.getElementById('clearSearch');
    const productsGrid = document.getElementById('productsGrid');
    const emptyState = document.getElementById('emptyState');
    const categoryBtns = document.querySelectorAll('.category-btn');
    const toast = document.getElementById('toast');
    const lastOrdersCard = document.getElementById('lastOrdersCard');
    const ordersList = document.getElementById('ordersList');
    const customerNameDisplay = document.getElementById('customerNameDisplay');

    let allProducts = [];
    let currentCategory = '';
    let searchTerm = '';

    loadProducts();
    updateCartBadge();
    loadLastOrders();

    searchToggle.addEventListener('click', function() {
        searchBar.classList.toggle('show');
        if (searchBar.classList.contains('show')) {
            searchInput.focus();
        }
    });

    searchInput.addEventListener('input', function() {
        searchTerm = this.value;
        clearSearch.classList.toggle('show', searchTerm.length > 0);
        filterProducts();
    });

    clearSearch.addEventListener('click', function() {
        searchInput.value = '';
        searchTerm = '';
        clearSearch.classList.remove('show');
        filterProducts();
    });

    categoryBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            categoryBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentCategory = this.dataset.category;
            filterProducts();
        });
    });

    function loadProducts() {
        fetch('/api/products')
            .then(response => response.json())
            .then(products => {
                allProducts = products;
                renderProducts(products);
            })
            .catch(err => console.error('Error loading products:', err));
    }

    function filterProducts() {
        let filtered = allProducts;

        if (currentCategory) {
            filtered = filtered.filter(p => p.category_id == currentCategory);
        }

        if (searchTerm) {
            const term = searchTerm.toLowerCase();
            filtered = filtered.filter(p => 
                p.name.toLowerCase().includes(term) || 
                (p.description && p.description.toLowerCase().includes(term))
            );
        }

        renderProducts(filtered);
    }

    function renderProducts(products) {
        if (products.length === 0) {
            productsGrid.style.display = 'none';
            emptyState.style.display = 'block';
            return;
        }

        productsGrid.style.display = 'grid';
        emptyState.style.display = 'none';

        productsGrid.innerHTML = products.map(product => `
            <div class="product-card" data-id="${product.id}">
                <div class="product-image">
                    <img src="${product.image_url || 'https://via.placeholder.com/300x300?text=Produto'}" alt="${product.name}" loading="lazy">
                    ${product.stock <= 5 && product.stock > 0 ? '<span class="product-badge warning">Últimas unidades</span>' : ''}
                    ${product.stock === 0 ? '<span class="product-badge danger">Esgotado</span>' : ''}
                </div>
                <div class="product-info">
                    <span class="product-category">${product.category_name || 'Geral'}</span>
                    <h3 class="product-name">${product.name}</h3>
                    <p class="product-description">${(product.description || '').substring(0, 80)}${product.description && product.description.length > 80 ? '...' : ''}</p>
                    <div class="product-footer">
                        <div class="product-price">
                            <span class="price">R$ ${formatPrice(product.price)}</span>
                        </div>
                        <button class="add-to-cart-btn" data-id="${product.id}" ${product.stock === 0 ? 'disabled' : ''}>
                            <i class="fas fa-plus"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');

        document.querySelectorAll('.add-to-cart-btn').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                addToCart(this.dataset.id);
            });
        });
    }

    function addToCart(productId) {
        fetch('/api/cart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_id: productId, quantity: 1 })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Produto adicionado ao carrinho!');
                updateCartBadge();
            }
        })
        .catch(err => console.error('Error adding to cart:', err));
    }

    function showToast(message, type = 'success') {
        toast.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : 'times-circle'}"></i><span>${message}</span>`;
        toast.classList.add('show');
        toast.classList.add(type);
        setTimeout(() => {
            toast.classList.remove('show');
            toast.classList.remove(type);
        }, 3000);
    }

    function formatPrice(price) {
        return parseFloat(price).toFixed(2).replace('.', ',');
    }

    // Verificar se o cliente está logado
    function checkLoginStatus() {
        fetch('/api/customer/check', {
            credentials: 'include', // Incluir cookies de sessão
            headers: {
                'Cache-Control': 'no-cache'
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.logged_in) {
                    showLoggedInMenu(data.customer_name);
                    loadLastOrders();
                } else {
                    showGuestMenu();
                }
            })
            .catch(err => console.error('Error checking login:', err));
    }

    function loadLastOrders() {
        fetch('/api/customer/last-orders', {
            credentials: 'include', // Incluir cookies de sessão
            headers: {
                'Cache-Control': 'no-cache'
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.logged_in && data.orders && data.orders.length > 0) {
                    customerNameDisplay.textContent = data.customer_name;

                    ordersList.innerHTML = data.orders.slice(0, 3).map(order => {
                        const statusMap = {
                            'pending': 'Pendente',
                            'confirmed': 'Confirmado',
                            'preparing': 'Preparando',
                            'processing': 'Em Preparo',
                            'shipped': 'Enviado',
                            'out_for_delivery': 'Em entrega',
                            'delivered': 'Entregue',
                            'cancelled': 'Cancelado'
                        };
                        const statusText = statusMap[order.status] || order.status;

                        // Formatar data corretamente
                        let formattedDate = 'Data inválida';
                        if (order.date) {
                            formattedDate = order.date;
                        } else if (order.created_at) {
                            try {
                                const orderDate = new Date(order.created_at);
                                if (!isNaN(orderDate.getTime())) {
                                    formattedDate = orderDate.toLocaleDateString('pt-BR', {
                                        day: '2-digit',
                                        month: '2-digit',
                                        year: 'numeric'
                                    });
                                }
                            } catch (e) {
                                console.error('Erro ao formatar data:', e);
                            }
                        };

                        return `
                            <div class="order-item-card">
                                <div class="order-item-header">
                                    <span class="order-id">#${order.id}</span>
                                    <span class="order-date">${formattedDate}</span>
                                </div>
                                <div class="order-item-info">
                                    <span>${order.item_count} ${order.item_count === 1 ? 'item' : 'itens'}</span>
                                    <span class="order-total">R$ ${order.total.toFixed(2).replace('.', ',')}</span>
                                </div>
                                <div class="order-item-status">
                                    <span class="status status-${order.status}">${statusText}</span>
                                    <a href="/acompanhar-pedido?id=${order.id}" class="track-order-btn">Acompanhar</a>
                                </div>
                            </div>
                        `;
                    }).join('');

                    lastOrdersCard.style.display = 'block';
                } else {
                    lastOrdersCard.style.display = 'none';
                }
            })
            .catch(err => {
                console.error('Error loading last orders:', err);
                lastOrdersCard.style.display = 'none';
            });
    }

    // Initial calls
    loadProducts();
    updateCartBadge();
    loadLastOrders();

    // Detectar quando o usuário volta para a página (após login)
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            updateCartBadge();
            loadLastOrders();
        }
    });

    // Placeholder for updateOrderStatus function if it's defined elsewhere and needed
    // If updateOrderStatus is not defined in the original script and not provided in changes,
    // it should not be added. Based on the provided <changes>, it seems like a function
    // that might exist in a different context or was intended to be part of the fix.
    // However, since it's not in the original and not fully defined in changes,
    // I'm omitting it to avoid introducing potentially unused or incomplete code.
    // If it was intended to be part of this file, its definition and usage context would be needed.

    // Example of how it *might* be used if defined and relevant:
    // function updateOrderStatus(orderId, newStatus, observations = '') { ... }
});

function updateCartBadge() {
    fetch('/api/cart')
        .then(response => response.json())
        .then(items => {
            const count = items.reduce((total, item) => total + item.quantity, 0);
            document.querySelectorAll('.cart-badge, #cartBadge, #cartBadgeFab').forEach(badge => {
                badge.textContent = count;
                badge.style.display = count > 0 ? 'flex' : 'none';
            });
        })
        .catch(err => console.error('Error loading cart:', err));
}