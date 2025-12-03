document.addEventListener('DOMContentLoaded', function() {
    const cartItemsContainer = document.getElementById('cartItems');
    const cartEmpty = document.getElementById('cartEmpty');
    const cartFooter = document.getElementById('cartFooter');
    const subtotalEl = document.getElementById('subtotal');
    const shippingEl = document.getElementById('shipping');
    const totalEl = document.getElementById('total');
    const checkoutBtn = document.getElementById('checkoutBtn');
    const clearCartBtn = document.getElementById('clearCartBtn');

    let cartItems = [];

    loadCart();

    clearCartBtn.addEventListener('click', function() {
        if (confirm('Limpar todo o carrinho?')) {
            clearCart();
        }
    });

    const paymentModal = document.getElementById('paymentModal');
    const closePaymentModal = document.getElementById('closePaymentModal');
    const paymentOptionBtns = document.querySelectorAll('.payment-option-btn');
    const trocoSection = document.getElementById('trocoSection');
    const trocoInput = document.getElementById('trocoInput');
    const confirmarTrocoBtn = document.getElementById('confirmarTroco');
    const trocoBtns = document.querySelectorAll('.troco-btn[data-troco]');

    let selectedPayment = null;
    let trocoValue = null;

    checkoutBtn.addEventListener('click', function() {
        if (cartItems.length === 0) {
            alert('Seu carrinho está vazio!');
            return;
        }
        paymentModal.classList.add('show');
    });

    closePaymentModal.addEventListener('click', function() {
        paymentModal.classList.remove('show');
        trocoSection.style.display = 'none';
        selectedPayment = null;
        trocoValue = null;
    });

    paymentModal.addEventListener('click', function(e) {
        if (e.target === paymentModal) {
            paymentModal.classList.remove('show');
            trocoSection.style.display = 'none';
            selectedPayment = null;
            trocoValue = null;
        }
    });

    paymentOptionBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            selectedPayment = this.dataset.payment;

            if (selectedPayment === 'dinheiro') {
                trocoSection.style.display = 'block';
            } else {
                finalizarPedido(selectedPayment, null);
            }
        });
    });

    trocoBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            trocoValue = 'nao';
            finalizarPedido('dinheiro', trocoValue);
        });
    });

    confirmarTrocoBtn.addEventListener('click', function() {
        const valor = trocoInput.value.trim();
        if (!valor) {
            alert('Por favor, informe o valor para o troco');
            return;
        }
        trocoValue = valor;
        finalizarPedido('dinheiro', trocoValue);
    });

    function finalizarPedido(pagamento, troco) {
        fetch('/api/checkout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                payment_method: pagamento,
                troco: troco
            })
        })
        .then(response => response.json())
        .then(data => {
            paymentModal.classList.remove('show');
            trocoSection.style.display = 'none';
            selectedPayment = null;
            trocoValue = null;

            if (data.success) {
                alert(`Pedido #${data.order_id} enviado com sucesso! Aguarde a confirmação.`);
                loadCart();
            } else {
                alert(data.error || 'Erro ao enviar pedido. Tente novamente.');
            }
        })
        .catch(err => {
            console.error('Error finalizing order:', err);
            alert('Erro ao enviar pedido. Tente novamente.');
            paymentModal.classList.remove('show');
        });
    }

    function loadCart() {
        fetch('/api/cart')
            .then(response => response.json())
            .then(items => {
                cartItems = items;
                renderCart();
            })
            .catch(err => console.error('Error loading cart:', err));
    }

    function renderCart() {
        if (cartItems.length === 0) {
            cartItemsContainer.style.display = 'none';
            cartEmpty.style.display = 'block';
            cartFooter.style.display = 'none';
            return;
        }

        cartItemsContainer.style.display = 'flex';
        cartEmpty.style.display = 'none';
        cartFooter.style.display = 'block';

        cartItemsContainer.innerHTML = cartItems.map(item => `
            <div class="cart-item" data-id="${item.id}">
                <div class="cart-item-image">
                    <img src="${item.image_url || 'https://via.placeholder.com/100x100?text=Produto'}" alt="${item.name}">
                </div>
                <div class="cart-item-info">
                    <h3 class="cart-item-name">${item.name}</h3>
                    <span class="cart-item-price">R$ ${formatPrice(item.price)}</span>
                    <div class="cart-item-actions">
                        <div class="quantity-control">
                            <button class="quantity-btn minus" data-id="${item.id}">-</button>
                            <span class="quantity-value">${item.quantity}</span>
                            <button class="quantity-btn plus" data-id="${item.id}">+</button>
                        </div>
                        <button class="remove-item-btn" data-id="${item.id}">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');

        document.querySelectorAll('.quantity-btn.minus').forEach(btn => {
            btn.addEventListener('click', () => updateQuantity(btn.dataset.id, -1));
        });

        document.querySelectorAll('.quantity-btn.plus').forEach(btn => {
            btn.addEventListener('click', () => updateQuantity(btn.dataset.id, 1));
        });

        document.querySelectorAll('.remove-item-btn').forEach(btn => {
            btn.addEventListener('click', () => removeItem(btn.dataset.id));
        });

        updateSummary();
    }

    function updateQuantity(itemId, change) {
        const item = cartItems.find(i => i.id == itemId);
        if (!item) return;

        const newQuantity = item.quantity + change;
        if (newQuantity < 1) {
            removeItem(itemId);
            return;
        }

        fetch('/api/cart', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_id: itemId, quantity: newQuantity })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loadCart();
            }
        })
        .catch(err => console.error('Error updating quantity:', err));
    }

    function removeItem(itemId) {
        fetch(`/api/cart?item_id=${itemId}`, { method: 'DELETE' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    loadCart();
                }
            })
            .catch(err => console.error('Error removing item:', err));
    }

    function clearCart() {
        const promises = cartItems.map(item => 
            fetch(`/api/cart?item_id=${item.id}`, { method: 'DELETE' })
        );

        Promise.all(promises).then(() => {
            loadCart();
        });
    }

    function updateSummary() {
        const subtotal = cartItems.reduce((total, item) => total + (item.price * item.quantity), 0);
        const shipping = subtotal > 0 ? 15.00 : 0;
        const total = subtotal + shipping;

        subtotalEl.textContent = `R$ ${formatPrice(subtotal)}`;
        shippingEl.textContent = shipping > 0 ? `R$ ${formatPrice(shipping)}` : 'Grátis';
        totalEl.textContent = `R$ ${formatPrice(total)}`;
    }

    function formatPrice(price) {
        return parseFloat(price).toFixed(2).replace('.', ',');
    }

    function verificarAutenticacao() {
        // Verifica se há customer_id na sessão checando se o login retorna sucesso
        fetch('/api/customer/check')
            .then(response => response.json())
            .then(data => {
                const checkoutBtn = document.getElementById('checkoutBtn');
                const loginBtn = document.getElementById('loginBtn');

                if (data.logged_in) {
                    checkoutBtn.style.display = 'flex';
                    loginBtn.style.display = 'none';
                    // Recarregar carrinho após detectar login para mostrar itens transferidos
                    loadCart();
                } else {
                    checkoutBtn.style.display = 'none';
                    loginBtn.style.display = 'flex';
                }
            })
            .catch(() => {
                // Se houver erro, assume que não está logado
                document.getElementById('checkoutBtn').style.display = 'none';
                document.getElementById('loginBtn').style.display = 'flex';
            });
    }

    function carregarCarrinho() {
        fetch('/api/cart')
            .then(response => response.json())
            .then(items => {
                cartItems = items;
                renderCart();
            })
            .catch(err => console.error('Error loading cart:', err));
    }

    // Chama verificarAutenticacao após carregar o carrinho e renderizar
    // Isso garante que os botões sejam exibidos corretamente na primeira carga da página
    verificarAutenticacao(); 
});