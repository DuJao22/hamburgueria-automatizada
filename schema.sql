-- Schema do banco de dados SQLite3
-- Sistema Burger House - Hamburgueria Artesanal
-- Desenvolvido por João Layon - Full Stack Developer

-- Tabela de usuários (admin)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT,
    is_admin INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de clientes
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT UNIQUE,
    email TEXT,
    cep TEXT,
    address TEXT,
    number TEXT,
    complement TEXT,
    neighborhood TEXT,
    city TEXT,
    state TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Tabela de categorias
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    image_url TEXT,
    active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de produtos
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    image_url TEXT,
    category_id INTEGER,
    stock INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- Tabela de variantes de produtos
CREATE TABLE IF NOT EXISTS product_variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    price_modifier REAL DEFAULT 0,
    stock INTEGER DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Tabela de conversas
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    session_id TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Tabela de mensagens
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    sender TEXT NOT NULL,
    content TEXT NOT NULL,
    message_type TEXT DEFAULT 'text',
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

-- Tabela de itens do carrinho
CREATE TABLE IF NOT EXISTS cart_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    session_id TEXT,
    product_id INTEGER NOT NULL,
    variant_id INTEGER,
    quantity INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (variant_id) REFERENCES product_variants(id)
);

-- Tabela de pedidos
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    subtotal REAL NOT NULL,
    shipping REAL DEFAULT 0,
    discount REAL DEFAULT 0,
    total REAL NOT NULL,
    payment_method TEXT,
    payment_status TEXT DEFAULT 'pending',
    shipping_address TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Tabela de itens do pedido
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    variant_id INTEGER,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Tabela de logs de pedidos
CREATE TABLE IF NOT EXISTS order_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

-- Tabela de tokens de login
CREATE TABLE IF NOT EXISTS login_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    token TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Tabela de cupons
CREATE TABLE IF NOT EXISTS coupons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    discount_type TEXT NOT NULL,
    discount_value REAL NOT NULL,
    min_value REAL DEFAULT 0,
    max_uses INTEGER,
    used_count INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de logs do sistema
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    message TEXT NOT NULL,
    data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de configurações
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de pedidos pendentes do chat (para persistir entre reconexões)
CREATE TABLE IF NOT EXISTS chat_pending_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER UNIQUE,
    customer_id INTEGER,
    items_json TEXT NOT NULL,
    total REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Criar índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_active ON products(active);
CREATE INDEX IF NOT EXISTS idx_conversations_customer ON conversations(customer_id);
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_cart_customer ON cart_items(customer_id);
CREATE INDEX IF NOT EXISTS idx_cart_session ON cart_items(session_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);

-- Inserir admin padrão (senha: admin123)
-- Hash SHA256 de 'admin123'
INSERT OR IGNORE INTO users (username, password, email, is_admin) 
VALUES ('admin', 'c7ad44cbad762a5da0a452f9e854fdc1e0e7a52a38015f23f3eab1d80b931dd4', 'admin@burgerhouse.com.br', 1);

-- Categorias para Hamburgueria
INSERT OR IGNORE INTO categories (id, name, description, active) VALUES 
(1, 'Hambúrgueres', 'Hambúrgueres artesanais com blend exclusivo', 1),
(2, 'Combos', 'Combos completos com hambúrguer, batata e bebida', 1),
(3, 'Acompanhamentos', 'Batatas fritas, onion rings e outros acompanhamentos', 1),
(4, 'Bebidas', 'Refrigerantes, sucos e outras bebidas', 1),
(5, 'Sobremesas', 'Milkshakes, brownies e sobremesas especiais', 1);

-- Produtos de Hamburgueria Artesanal
INSERT OR IGNORE INTO products (id, name, description, price, category_id, stock, active, image_url) VALUES 
-- Hambúrgueres
(1, 'Classic Burger', 'Hambúrguer artesanal 180g, queijo cheddar, alface, tomate, cebola e molho especial', 29.90, 1, 100, 1, 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400'),
(2, 'Cheese Bacon Burger', 'Hambúrguer 180g, queijo cheddar duplo, bacon crocante e molho barbecue', 34.90, 1, 100, 1, 'https://images.unsplash.com/photo-1553979459-d2229ba7433b?w=400'),
(3, 'Smash Burger Duplo', 'Dois hambúrgueres smash 90g, queijo americano, cebola caramelizada', 32.90, 1, 100, 1, 'https://images.unsplash.com/photo-1594212699903-ec8a3eca50f5?w=400'),
(4, 'BBQ Burger', 'Hambúrguer 180g, queijo provolone, onion rings, molho BBQ defumado', 36.90, 1, 100, 1, 'https://images.unsplash.com/photo-1572802419224-296b0aeee0d9?w=400'),
(5, 'Veggie Burger', 'Hambúrguer vegetariano de grão-de-bico, queijo, alface, tomate e maionese de ervas', 28.90, 1, 80, 1, 'https://images.unsplash.com/photo-1520072959219-c595dc870360?w=400'),
(6, 'Double Burger', 'Dois hambúrgueres 150g, queijo cheddar triplo, bacon e molho especial', 42.90, 1, 100, 1, 'https://images.unsplash.com/photo-1551782450-17144efb9c50?w=400'),

-- Combos
(7, 'Combo Classic', 'Classic Burger + Batata Frita média + Refrigerante 350ml', 44.90, 2, 100, 1, 'https://images.unsplash.com/photo-1610614819513-58e34989848b?w=400'),
(8, 'Combo Cheese Bacon', 'Cheese Bacon Burger + Batata Frita grande + Refrigerante 500ml', 52.90, 2, 100, 1, 'https://images.unsplash.com/photo-1586816001966-79b736744398?w=400'),
(9, 'Combo Family', '2 Classic Burgers + 2 Cheese Bacon + Batata grande + 4 Refrigerantes', 139.90, 2, 50, 1, 'https://images.unsplash.com/photo-1550547660-d9450f859349?w=400'),
(10, 'Combo Kids', 'Mini Burger + Batata pequena + Suco de laranja + Brinde', 29.90, 2, 80, 1, 'https://images.unsplash.com/photo-1596956470007-2bf6095e7e16?w=400'),

-- Acompanhamentos
(11, 'Batata Frita Pequena', 'Porção de batata frita crocante - 150g', 12.90, 3, 200, 1, 'https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=400'),
(12, 'Batata Frita Média', 'Porção de batata frita crocante - 250g', 18.90, 3, 200, 1, 'https://images.unsplash.com/photo-1630384060421-cb20d0e0649d?w=400'),
(13, 'Batata Frita Grande', 'Porção de batata frita crocante - 400g', 24.90, 3, 200, 1, 'https://images.unsplash.com/photo-1529589510304-b7e994a92f60?w=400'),
(14, 'Onion Rings', 'Anéis de cebola empanados e fritos - 200g', 16.90, 3, 150, 1, 'https://images.unsplash.com/photo-1639024471283-03518883512d?w=400'),
(15, 'Batata com Cheddar e Bacon', 'Batata frita com cheddar cremoso e bacon crocante', 28.90, 3, 100, 1, 'https://images.unsplash.com/photo-1585109649139-366815a0d713?w=400'),

-- Bebidas
(16, 'Coca-Cola 350ml', 'Refrigerante Coca-Cola lata 350ml', 6.90, 4, 300, 1, 'https://images.unsplash.com/photo-1554866585-cd94860890b7?w=400'),
(17, 'Coca-Cola 500ml', 'Refrigerante Coca-Cola garrafa 500ml', 8.90, 4, 300, 1, 'https://images.unsplash.com/photo-1629203851122-3726ecdf080e?w=400'),
(18, 'Guaraná Antarctica 350ml', 'Refrigerante Guaraná Antarctica lata 350ml', 5.90, 4, 300, 1, 'https://images.unsplash.com/photo-1625772299848-391b6a87d7b3?w=400'),
(19, 'Suco de Laranja Natural', 'Suco de laranja natural - 300ml', 9.90, 4, 100, 1, 'https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=400'),
(20, 'Água Mineral 500ml', 'Água mineral sem gás 500ml', 4.90, 4, 300, 1, 'https://images.unsplash.com/photo-1560023907-5f339617ea30?w=400'),

-- Sobremesas
(21, 'Milkshake Chocolate', 'Milkshake cremoso de chocolate - 400ml', 18.90, 5, 80, 1, 'https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=400'),
(22, 'Milkshake Morango', 'Milkshake cremoso de morango - 400ml', 18.90, 5, 80, 1, 'https://images.unsplash.com/photo-1579954115545-a95591f28bfc?w=400'),
(23, 'Milkshake Ovomaltine', 'Milkshake cremoso de ovomaltine - 400ml', 19.90, 5, 80, 1, 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400'),
(24, 'Brownie com Sorvete', 'Brownie de chocolate com sorvete de creme e calda', 16.90, 5, 60, 1, 'https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=400'),
(25, 'Petit Gateau', 'Bolo de chocolate com centro cremoso e sorvete', 21.90, 5, 50, 1, 'https://images.unsplash.com/photo-1624353365286-3f8d62daad51?w=400');
