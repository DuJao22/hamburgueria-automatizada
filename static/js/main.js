document.addEventListener('DOMContentLoaded', function() {
    updateCartBadge();
    fetch('/api/customer/check')
        .then(response => response.json())
        .then(data => {
            if (data.logged_in) {
                updateUserInfo(data.customer_name);
                const ordersLink = document.getElementById('ordersLink');
                if (ordersLink) {
                    ordersLink.style.display = 'flex';
                }
            }
        })
        .catch(err => console.error('Error checking customer login:', err));
});

function updateCartBadge() {
    fetch('/api/cart')
        .then(response => response.json())
        .then(items => {
            const count = items.reduce((total, item) => total + item.quantity, 0);
            document.querySelectorAll('.cart-badge, #cartBadge').forEach(badge => {
                badge.textContent = count;
                badge.style.display = count > 0 ? 'flex' : 'none';
            });
        })
        .catch(err => console.error('Error loading cart:', err));
}

function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    if (toast) {
        toast.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i><span>${message}</span>`;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 3000);
    }
}

function updateUserInfo(customerName) {
    const userInfoElement = document.getElementById('userInfo');
    if (userInfoElement) {
        userInfoElement.textContent = `Olá, ${customerName}!`;
        userInfoElement.style.display = 'flex';
    }
    const loginLogoutButton = document.getElementById('loginLogoutButton');
    if (loginLogoutButton) {
        loginLogoutButton.textContent = 'Sair';
        loginLogoutButton.onclick = handleLogout;
    }
}

function handleLogout() {
    fetch('/api/customer/logout', { method: 'POST' })
        .then(response => {
            if (response.ok) {
                window.location.href = '/login';
            } else {
                showToast('Erro ao sair. Tente novamente.', 'error');
            }
        })
        .catch(err => {
            console.error('Error during logout:', err);
            showToast('Erro ao sair. Tente novamente.', 'error');
        });
}