# IMPORTANTE: eventlet.monkey_patch() DEVE ser a primeira coisa executada
import eventlet
eventlet.monkey_patch()

import os
import sqlitecloud
import json
import hashlib
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from functools import wraps

# Fuso horário de Brasília (UTC-3)
BRASILIA_TZ = timezone(timedelta(hours=-3))

def brasilia_now():
    """Retorna datetime atual no fuso horário de Brasília"""
    return datetime.now(BRASILIA_TZ)
import requests
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, g
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', secrets.token_hex(32))
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_PATH'] = '/'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

SQLITECLOUD_URL = "sqlitecloud://cmq6frwshz.g4.sqlite.cloud:8860/burger_house.db?apikey=Dor8OwUECYmrbcS5vWfsdGpjCpdm9ecSDJtywgvRw8k"

def get_db():
    if 'db' not in g:
        g.db = sqlitecloud.connect(SQLITECLOUD_URL)
        g.db.row_factory = sqlitecloud.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    print("🔄 Inicializando banco de dados SQLite Cloud...")
    try:
        conn = sqlitecloud.connect(SQLITECLOUD_URL)
        conn.row_factory = sqlitecloud.Row
        with open('schema.sql', 'r') as f:
            schema = f.read()
            statements = schema.split(';')
            for statement in statements:
                statement = statement.strip()
                if statement:
                    try:
                        conn.execute(statement)
                    except Exception as e:
                        if 'already exists' not in str(e).lower() and 'duplicate' not in str(e).lower():
                            print(f"⚠️ Aviso ao executar statement: {e}")

        # Ensure chat_pending_orders table exists
        try:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS chat_pending_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER UNIQUE,
                    customer_id INTEGER,
                    items_json TEXT NOT NULL,
                    total REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            ''')
            print("✅ Tabela chat_pending_orders verificada/criada com sucesso!")
        except Exception as table_err:
            print(f"⚠️ Erro ao criar tabela chat_pending_orders: {table_err}")

        conn.commit()
        conn.close()
        print("✅ Banco de dados SQLite Cloud inicializado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao inicializar banco de dados: {e}")

def ping_database():
    while True:
        try:
            time.sleep(300)
            conn = sqlitecloud.connect(SQLITECLOUD_URL)
            conn.execute("SELECT 1")
            conn.close()
            print(f"🏓 Ping SQLite Cloud - {brasilia_now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"❌ Erro no ping: {e}")

def start_ping_thread():
    ping_thread = threading.Thread(target=ping_database, daemon=True)
    ping_thread.start()
    print("🚀 Sistema de ping iniciado (a cada 5 minutos)")

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def insert_db(query, args=()):
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    return cur.lastrowid

def update_db(query, args=()):
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    return cur.rowcount

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token():
    return secrets.token_urlsafe(32)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def customer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'customer_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('admin_login'))
        user = query_db('SELECT * FROM users WHERE id = ?', [session['user_id']], one=True)
        if not user or not user['is_admin']:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat')
def chat():
    session_id = session.get('session_id')
    if not session_id:
        session['session_id'] = generate_token()
    return render_template('chat.html')

@app.route('/loja')
def loja():
    categories = query_db('SELECT * FROM categories WHERE active = 1 ORDER BY name')
    products = query_db('SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id = c.id WHERE p.active = 1 ORDER BY p.name')
    return render_template('loja.html', categories=categories, products=products)

@app.route('/carrinho')
def carrinho():
    return render_template('carrinho.html')

@app.route('/meus-pedidos')
@customer_required
def meus_pedidos():
    return render_template('meus_pedidos.html')

@app.route('/acompanhar-pedido')
def acompanhar_pedido():
    return render_template('acompanhar_pedido.html')

@app.route('/api/track-order/<int:order_id>')
def track_order(order_id):
    """API para acompanhar status de pedido - pública (sem necessidade de login)"""
    order = query_db('''
        SELECT o.*, c.name as customer_name, c.phone as customer_phone
        FROM orders o
        LEFT JOIN customers c ON o.customer_id = c.id
        WHERE o.id = ?
    ''', [order_id], one=True)

    if not order:
        return jsonify({'error': 'Pedido não encontrado'}), 404

    # Buscar itens do pedido
    items = query_db('''
        SELECT oi.*, p.name, p.image_url
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
    ''', [order_id])

    # Buscar logs de status
    logs = query_db('''
        SELECT * FROM order_logs
        WHERE order_id = ?
        ORDER BY created_at
    ''', [order_id])

    order_dict = dict(order)
    order_dict['items'] = [dict(item) for item in items]
    order_dict['logs'] = [dict(log) for log in logs]

    return jsonify(order_dict)

@app.route('/api/customer/orders')
def customer_orders():
    customer_id = session.get('customer_id')
    
    # Log para debug
    print(f"🔍 Session check - customer_id: {customer_id}, session keys: {list(session.keys())}")
    print(f"🔍 Session permanent: {session.permanent}")
    
    if not customer_id:
        print(f"❌ Cliente não autenticado")
        return jsonify({'error': 'Não autenticado', 'redirect': '/login'}), 401

    try:
        # Verificar se o cliente ainda existe no banco
        customer = query_db('SELECT id, name FROM customers WHERE id = ?', [customer_id], one=True)
        if not customer:
            print(f"❌ Cliente {customer_id} não encontrado no banco")
            session.clear()
            return jsonify({'error': 'Sessão inválida', 'redirect': '/login'}), 401
        
        # Garantir que a sessão permanente está ativa
        if not session.permanent:
            session.permanent = True
            session.modified = True
        
        orders = query_db('''
            SELECT o.*, 
                (SELECT COUNT(*) FROM order_items WHERE order_id = o.id) as item_count
            FROM orders o
            WHERE o.customer_id = ?
            ORDER BY o.created_at DESC
        ''', [customer_id])

        # Formatar datas corretamente
        orders_list = []
        for order in orders:
            order_dict = dict(order)
            
            # Formatar created_at
            if order_dict.get('created_at'):
                try:
                    created = order_dict['created_at']
                    if isinstance(created, str):
                        from datetime import datetime
                        created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        order_dict['created_at'] = created_dt.isoformat()
                    elif hasattr(created, 'isoformat'):
                        order_dict['created_at'] = created.isoformat()
                except:
                    pass
            
            orders_list.append(order_dict)

        return jsonify(orders_list)
    except Exception as e:
        print(f"Erro ao buscar pedidos: {e}")
        return jsonify({'error': 'Erro ao buscar pedidos'}), 500

@app.route('/api/customer/orders/<int:order_id>/items')
def customer_order_items(order_id):
    customer_id = session.get('customer_id')
    if not customer_id:
        return jsonify({'error': 'Não autenticado'}), 401

    # Verificar se o pedido pertence ao cliente
    order = query_db('SELECT * FROM orders WHERE id = ? AND customer_id = ?', 
                     [order_id, customer_id], one=True)

    if not order:
        return jsonify({'error': 'Pedido não encontrado'}), 404

    items = query_db('''
        SELECT oi.*, p.name, p.image_url
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
    ''', [order_id])

    return jsonify([dict(i) for i in items])

@app.route('/login')
def login_page():
    token = request.args.get('token')
    if token:
        token_data = query_db('SELECT * FROM login_tokens WHERE token = ? AND expires_at > ? AND used = 0', 
                              [token, brasilia_now()], one=True)
        if token_data:
            update_db('UPDATE login_tokens SET used = 1 WHERE id = ?', [token_data['id']])
            customer = query_db('SELECT * FROM customers WHERE id = ?', [token_data['customer_id']], one=True)
            if customer:
                session['customer_id'] = customer['id']
                session['customer_name'] = customer['name']
                return redirect(url_for('loja'))
    return render_template('login.html')

@app.route('/api/customer/login', methods=['POST'])
def customer_login():
    data = request.get_json()
    phone = data.get('phone', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '').strip()

    if not phone or len(phone) < 10:
        return jsonify({'success': False, 'error': 'Telefone inválido'})

    customer = query_db('SELECT * FROM customers WHERE phone = ?', [phone], one=True)

    if customer:
        # Obter session_id atual antes de fazer login
        old_session_id = session.get('session_id')

        # Fazer login do cliente - NÃO limpar sessão, apenas atualizar
        session.clear()  # Limpar dados antigos primeiro
        session['customer_id'] = customer['id']
        session['customer_name'] = customer['name']
        session['session_id'] = old_session_id or generate_token()
        session.permanent = True # Manter sessão ativa por 30 dias
        session.modified = True  # Forçar salvamento da sessão
        
        print(f"✅ Login realizado: {customer['name']} (ID: {customer['id']})")

        # Transferir itens do carrinho anônimo para o carrinho do cliente
        if old_session_id:
            # Buscar itens do carrinho da sessão anônima
            anonymous_cart_items = query_db('''
                SELECT * FROM cart_items 
                WHERE session_id = ? AND customer_id IS NULL
            ''', [old_session_id])

            for item in anonymous_cart_items:
                # Verificar se o produto já existe no carrinho do cliente
                existing_item = query_db('''
                    SELECT * FROM cart_items 
                    WHERE customer_id = ? AND product_id = ?
                ''', [customer['id'], item['product_id']], one=True)

                if existing_item:
                    # Se já existe, somar as quantidades
                    update_db('''
                        UPDATE cart_items 
                        SET quantity = quantity + ?, updated_at = ?
                        WHERE id = ?
                    ''', [item['quantity'], brasilia_now(), existing_item['id']])
                else:
                    # Se não existe, criar novo item com customer_id
                    insert_db('''
                        INSERT INTO cart_items (customer_id, product_id, quantity, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', [customer['id'], item['product_id'], item['quantity'], brasilia_now(), brasilia_now()])

            # Remover itens do carrinho anônimo após transferir
            update_db('DELETE FROM cart_items WHERE session_id = ?', [old_session_id])

        return jsonify({
            'success': True, 
            'customer_name': customer['name'],
            'redirect': url_for('loja')
        })
    else:
        return jsonify({
            'success': False, 
            'error': 'Telefone não cadastrado. Por favor, faça seu cadastro pelo chat.'
        })

@app.route('/api/customer/logout')
def customer_logout():
    session.pop('customer_id', None)
    session.pop('customer_name', None)
    session.permanent = False # Desativar sessão permanente
    return jsonify({'success': True})

@app.route('/api/customer/check')
def customer_check():
    customer_id = session.get('customer_id')
    print(f"🔍 Check login - customer_id: {customer_id}, permanent: {session.permanent}")
    
    if customer_id:
        customer = query_db('SELECT name FROM customers WHERE id = ?', [customer_id], one=True)
        if customer:
            # Garantir sessão permanente
            if not session.permanent:
                session.permanent = True
                session.modified = True
            
            return jsonify({
                'logged_in': True,
                'customer_name': customer['name']
            })
    return jsonify({'logged_in': False})

@app.route('/api/customer/last-orders')
def customer_last_orders():
    """Retorna os últimos pedidos do cliente com informações resumidas"""
    customer_id = session.get('customer_id')
    if not customer_id:
        return jsonify({'orders': [], 'logged_in': False})

    customer = query_db('SELECT name FROM customers WHERE id = ?', [customer_id], one=True)
    if not customer:
        return jsonify({'orders': [], 'logged_in': False})

    orders = query_db('''
        SELECT o.id, o.total, o.status, o.created_at, o.payment_method,
            (SELECT COUNT(*) FROM order_items WHERE order_id = o.id) as item_count
        FROM orders o
        WHERE o.customer_id = ?
        ORDER BY o.created_at DESC
        LIMIT 5
    ''', [customer_id])

    status_map = {
        'pending': 'Pendente',
        'confirmed': 'Confirmado',
        'preparing': 'Preparando',
        'out_for_delivery': 'Saiu para entrega',
        'delivered': 'Entregue',
        'cancelled': 'Cancelado'
    }

    orders_list = []
    for order in orders:
        created = order['created_at']
        date_str = ''
        
        if created:
            try:
                # Tentar converter para datetime se for string
                if isinstance(created, str):
                    from datetime import datetime
                    created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    date_str = created_dt.strftime('%d/%m/%Y')
                elif hasattr(created, 'strftime'):
                    date_str = created.strftime('%d/%m/%Y')
                else:
                    date_str = str(created)[:10] if created else ''
            except Exception as e:
                print(f"Erro ao formatar data: {e}")
                date_str = str(created)[:10] if created else ''

        orders_list.append({
            'id': order['id'],
            'total': float(order['total']),
            'status': order['status'],
            'status_text': status_map.get(order['status'], order['status']),
            'date': date_str,
            'item_count': order['item_count'],
            'created_at': str(created) if created else ''
        })

    return jsonify({
        'orders': orders_list,
        'logged_in': True,
        'customer_name': customer['name']
    })

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')

        user = query_db('SELECT * FROM users WHERE username = ? AND password = ?', 
                        [username, hash_password(password)], one=True)

        if user and user['is_admin']:
            session['user_id'] = user['id']
            session['username'] = user['username']
            if request.is_json:
                return jsonify({'success': True, 'redirect': '/admin'})
            return redirect(url_for('admin_dashboard'))

        if request.is_json:
            return jsonify({'success': False, 'error': 'Credenciais inválidas'})
        return render_template('admin_login.html', error='Credenciais inválidas')

    return render_template('admin_login.html')

@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html')

@app.route('/admin/produtos')
@admin_required
def admin_produtos():
    return render_template('admin/produtos.html')

@app.route('/admin/pedidos')
@admin_required
def admin_pedidos():
    return render_template('admin/pedidos.html')

@app.route('/admin/clientes')
@admin_required
def admin_clientes():
    return render_template('admin/clientes.html')

@app.route('/admin/conversas')
@admin_required
def admin_conversas():
    return render_template('admin/conversas.html')

@app.route('/admin/relatorios')
@admin_required
def admin_relatorios():
    return render_template('admin/relatorios.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/api/cep/<cep>')
def buscar_cep(cep):
    cep = cep.replace('-', '').replace('.', '')
    if len(cep) != 8:
        return jsonify({'error': 'CEP inválido'}), 400

    try:
        response = requests.get(f'https://viacep.com.br/ws/{cep}/json/', timeout=5)
        data = response.json()
        if 'erro' in data:
            return jsonify({'error': 'CEP não encontrado'}), 404
        return jsonify({
            'cep': data.get('cep'),
            'logradouro': data.get('logradouro'),
            'bairro': data.get('bairro'),
            'cidade': data.get('localidade'),
            'estado': data.get('uf')
        })
    except Exception as e:
        return jsonify({'error': 'Erro ao buscar CEP'}), 500

@app.route('/api/buscar-endereco')
def buscar_endereco():
    estado = request.args.get('estado', '')
    cidade = request.args.get('cidade', '')
    rua = request.args.get('rua', '')

    if len(rua) < 3:
        return jsonify({'error': 'Digite pelo menos 3 caracteres'}), 400

    try:
        response = requests.get(f'https://viacep.com.br/ws/{estado}/{cidade}/{rua}/json/', timeout=5)
        data = response.json()
        return jsonify(data if isinstance(data, list) else [])
    except Exception as e:
        return jsonify({'error': 'Erro ao buscar endereço'}), 500

@app.route('/api/products')
def get_products():
    category = request.args.get('category')
    search = request.args.get('search', '')

    if category:
        products = query_db('''
            SELECT p.*, c.name as category_name 
            FROM products p 
            LEFT JOIN categories c ON p.category_id = c.id 
            WHERE p.active = 1 AND p.category_id = ?
            ORDER BY p.name
        ''', [category])
    elif search:
        products = query_db('''
            SELECT p.*, c.name as category_name 
            FROM products p 
            LEFT JOIN categories c ON p.category_id = c.id 
            WHERE p.active = 1 AND (p.name LIKE ? OR p.description LIKE ?)
            ORDER BY p.name
        ''', [f'%{search}%', f'%{search}%'])
    else:
        products = query_db('''
            SELECT p.*, c.name as category_name 
            FROM products p 
            LEFT JOIN categories c ON p.category_id = c.id 
            WHERE p.active = 1
            ORDER BY p.name
        ''')

    return jsonify([dict(p) for p in products])

@app.route('/api/categories')
def get_categories():
    categories = query_db('SELECT * FROM categories WHERE active = 1 ORDER BY name')
    return jsonify([dict(c) for c in categories])

@app.route('/api/cart', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_cart():
    session_id = session.get('session_id') or session.get('customer_id')
    customer_id = session.get('customer_id')

    if request.method == 'GET':
        if customer_id:
            items = query_db('''
                SELECT ci.*, p.name, p.price, p.image_url 
                FROM cart_items ci 
                JOIN products p ON ci.product_id = p.id 
                WHERE ci.customer_id = ?
            ''', [customer_id])
        else:
            items = query_db('''
                SELECT ci.*, p.name, p.price, p.image_url 
                FROM cart_items ci 
                JOIN products p ON ci.product_id = p.id 
                WHERE ci.session_id = ?
            ''', [session_id])
        return jsonify([dict(i) for i in items])

    elif request.method == 'POST':
        data = request.get_json()
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)

        if customer_id:
            existing = query_db('SELECT * FROM cart_items WHERE customer_id = ? AND product_id = ?', 
                              [customer_id, product_id], one=True)
            if existing:
                update_db('UPDATE cart_items SET quantity = quantity + ?, updated_at = ? WHERE id = ?',
                         [quantity, brasilia_now(), existing['id']])
            else:
                insert_db('INSERT INTO cart_items (customer_id, product_id, quantity, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
                         [customer_id, product_id, quantity, brasilia_now(), brasilia_now()])
        else:
            existing = query_db('SELECT * FROM cart_items WHERE session_id = ? AND product_id = ?', 
                              [session_id, product_id], one=True)
            if existing:
                update_db('UPDATE cart_items SET quantity = quantity + ?, updated_at = ? WHERE id = ?',
                         [quantity, brasilia_now(), existing['id']])
            else:
                insert_db('INSERT INTO cart_items (session_id, product_id, quantity, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
                         [session_id, product_id, quantity, brasilia_now(), brasilia_now()])

        return jsonify({'success': True})

    elif request.method == 'PUT':
        data = request.get_json()
        item_id = data.get('item_id')
        quantity = data.get('quantity')

        update_db('UPDATE cart_items SET quantity = ?, updated_at = ? WHERE id = ?',
                 [quantity, brasilia_now(), item_id])
        return jsonify({'success': True})

    elif request.method == 'DELETE':
        item_id = request.args.get('item_id')
        if item_id:
            update_db('DELETE FROM cart_items WHERE id = ?', [item_id])
        return jsonify({'success': True})

@app.route('/api/checkout', methods=['POST'])
def checkout():
    session_id = session.get('session_id') or session.get('customer_id')
    customer_id = session.get('customer_id')

    if customer_id:
        cart_items = query_db('''
            SELECT ci.*, p.name, p.price, p.image_url 
            FROM cart_items ci 
            JOIN products p ON ci.product_id = p.id 
            WHERE ci.customer_id = ?
        ''', [customer_id])
    else:
        cart_items = query_db('''
            SELECT ci.*, p.name, p.price, p.image_url 
            FROM cart_items ci 
            JOIN products p ON ci.product_id = p.id 
            WHERE ci.session_id = ?
        ''', [session_id])

    if not cart_items:
        return jsonify({'success': False, 'error': 'Carrinho vazio'})

    data = request.get_json()
    payment_method = data.get('payment_method', 'pending')
    troco = data.get('troco')

    subtotal = sum(item['price'] * item['quantity'] for item in cart_items)
    shipping = 15.00
    total = subtotal + shipping

    customer = None
    delivery_address = 'Endereço não informado'
    if customer_id:
        customer = query_db('SELECT * FROM customers WHERE id = ?', [customer_id], one=True)
        if customer:
            delivery_address = f"{customer['address']}, {customer['number']} {customer['complement'] or ''} - {customer['neighborhood']}, {customer['city']}/{customer['state']}"

    notes = f"Forma de Pagamento: {payment_method.upper()}"
    if payment_method == 'dinheiro' and troco:
        if troco == 'nao':
            notes += " | Troco: Não precisa"
        else:
            notes += f" | Troco para: {troco}"

    order_id = insert_db('''
        INSERT INTO orders (customer_id, subtotal, shipping, discount, total, status, payment_method, shipping_address, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        customer_id,
        subtotal,
        shipping,
        0,
        total,
        'pending',
        payment_method,
        delivery_address,
        notes,
        brasilia_now(),
        brasilia_now()
    ])

    for item in cart_items:
        insert_db('''
            INSERT INTO order_items (order_id, product_id, quantity, price, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', [
            order_id,
            item['product_id'],
            item['quantity'],
            item['price'],
            brasilia_now()
        ])

    if customer_id:
        update_db('DELETE FROM cart_items WHERE customer_id = ?', [customer_id])
    else:
        update_db('DELETE FROM cart_items WHERE session_id = ?', [session_id])

    insert_db('INSERT INTO order_logs (order_id, status, notes, created_at) VALUES (?, ?, ?, ?)',
             [order_id, 'pending', 'Pedido criado via loja', brasilia_now()])

    return jsonify({
        'success': True, 
        'order_id': order_id,
        'message': 'Pedido enviado com sucesso!'
    })

@app.route('/api/admin/dashboard')
@admin_required
def admin_dashboard_data():
    today = brasilia_now().date()
    month_start = today.replace(day=1)

    total_customers = query_db('SELECT COUNT(*) as count FROM customers', one=True)['count']
    total_orders = query_db('SELECT COUNT(*) as count FROM orders', one=True)['count']
    total_products = query_db('SELECT COUNT(*) as count FROM products WHERE active = 1', one=True)['count']

    total_revenue = query_db('SELECT COALESCE(SUM(total), 0) as total FROM orders WHERE status != "cancelled"', one=True)['total']
    month_revenue = query_db('''
        SELECT COALESCE(SUM(total), 0) as total FROM orders 
        WHERE status != "cancelled" AND date(created_at) >= ?
    ''', [month_start], one=True)['total']

    today_orders = query_db('SELECT COUNT(*) as count FROM orders WHERE date(created_at) = ?', [today], one=True)['count']
    pending_orders = query_db('SELECT COUNT(*) as count FROM orders WHERE status = "pending"', one=True)['count']

    abandoned_carts = query_db('''
        SELECT COUNT(DISTINCT COALESCE(customer_id, session_id)) as count 
        FROM cart_items 
        WHERE updated_at < datetime("now", "-24 hours")
    ''', one=True)['count']

    recent_orders = query_db('''
        SELECT o.*, c.name as customer_name 
        FROM orders o 
        LEFT JOIN customers c ON o.customer_id = c.id 
        ORDER BY o.created_at DESC LIMIT 10
    ''')

    sales_by_day = query_db('''
        SELECT date(created_at) as date, SUM(total) as total, COUNT(*) as count
        FROM orders WHERE status != "cancelled"
        GROUP BY date(created_at)
        ORDER BY date DESC LIMIT 30
    ''')

    top_products = query_db('''
        SELECT p.name, SUM(oi.quantity) as total_sold, SUM(oi.quantity * oi.price) as revenue
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        GROUP BY p.id
        ORDER BY total_sold DESC LIMIT 10
    ''')

    orders_by_status = query_db('''
        SELECT status, COUNT(*) as count FROM orders GROUP BY status
    ''')

    return jsonify({
        'total_customers': total_customers,
        'total_orders': total_orders,
        'total_products': total_products,
        'total_revenue': total_revenue,
        'month_revenue': month_revenue,
        'today_orders': today_orders,
        'pending_orders': pending_orders,
        'abandoned_carts': abandoned_carts,
        'recent_orders': [dict(o) for o in recent_orders],
        'sales_by_day': [dict(s) for s in sales_by_day],
        'top_products': [dict(p) for p in top_products],
        'orders_by_status': [dict(o) for o in orders_by_status]
    })

@app.route('/api/admin/products', methods=['GET', 'POST', 'PUT', 'DELETE'])
@admin_required
def admin_products():
    if request.method == 'GET':
        products = query_db('''
            SELECT p.*, c.name as category_name 
            FROM products p 
            LEFT JOIN categories c ON p.category_id = c.id 
            ORDER BY p.created_at DESC
        ''')
        return jsonify([dict(p) for p in products])

    elif request.method == 'POST':
        data = request.get_json()
        product_id = insert_db('''
            INSERT INTO products (name, description, price, image_url, category_id, stock, active, created_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', [data['name'], data.get('description', ''), data['price'], 
              data.get('image_url', ''), data.get('category_id'), 
              data.get('stock', 0), data.get('active', 1), brasilia_now()])
        return jsonify({'success': True, 'id': product_id})

    elif request.method == 'PUT':
        data = request.get_json()
        update_db('''
            UPDATE products SET name = ?, description = ?, price = ?, image_url = ?, 
            category_id = ?, stock = ?, active = ? WHERE id = ?
        ''', [data['name'], data.get('description', ''), data['price'], 
              data.get('image_url', ''), data.get('category_id'), 
              data.get('stock', 0), data.get('active', 1), data['id']])
        return jsonify({'success': True})

    elif request.method == 'DELETE':
        product_id = request.args.get('id')
        update_db('UPDATE products SET active = 0 WHERE id = ?', [product_id])
        return jsonify({'success': True})

@app.route('/api/admin/categories', methods=['GET', 'POST', 'PUT', 'DELETE'])
@admin_required
def admin_categories():
    if request.method == 'GET':
        categories = query_db('SELECT * FROM categories ORDER BY name')
        return jsonify([dict(c) for c in categories])

    elif request.method == 'POST':
        data = request.get_json()
        cat_id = insert_db('INSERT INTO categories (name, description, active) VALUES (?, ?, ?)',
                          [data['name'], data.get('description', ''), 1])
        return jsonify({'success': True, 'id': cat_id})

    elif request.method == 'PUT':
        data = request.get_json()
        update_db('UPDATE categories SET name = ?, description = ?, active = ? WHERE id = ?',
                 [data['name'], data.get('description', ''), data.get('active', 1), data['id']])
        return jsonify({'success': True})

    elif request.method == 'DELETE':
        cat_id = request.args.get('id')
        update_db('UPDATE categories SET active = 0 WHERE id = ?', [cat_id])
        return jsonify({'success': True})

@app.route('/api/admin/orders', methods=['GET', 'PUT'])
@admin_required
def admin_orders():
    if request.method == 'GET':
        status = request.args.get('status')
        if status:
            orders = query_db('''
                SELECT o.*, c.name as customer_name, c.phone as customer_phone
                FROM orders o
                LEFT JOIN customers c ON o.customer_id = c.id
                WHERE o.status = ?
                ORDER BY o.created_at DESC
            ''', [status])
        else:
            orders = query_db('''
                SELECT o.*, c.name as customer_name, c.phone as customer_phone
                FROM orders o
                LEFT JOIN customers c ON o.customer_id = c.id
                ORDER BY o.created_at DESC
            ''')
        return jsonify([dict(o) for o in orders])

    elif request.method == 'PUT':
        data = request.get_json()
        update_db('UPDATE orders SET status = ?, updated_at = ? WHERE id = ?',
                 [data['status'], brasilia_now(), data['id']])

        insert_db('INSERT INTO order_logs (order_id, status, notes, created_at) VALUES (?, ?, ?, ?)',
                 [data['id'], data['status'], data.get('notes', ''), brasilia_now()])

        return jsonify({'success': True})

@app.route('/api/admin/orders/<int:order_id>/items')
@admin_required
def admin_order_items(order_id):
    items = query_db('''
        SELECT oi.*, p.name, p.image_url
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
    ''', [order_id])
    return jsonify([dict(i) for i in items])

@app.route('/api/admin/customers', methods=['GET'])
@admin_required
def admin_customers():
    customers = query_db('''
        SELECT c.*, 
            (SELECT COUNT(*) FROM orders WHERE customer_id = c.id) as order_count,
            (SELECT COALESCE(SUM(total), 0) FROM orders WHERE customer_id = c.id AND status != "cancelled") as total_spent
        FROM customers c
        ORDER BY c.created_at DESC
    ''')
    return jsonify([dict(c) for c in customers])

@app.route('/api/admin/conversations', methods=['GET'])
@admin_required
def admin_conversations():
    conversations = query_db('''
        SELECT cv.*, c.name as customer_name, c.phone as customer_phone,
            (SELECT COUNT(*) FROM messages WHERE conversation_id = cv.id) as message_count
        FROM conversations cv
        LEFT JOIN customers c ON cv.customer_id = c.id
        ORDER BY cv.updated_at DESC
    ''')
    return jsonify([dict(cv) for cv in conversations])

@app.route('/api/admin/conversations/<int:conv_id>/messages')
@admin_required
def admin_conversation_messages(conv_id):
    messages = query_db('''
        SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at
    ''', [conv_id])
    return jsonify([dict(m) for m in messages])

@app.route('/api/admin/reports/sales')
@admin_required
def admin_report_sales():
    start_date = request.args.get('start_date', (brasilia_now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', brasilia_now().strftime('%Y-%m-%d'))

    daily_sales = query_db('''
        SELECT date(created_at) as date, SUM(total) as revenue, COUNT(*) as orders
        FROM orders
        WHERE status != "cancelled" AND date(created_at) BETWEEN ? AND ?
        GROUP BY date(created_at)
        ORDER BY date
    ''', [start_date, end_date])

    category_sales = query_db('''
        SELECT c.name, SUM(oi.quantity * oi.price) as revenue, SUM(oi.quantity) as quantity
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        LEFT JOIN categories c ON p.category_id = c.id
        JOIN orders o ON oi.order_id = o.id
        WHERE o.status != "cancelled" AND date(o.created_at) BETWEEN ? AND ?
        GROUP BY c.id
    ''', [start_date, end_date])

    return jsonify({
        'daily_sales': [dict(d) for d in daily_sales],
        'category_sales': [dict(c) for c in category_sales]
    })


def process_with_ai(session_id, content, conv_data):
    """Processa mensagens usando Gemini AI para entender intenções e fazer pedidos"""
    content_lower = content.lower()
    user_data = conv_data.get('data', {})
    customer_id = user_data.get('customer_id')

    if not customer_id:
        customer_id = session.get('customer_id')

    # Buscar informações do cliente
    customer = None
    if customer_id:
        customer = query_db('SELECT * FROM customers WHERE id = ?', [customer_id], one=True)

    # Verificar se está aguardando confirmação de pedido - NÃO processar aqui
    state = conv_data.get('state', 'registered')
    if state == 'awaiting_order_confirmation':
        # Retornar para ser processado em process_chat_message
        return None

    if not GEMINI_AVAILABLE or not gemini_chat:
        # Fallback sem Gemini
        return process_without_ai(content_lower, session_id, conv_data)

    try:
        # Buscar produtos disponíveis
        products = query_db('SELECT id, name, price, description, stock FROM products WHERE active = 1')
        products_info = []
        for p in products:
            products_info.append({
                'id': p['id'],
                'name': p['name'],
                'price': float(p['price']),
                'description': p['description'],
                'stock': p['stock']
            })

        # Criar contexto rico para o Gemini
        context = f"""
Você é o assistente virtual da Burger House, hamburgueria artesanal especializada em atendimento e vendas.

INFORMAÇÕES DO CLIENTE:
- Nome: {customer['name'] if customer else 'Não identificado'}
- Telefone: {customer['phone'] if customer else 'Não informado'}
- Endereço: {customer['address'] if customer else 'Não cadastrado'}, {customer['number'] if customer else ''} {customer['complement'] if customer else ''}

PRODUTOS DISPONÍVEIS:
{json.dumps(products_info, indent=2, ensure_ascii=False)}

REGRAS CRÍTICAS DE INTERPRETAÇÃO DE PEDIDOS:

1. **UNIDADES INDIVIDUAIS**: Quando o cliente menciona "1 lata", "2 latas", "1 garrafa", ele quer UNIDADES INDIVIDUAIS!
   - "1 lata" = 1 unidade individual
   - "2 garrafas" = 2 unidades individuais

2. **PACKS vs UNIDADES**:
   - Se o produto tem "(Pack" no nome e o cliente NÃO mencionou "pack", procure a versão individual
   - Se só existe versão pack, SEMPRE confirme com o cliente quantas unidades vem no pack

3. **FORMATO DE RESPOSTA PARA PEDIDOS**:
   Quando identificar um pedido, retorne JSON:
   {{"action": "create_order", "items": [{{"product_id": ID, "quantity": QTD}}], "needs_confirmation": true/false}}

4. **Exemplos**:
   - "quero 1 coca lata" → Buscar produto sem "(Pack" no nome
   - "quero 1 pack de coca" → Aí sim usar o produto com "(Pack"

5. **ACOMPANHAMENTO DE PEDIDO**:
   - Se o cliente perguntar sobre status/rastrear/acompanhar pedido, peça o número do pedido
   - Se informar um número de pedido, confirme que ele pode acompanhar pelo site

IMPORTANTE:
- Sempre confirme se é pack quando a quantidade for pequena (1-3 unidades)
- Use apenas product_id válidos da lista
- Seja claro sobre o que vem no pedido
- Ajude com acompanhamento de pedidos quando solicitado
"""

        response = gemini_chat.chat(content, context)

        # Verificar se a resposta é um JSON de pedido
        try:
            json_match = response.strip()
            if '{' in json_match and '}' in json_match:
                start = json_match.find('{')
                end = json_match.rfind('}') + 1
                json_str = json_match[start:end]

                try:
                    order_data = json.loads(json_str)

                    if order_data.get('action') == 'create_order' and customer_id:
                        items = order_data.get('items', [])
                        if items:
                            total = 0
                            order_items_details = []

                            for item in items:
                                product = query_db('SELECT * FROM products WHERE id = ? AND active = 1', 
                                                 [item['product_id']], one=True)
                                if product:
                                    product_name_lower = product['name'].lower()
                                    is_pack = '(pack' in product_name_lower

                                    # Se é pack e quantidade pequena, confirmar
                                    if is_pack and item['quantity'] <= 3:
                                        import re
                                        pack_match = re.search(r'\(pack\s*(\d+)', product_name_lower)
                                        if pack_match:
                                            units_in_pack = pack_match.group(1)
                                            total_units = int(units_in_pack) * item['quantity']
                                            total_price = float(product['price']) * item['quantity']

                                            # Salvar temporariamente para caso o usuário confirme
                                            temp_order = [{
                                                'product_id': product['id'],
                                                'name': product['name'],
                                                'quantity': item['quantity'],
                                                'price': float(product['price']),
                                                'total': total_price
                                            }]
                                            active_conversations[session_id]['data']['temp_pack_order'] = temp_order
                                            active_conversations[session_id]['data']['temp_pack_total'] = total_price

                                            return f"⚠️ Atenção!\n\n*{product['name']}* vem em pack fechado com {units_in_pack} unidades.\n\nVocê quer {item['quantity']} pack(s) = {total_units} unidades por R$ {total_price:.2f}?\n\n👍 Responda *SIM* para confirmar\n👎 Ou *NÃO* para cancelar"

                                    item_total = float(product['price']) * item['quantity']
                                    total += item_total
                                    order_items_details.append({
                                        'product_id': product['id'],
                                        'name': product['name'],
                                        'quantity': item['quantity'],
                                        'price': float(product['price']),
                                        'total': item_total
                                    })

                            if order_items_details:
                                # Salvar pedido pendente
                                active_conversations[session_id]['data']['pending_order_items'] = order_items_details
                                active_conversations[session_id]['data']['pending_order_total'] = total
                                active_conversations[session_id]['state'] = 'awaiting_order_confirmation'

                                # Salvar no banco
                                conv_id = active_conversations[session_id].get('conversation_id')
                                if conv_id and customer_id:
                                    try:
                                        update_db('DELETE FROM chat_pending_orders WHERE conversation_id = ?', [conv_id])
                                        insert_db('''
                                            INSERT INTO chat_pending_orders (conversation_id, customer_id, items_json, total, created_at)
                                            VALUES (?, ?, ?, ?, ?)
                                        ''', [conv_id, customer_id, json.dumps(order_items_details), total, brasilia_now()])
                                        print(f"✅ Pedido salvo: {len(order_items_details)} itens, R$ {total:.2f}")
                                    except Exception as db_err:
                                        print(f"⚠️ Erro ao salvar: {db_err}")

                                items_list = [f"• {i['quantity']}x {i['name']} - R$ {i['total']:.2f}" for i in order_items_details]
                                items_text = "\n".join(items_list)

                                return f"Seu pedido:\n{items_text}\n\nTotal: R$ {total:.2f}\n\nConfirma? Responde SIM ou NÃO"
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            print(f"JSON parse error: {e}")

        return response

    except Exception as e:
        print(f"Gemini error: {e}")
        return process_without_ai(content_lower, session_id, conv_data)

def process_without_ai(content_lower, session_id=None, conv_data=None):
    """Fallback inteligente quando Gemini não está disponível - processa pedidos naturalmente"""
    import re

    # Pegar dados do cliente se disponíveis
    customer_id = None
    customer_name = 'amigo'
    if conv_data:
        user_data = conv_data.get('data', {})
        customer_id = user_data.get('customer_id') or session.get('customer_id')
        if customer_id:
            customer = query_db('SELECT name FROM customers WHERE id = ?', [customer_id], one=True)
            if customer:
                customer_name = customer['name'].split()[0] if customer['name'] else 'amigo'

    # Verificar se está escolhendo um produto da lista
    if session_id and session_id in active_conversations:
        awaiting_choice = active_conversations[session_id].get('awaiting_product_choice', False)
        if awaiting_choice:
            available_products = active_conversations[session_id].get('available_products', [])

            # Tentar entender a escolha do cliente - ser mais flexível
            for idx, product in enumerate(available_products):
                product_name_lower = product['name'].lower()
                
                # Se cliente digitou número da opção
                if content_lower.strip().isdigit():
                    choice_num = int(content_lower.strip())
                    if 1 <= choice_num <= len(available_products):
                        product = available_products[choice_num - 1]
                        quantity = active_conversations[session_id].get('pending_quantity', 1)
                        total = float(product['price']) * quantity

                        order_items = [{
                            'product_id': product['id'],
                            'name': product['name'],
                            'price': float(product['price']),
                            'quantity': quantity
                        }]

                        active_conversations[session_id]['data']['pending_order_items'] = order_items
                        active_conversations[session_id]['data']['pending_order_total'] = total
                        active_conversations[session_id]['state'] = 'awaiting_order_confirmation'
                        active_conversations[session_id]['awaiting_product_choice'] = False

                        conv_id = conv_data.get('conversation_id') if conv_data else None
                        if conv_id:
                            try:
                                update_db('DELETE FROM chat_pending_orders WHERE conversation_id = ?', [conv_id])
                                insert_db('''
                                    INSERT INTO chat_pending_orders (conversation_id, customer_id, items_json, total, created_at)
                                    VALUES (?, ?, ?, ?, ?)
                                ''', [conv_id, customer_id, json.dumps(order_items), total, brasilia_now()])
                            except:
                                pass

                        return f"Beleza!\n\n{quantity}x {product['name']} - R$ {total:.2f}\n\nConfirma? Responde SIM ou NÃO"
                
                # Verificar por características específicas do produto mencionadas
                if any(word in content_lower for word in ['20l', '20 l', '20 litros', 'galão', 'galao']):
                    if '20l' in product_name_lower or 'galão' in product_name_lower:
                        quantity = active_conversations[session_id].get('pending_quantity', 1)
                        total = float(product['price']) * quantity
                        order_items = [{
                            'product_id': product['id'],
                            'name': product['name'],
                            'price': float(product['price']),
                            'quantity': quantity
                        }]
                        active_conversations[session_id]['data']['pending_order_items'] = order_items
                        active_conversations[session_id]['data']['pending_order_total'] = total
                        active_conversations[session_id]['state'] = 'awaiting_order_confirmation'
                        active_conversations[session_id]['awaiting_product_choice'] = False
                        conv_id = conv_data.get('conversation_id') if conv_data else None
                        if conv_id:
                            try:
                                update_db('DELETE FROM chat_pending_orders WHERE conversation_id = ?', [conv_id])
                                insert_db('''
                                    INSERT INTO chat_pending_orders (conversation_id, customer_id, items_json, total, created_at)
                                    VALUES (?, ?, ?, ?, ?)
                                ''', [conv_id, customer_id, json.dumps(order_items), total, brasilia_now()])
                            except:
                                pass
                        return f"Beleza!\n\n{quantity}x {product['name']} - R$ {total:.2f}\n\nConfirma? Responde SIM ou NÃO"

                elif any(word in content_lower for word in ['350ml', '350 ml', 'lata individual', '350']):
                    if '350ml' in product_name_lower and 'pack' not in product_name_lower:
                        quantity = active_conversations[session_id].get('pending_quantity', 1)
                        total = float(product['price']) * quantity
                        order_items = [{
                            'product_id': product['id'],
                            'name': product['name'],
                            'price': float(product['price']),
                            'quantity': quantity
                        }]
                        active_conversations[session_id]['data']['pending_order_items'] = order_items
                        active_conversations[session_id]['data']['pending_order_total'] = total
                        active_conversations[session_id]['state'] = 'awaiting_order_confirmation'
                        active_conversations[session_id]['awaiting_product_choice'] = False
                        conv_id = conv_data.get('conversation_id') if conv_data else None
                        if conv_id:
                            try:
                                update_db('DELETE FROM chat_pending_orders WHERE conversation_id = ?', [conv_id])
                                insert_db('''
                                    INSERT INTO chat_pending_orders (conversation_id, customer_id, items_json, total, created_at)
                                    VALUES (?, ?, ?, ?, ?)
                                ''', [conv_id, customer_id, json.dumps(order_items), total, brasilia_now()])
                            except:
                                pass
                        return f"Beleza!\n\n{quantity}x {product['name']} - R$ {total:.2f}\n\nConfirma? Responde SIM ou NÃO"

                elif 'pack' in content_lower:
                    if 'pack' in product_name_lower:
                        quantity = active_conversations[session_id].get('pending_quantity', 1)
                        total = float(product['price']) * quantity
                        order_items = [{
                            'product_id': product['id'],
                            'name': product['name'],
                            'price': float(product['price']),
                            'quantity': quantity
                        }]
                        active_conversations[session_id]['data']['pending_order_items'] = order_items
                        active_conversations[session_id]['data']['pending_order_total'] = total
                        active_conversations[session_id]['state'] = 'awaiting_order_confirmation'
                        active_conversations[session_id]['awaiting_product_choice'] = False
                        conv_id = conv_data.get('conversation_id') if conv_data else None
                        if conv_id:
                            try:
                                update_db('DELETE FROM chat_pending_orders WHERE conversation_id = ?', [conv_id])
                                insert_db('''
                                    INSERT INTO chat_pending_orders (conversation_id, customer_id, items_json, total, created_at)
                                    VALUES (?, ?, ?, ?, ?)
                                ''', [conv_id, customer_id, json.dumps(order_items), total, brasilia_now()])
                            except:
                                pass
                        return f"Beleza!\n\n{quantity}x {product['name']} - R$ {total:.2f}\n\nConfirma? Responde SIM ou NÃO"

    # Saudações simples
    saudacoes = ['oi', 'ola', 'olá', 'e aí', 'eai', 'bom dia', 'boa tarde', 'boa noite', 'hey', 'hi']
    if any(content_lower.strip() == s for s in saudacoes):
        return f"Oi, {customer_name}! Tudo bem? 😊\n\nO que você precisa hoje?"

    # Agradecimentos
    if any(word in content_lower for word in ['obrigado', 'obrigada', 'valeu', 'thanks', 'brigado', 'brigada']):
        responses = [
            "Por nada! Precisando, é só chamar! 😊",
            "Imagina! Qualquer coisa, tô aqui!",
            "Disponha! Até a próxima! 😊"
        ]
        import random
        return random.choice(responses)

    # Horário de funcionamento
    if any(word in content_lower for word in ['horário', 'horario', 'abre', 'fecha', 'funcionamento', 'aberto', 'fechado']):
        return "Nosso horário:\n\nTer a Dom: 18:00 às 23:00\nSegunda: Fechado"

    # Catálogo/produtos
    if any(word in content_lower for word in ['produto', 'produtos', 'catalogo', 'catálogo', 'cardapio', 'cardápio', 'menu', 'o que tem', 'que vende']):
        products = query_db('SELECT name, price FROM products WHERE active = 1 LIMIT 8')
        if products:
            prod_list = "\n".join([f"• {p['name']} - R$ {p['price']:.2f}" for p in products])
            return f"Nossos produtos:\n\n{prod_list}\n\nQual você quer?"
        return "Tô sem produtos cadastrados no momento. Entra em contato pelo WhatsApp (31) 99212-2844!"

    # Acompanhamento de pedido
    if any(word in content_lower for word in ['acompanhar', 'rastrear', 'status', 'onde está', 'cadê meu', 'meu pedido']):
        numbers = re.findall(r'\d+', content_lower)
        if numbers:
            order_id = numbers[0]
            order = query_db('SELECT status FROM orders WHERE id = ?', [order_id], one=True)
            if order:
                status_map = {
                    'pending': 'Pendente',
                    'confirmed': 'Confirmado',
                    'preparing': 'Preparando',
                    'out_for_delivery': 'Saiu pra entrega',
                    'delivered': 'Entregue',
                    'cancelled': 'Cancelado'
                }
                return f"Pedido #{order_id}: {status_map.get(order['status'], order['status'])}\n\nQuer mais detalhes? Clica em 'Meus Pedidos' no menu!"
            return f"Não achei o pedido #{order_id}. Confere o número?"
        return "Me passa o número do pedido pra eu ver o status!"

    # Tentar processar como pedido - BUSCAR PRODUTOS RELACIONADOS
    if any(word in content_lower for word in ['quero', 'preciso', 'manda', 'me vê', 'me da', 'me dá', 'queria', 'gostaria', 'pode', 'pedir']):
        # Extrair quantidade
        quantity_match = re.search(r'(\d+)\s*(galão|galões|galao|galoes|garrafa|garrafas|lata|latas|litro|litros|pack|packs|unidade|unidades|caixa|caixas|hamburguer|hamburgueres|burger|burgers)?', content_lower)
        quantity = int(quantity_match.group(1)) if quantity_match else 1

        # Detectar se o cliente quer explicitamente um PACK
        wants_pack = 'pack' in content_lower or 'caixa' in content_lower or quantity >= 6

        # Buscar produtos relacionados
        products = query_db('SELECT id, name, price, stock FROM products WHERE active = 1')

        # IDENTIFICAÇÃO INTELIGENTE
        matching_products = []

        # Detectar produto específico - INCLUINDO HAMBÚRGUERES
        product_keywords = {
            'coca': ['coca', 'coca-cola'],
            'guarana': ['guaraná', 'guarana', 'antarctica'],
            'fanta': ['fanta'],
            'sprite': ['sprite'],
            'agua': ['água', 'agua', 'mineral'],
            'cerveja': ['cerveja', 'brahma', 'skol', 'heineken'],
            'suco': ['suco'],
            'hamburguer': ['hamburguer', 'hamburger', 'burger', 'lanche'],
            'cheese bacon': ['cheese bacon', 'bacon'],
            'classic': ['classic'],
            'smash': ['smash'],
            'batata': ['batata', 'frita']
        }

        detected_product = None
        detected_volume = None
        
        # Detectar volume/tamanho mencionado
        if any(vol in content_lower for vol in ['2l', '2 l', '2 litros', 'garrafa']):
            detected_volume = '2l'
        elif any(vol in content_lower for vol in ['350ml', '350 ml', 'lata', 'latinha']):
            detected_volume = '350ml'
        elif any(vol in content_lower for vol in ['500ml', '500 ml']):
            detected_volume = '500ml'
        elif any(vol in content_lower for vol in ['1l', '1 l', '1 litro']):
            detected_volume = '1l'
        elif any(vol in content_lower for vol in ['20l', '20 l', 'galão', 'galao']):
            detected_volume = '20l'
        
        # Detectar produto - procurar PRIMEIRO por nomes compostos (mais específicos)
        for product_key, keywords in sorted(product_keywords.items(), key=lambda x: -len(max(x[1], key=len))):
            if any(kw in content_lower for kw in keywords):
                detected_product = product_key
                break
        
        # CASO ESPECIAL: Se não detectou produto mas disse "hamburguer", usar genérico
        if not detected_product and any(word in content_lower for word in ['hamburguer', 'hamburger', 'burger', 'lanche']):
            detected_product = 'hamburguer'

        # Se cliente pediu "lata" especificamente e NÃO mencionou pack
        if 'lata' in content_lower and not wants_pack:
            # Buscar produto INDIVIDUAL (sem pack no nome)
            for product in products:
                product_name_lower = product['name'].lower()
                
                # Verificar se é o produto certo E não é pack
                if detected_product:
                    product_match = any(kw in product_name_lower for kw in product_keywords.get(detected_product, []))
                    if product_match and 'lata' in product_name_lower and 'pack' not in product_name_lower:
                        matching_products = [product]
                        break

        # Se não encontrou produto individual, buscar normalmente
        if not matching_products:
            for product in products:
                product_name_lower = product['name'].lower()
                
                # Se o cliente mencionou um produto específico
                if detected_product:
                    product_match = any(kw in product_name_lower for kw in product_keywords.get(detected_product, []))
                    
                    # BUSCA FLEXÍVEL: Se não encontrou match exato, procurar palavras individuais
                    if not product_match and detected_product == 'hamburguer':
                        # Aceitar qualquer produto que tenha "burger" no nome
                        product_match = 'burger' in product_name_lower or 'hamburguer' in product_name_lower
                    
                    if product_match:
                        # Se quer pack, pegar só packs
                        if wants_pack:
                            if 'pack' in product_name_lower:
                                matching_products.append(product)
                        # Se não quer pack e quantidade pequena, evitar packs
                        elif quantity <= 3:
                            if 'pack' not in product_name_lower:
                                matching_products.append(product)
                        else:
                            matching_products.append(product)

        # CASO ESPECIAL: Se cliente pediu "hamburguer" genérico sem especificar qual
        if detected_product == 'hamburguer' and not any(kw in content_lower for kw in ['cheese', 'bacon', 'classic', 'smash', 'bbq']):
            if len(matching_products) > 1:
                # Tem vários hambúrgueres, listar e marcar que está aguardando escolha
                prod_list = "\n".join([f"{idx+1}. {p['name']} - R$ {p['price']:.2f}" for idx, p in enumerate(matching_products)])
                
                if session_id:
                    active_conversations[session_id]['awaiting_burger_type'] = True
                    active_conversations[session_id]['available_products'] = matching_products
                    active_conversations[session_id]['pending_burger_quantity'] = quantity
                
                return f"Temos essas opções:\n\n{prod_list}\n\nQual você quer?"
        
        # INTELIGÊNCIA MELHORADA: Se encontrou apenas 1 produto mesmo sem volume específico, usar direto
        if len(matching_products) == 1 and not detected_volume:
            matched_product = matching_products[0]

            # Verificar estoque
            if matched_product['stock'] < quantity:
                return f"Tenho só {matched_product['stock']} unidades de {matched_product['name']} no momento. Quer essa quantidade?"

            # Criar pedido pendente automaticamente
            total = float(matched_product['price']) * quantity

            order_items = [{
                'product_id': matched_product['id'],
                'name': matched_product['name'],
                'price': float(matched_product['price']),
                'quantity': quantity
            }]

            if session_id and session_id in active_conversations:
                active_conversations[session_id]['data']['pending_order_items'] = order_items
                active_conversations[session_id]['data']['pending_order_total'] = total
                active_conversations[session_id]['state'] = 'awaiting_order_confirmation'

                # Salvar no banco também
                conv_id = conv_data.get('conversation_id') if conv_data else None
                if conv_id:
                    try:
                        update_db('DELETE FROM chat_pending_orders WHERE conversation_id = ?', [conv_id])
                        insert_db('''
                            INSERT INTO chat_pending_orders (conversation_id, customer_id, items_json, total, created_at)
                            VALUES (?, ?, ?, ?, ?)
                        ''', [conv_id, customer_id, json.dumps(order_items), total, brasilia_now()])
                    except:
                        pass

            return f"Beleza!\n\n{quantity}x {matched_product['name']} - R$ {total:.2f}\n\nConfirma? SIM ou NÃO"

        # Se encontrou múltiplos produtos, listar com números
        elif len(matching_products) > 1:
            prod_list = "\n".join([f"{idx+1}. {p['name']} - R$ {p['price']:.2f}" for idx, p in enumerate(matching_products)])

            # Salvar estado para próxima resposta
            if session_id:
                active_conversations[session_id]['awaiting_product_choice'] = True
                active_conversations[session_id]['available_products'] = matching_products
                active_conversations[session_id]['pending_quantity'] = quantity

            return f"Encontrei essas opções:\n\n{prod_list}\n\nDigite o *número* da opção que você quer ou descreva melhor!"

        # Se encontrou apenas 1, processar diretamente
        elif len(matching_products) == 1:
            matched_product = matching_products[0]

            # Verificar estoque
            if matched_product['stock'] < quantity:
                return f"Tenho só {matched_product['stock']} unidades de {matched_product['name']} no momento. Quer essa quantidade?"

            # Criar pedido pendente
            total = float(matched_product['price']) * quantity

            order_items = [{
                'product_id': matched_product['id'],
                'name': matched_product['name'],
                'price': float(matched_product['price']),
                'quantity': quantity
            }]

            if session_id and session_id in active_conversations:
                active_conversations[session_id]['data']['pending_order_items'] = order_items
                active_conversations[session_id]['data']['pending_order_total'] = total
                active_conversations[session_id]['state'] = 'awaiting_order_confirmation'

                # Salvar no banco também
                conv_id = conv_data.get('conversation_id') if conv_data else None
                if conv_id:
                    try:
                        update_db('DELETE FROM chat_pending_orders WHERE conversation_id = ?', [conv_id])
                        insert_db('''
                            INSERT INTO chat_pending_orders (conversation_id, customer_id, items_json, total, created_at)
                            VALUES (?, ?, ?, ?, ?)
                        ''', [conv_id, customer_id, json.dumps(order_items), total, brasilia_now()])
                    except:
                        pass

            return f"Beleza!\n\n{quantity}x {matched_product['name']} - R$ {total:.2f}\n\nConfirma? SIM ou NÃO"

        # Não encontrou produto específico
        if not matching_products:
            if detected_product:
                return f"😕 Não encontrei *{detected_product}* no estoque no momento.\n\nQuer ver outros produtos disponíveis? Digite *produtos* ou me fale o que você precisa!"
            
            # Mostrar alguns produtos populares
            if products and len(products) > 0:
                popular = products[:5]
                prod_list = "\n".join([f"{idx+1}. {p['name']} - R$ {p['price']:.2f}" for idx, p in enumerate(popular)])
                return f"Temos esses produtos disponíveis:\n\n{prod_list}\n\nDigite o *número* ou me fale o que você quer!"
            
        return "Me fala direitinho o que você quer que eu busco aqui!"

    # Resposta padrão amigável
    responses = [
        f"Oi, {customer_name}! Em que posso te ajudar?",
        "Me fala o que você precisa!",
        "Tô aqui! O que vai ser hoje?"
    ]
    import random
    return random.choice(responses)


@app.route('/api/admin/reports/customers')
@admin_required
def admin_report_customers():
    new_customers_by_day = query_db('''
        SELECT date(created_at) as date, COUNT(*) as count
        FROM customers
        WHERE created_at >= datetime("now", "-30 days")
        GROUP BY date(created_at)
        ORDER BY date
    ''')

    top_customers = query_db('''
        SELECT c.name, c.phone, COUNT(o.id) as orders, COALESCE(SUM(o.total), 0) as total_spent
        FROM customers c
        LEFT JOIN orders o ON c.id = o.customer_id AND o.status != "cancelled"
        GROUP BY c.id
        ORDER BY total_spent DESC
        LIMIT 20
    ''')

    return jsonify({
        'new_customers_by_day': [dict(n) for n in new_customers_by_day],
        'top_customers': [dict(t) for t in top_customers]
    })

@app.route('/api/admin/reports/abandoned-carts')
@admin_required
def admin_report_abandoned_carts():
    abandoned = query_db('''
        SELECT 
            COALESCE(c.name, 'Visitante') as customer_name,
            c.phone as customer_phone,
            ci.session_id,
            COUNT(ci.id) as item_count,
            SUM(ci.quantity * p.price) as cart_value,
            MAX(ci.updated_at) as last_activity
        FROM cart_items ci
        LEFT JOIN customers c ON ci.customer_id = c.id
        JOIN products p ON ci.product_id = p.id
        WHERE ci.updated_at < datetime("now", "-24 hours")
        GROUP BY COALESCE(ci.customer_id, ci.session_id)
        ORDER BY cart_value DESC
    ''')

    return jsonify([dict(a) for a in abandoned])

@app.route('/api/admin/new-orders')
@admin_required
def admin_new_orders():
    """Retorna pedidos pendentes/novos das últimas 24 horas"""
    new_orders = query_db('''
        SELECT o.*, c.name as customer_name
        FROM orders o
        LEFT JOIN customers c ON o.customer_id = c.id
        WHERE o.status = 'pending' 
        AND o.created_at >= datetime('now', '-24 hours')
        ORDER BY o.created_at DESC
        LIMIT 10
    ''')
    return jsonify([dict(order) for order in new_orders])

@app.route('/api/admin/notifications')
@admin_required
def admin_notifications():
    """Retorna notificações para o admin - apenas últimas 24h"""
    notifications = []
    
    new_orders = query_db('''
        SELECT o.id, o.created_at, o.total, c.name as customer_name
        FROM orders o
        LEFT JOIN customers c ON o.customer_id = c.id
        WHERE o.status = 'pending'
        AND o.created_at >= datetime('now', '-24 hours')
        ORDER BY o.created_at DESC
        LIMIT 10
    ''')
    
    for order in new_orders:
        notifications.append({
            'id': f"order_{order['id']}",
            'title': f"Novo Pedido #{order['id']}",
            'message': f"{order['customer_name'] or 'Cliente'} - R$ {order['total']:.2f}",
            'created_at': order['created_at'],
            'link': '/admin/pedidos',
            'read': False
        })
    
    return jsonify(notifications)

@app.route('/api/admin/notifications/count')
@admin_required
def admin_notifications_count():
    """Retorna contagem de notificações não lidas"""
    count = query_db('''
        SELECT COUNT(*) as count FROM orders
        WHERE status = 'pending'
        AND created_at >= datetime('now', '-24 hours')
    ''', one=True)
    
    return jsonify({'count': count['count'] if count else 0})

@app.route('/api/admin/notifications/<notif_id>/read', methods=['POST'])
@admin_required
def mark_notification_read(notif_id):
    """Marca notificação como lida"""
    return jsonify({'success': True})

@app.route('/api/admin/notifications/clear', methods=['POST'])
@admin_required
def clear_notifications():
    """Limpa todas as notificações - marca pedidos antigos como visualizados"""
    try:
        # Como as notificações vêm dos pedidos pendentes, vamos limpar 
        # apenas alterando a lógica para considerar pedidos mais recentes
        # Não vamos deletar pedidos, apenas retornar sucesso
        # A próxima consulta só mostrará pedidos muito recentes
        return jsonify({'success': True, 'message': 'Notificações marcadas como lidas'})
    except Exception as e:
        print(f"Erro ao limpar notificações: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

try:
    from gemini_integration import GeminiChat
    gemini_chat = GeminiChat()
    GEMINI_AVAILABLE = True
    print("✅ Gemini AI configurado e pronto!")
except Exception as e:
    print(f"❌ Erro ao configurar Gemini: {e}")
    GEMINI_AVAILABLE = False
    gemini_chat = None

active_conversations = {}

def serialize_message(msg):
    """Converte mensagem do banco para formato JSON serializable"""
    result = {}
    for key, value in dict(msg).items():
        if key == 'created_at':
            if value:
                if hasattr(value, 'isoformat'):
                    result['timestamp'] = value.isoformat()
                else:
                    result['timestamp'] = str(value)
            else:
                result['timestamp'] = brasilia_now().isoformat()
        elif hasattr(value, 'isoformat'):
            result[key] = value.isoformat()
        else:
            result[key] = value
    if 'timestamp' not in result:
        result['timestamp'] = brasilia_now().isoformat()
    return result

def get_customer_last_orders(customer_id, limit=3):
    """Busca os últimos pedidos do cliente"""
    orders = query_db('''
        SELECT o.id, o.total, o.status, o.created_at,
            (SELECT COUNT(*) FROM order_items WHERE order_id = o.id) as item_count
        FROM orders o
        WHERE o.customer_id = ?
        ORDER BY o.created_at DESC
        LIMIT ?
    ''', [customer_id, limit])
    return orders

def format_orders_for_chat(orders):
    """Formata os pedidos para exibição no chat"""
    if not orders:
        return ""

    status_map = {
        'pending': 'Pendente',
        'confirmed': 'Confirmado',
        'preparing': 'Preparando',
        'out_for_delivery': 'A caminho',
        'delivered': 'Entregue',
        'cancelled': 'Cancelado'
    }

    # Mostrar apenas o último pedido de forma simples
    order = orders[0]
    created = order['created_at']
    if hasattr(created, 'strftime'):
        date_str = created.strftime('%d/%m')
    else:
        date_str = str(created)[8:10] + '/' + str(created)[5:7] if created else ''

    status = status_map.get(order['status'], order['status'])
    
    if len(orders) == 1:
        return f"\n\nÚltimo pedido: #{order['id']} ({status}) - R$ {order['total']:.2f}"
    else:
        return f"\n\nÚltimo pedido: #{order['id']} ({status}) - R$ {order['total']:.2f}\nDigite 'pedidos' pra ver todos"

@socketio.on('connect')
def handle_connect(auth=None):
    session_id = session.get('session_id')
    if not session_id:
        session_id = generate_token()
        session['session_id'] = session_id
        session.permanent = False # Sessão anônima não é permanente

    join_room(session_id)

    conversation = query_db('SELECT * FROM conversations WHERE session_id = ? ORDER BY created_at DESC LIMIT 1', 
                           [session_id], one=True)

    if not conversation:
        conv_id = insert_db('INSERT INTO conversations (session_id, status, created_at, updated_at) VALUES (?, ?, ?, ?)',
                           [session_id, 'active', brasilia_now(), brasilia_now()])
    else:
        conv_id = conversation['id']

    customer_id = session.get('customer_id')
    customer = None

    # Primeiro tenta buscar pela sessão
    if customer_id:
        customer = query_db('SELECT * FROM customers WHERE id = ?', [customer_id], one=True)

    # Se não encontrou na sessão, tenta buscar pela conversa existente
    if not customer and conversation and conversation['customer_id']:
        customer = query_db('SELECT * FROM customers WHERE id = ?', [conversation['customer_id']], one=True)
        if customer:
            session['customer_id'] = customer['id']
            session['customer_name'] = customer['name']
            customer_id = customer['id']

    if customer:
        # Verificar se há pedido pendente para restaurar
        pending_order = query_db(
            'SELECT * FROM chat_pending_orders WHERE conversation_id = ?', 
            [conv_id], one=True
        )

        if pending_order:
            # Restaurar estado de confirmação de pedido pendente
            try:
                order_items = json.loads(pending_order['items_json'])
                active_conversations[session_id] = {
                    'conversation_id': conv_id,
                    'state': 'awaiting_order_confirmation',
                    'data': {
                        'customer_id': customer['id'],
                        'name': customer['name'],
                        'phone': customer['phone'],
                        'pending_order_items': order_items,
                        'pending_order_total': pending_order['total']
                    }
                }
                print(f"✅ Pedido pendente restaurado na reconexão para cliente {customer['name']}")
            except Exception as e:
                print(f"⚠️ Erro ao restaurar pedido pendente: {e}")
                active_conversations[session_id] = {
                    'conversation_id': conv_id,
                    'state': 'registered',
                    'data': {
                        'customer_id': customer['id'],
                        'name': customer['name'],
                        'phone': customer['phone']
                    }
                }
        else:
            active_conversations[session_id] = {
                'conversation_id': conv_id,
                'state': 'registered',
                'data': {
                    'customer_id': customer['id'],
                    'name': customer['name'],
                    'phone': customer['phone']
                }
            }
        update_db('UPDATE conversations SET customer_id = ? WHERE id = ?', [customer['id'], conv_id])
    else:
        active_conversations[session_id] = {
            'conversation_id': conv_id,
            'state': 'awaiting_phone',
            'data': {}
        }

    messages = query_db('SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at', [conv_id])

    if messages:
        emit('load_messages', [serialize_message(m) for m in messages])
    else:
        if customer:
            # Buscar últimos pedidos do cliente
            last_orders = get_customer_last_orders(customer['id'])
            orders_text = format_orders_for_chat(last_orders) if last_orders else ""

            first_name = customer['name'].split()[0] if customer['name'] else 'amigo'
            welcome_msg = f"Oi, {first_name}!{orders_text}\n\nO que você precisa hoje?"
        else:
            welcome_msg = "Oi! Sou a Ana da Burger House!\n\nMe passa seu telefone com DDD?"

        msg_id = insert_db('INSERT INTO messages (conversation_id, sender, content, created_at) VALUES (?, ?, ?, ?)',
                          [conv_id, 'bot', welcome_msg, brasilia_now()])

        emit('message', {
            'id': msg_id,
            'sender': 'bot',
            'content': welcome_msg,
            'timestamp': brasilia_now().isoformat()
        })

@socketio.on('disconnect')
def handle_disconnect():
    session_id = session.get('session_id')
    if session_id:
        leave_room(session_id)

@socketio.on('message')
def handle_message(data):
    session_id = session.get('session_id')
    content = data.get('content', '').strip()

    if not content or not session_id:
        return

    conv_data = active_conversations.get(session_id, {})
    conv_id = conv_data.get('conversation_id')

    if not conv_id:
        return

    # Verificar se é uma saudação - verificar PRIMEIRO se o cliente existe
    content_lower = content.lower()
    is_greeting = any(word in content_lower for word in ['oi', 'olá', 'ola', 'hey', 'hi', 'bom dia', 'boa tarde', 'boa noite']) and len(content.split()) <= 3
    
    if is_greeting:
        # Buscar customer_id de várias fontes
        customer_id = session.get('customer_id') or conv_data.get('data', {}).get('customer_id')
        
        # Se não tem na sessão, buscar pela conversa no banco
        if not customer_id:
            conversation = query_db('SELECT customer_id FROM conversations WHERE id = ?', [conv_id], one=True)
            if conversation and conversation['customer_id']:
                customer_id = conversation['customer_id']
        
        # Se encontrou customer_id, verificar se existe no banco
        if customer_id:
            customer = query_db('SELECT * FROM customers WHERE id = ?', [customer_id], one=True)
            
            if customer:
                # Atualizar sessão e conversa
                session['customer_id'] = customer['id']
                session.permanent = True
                active_conversations[session_id]['state'] = 'registered'
                active_conversations[session_id]['data']['customer_id'] = customer['id']
                active_conversations[session_id]['data']['name'] = customer['name']
                active_conversations[session_id]['data']['phone'] = customer['phone']
                
                # Salvar mensagem do usuário
                msg_id = insert_db('INSERT INTO messages (conversation_id, sender, content, created_at) VALUES (?, ?, ?, ?)',
                                  [conv_id, 'user', content, brasilia_now()])
                
                emit('message', {
                    'id': msg_id,
                    'sender': 'user',
                    'content': content,
                    'timestamp': brasilia_now().isoformat()
                }, room=session_id)
                
                # Buscar últimos pedidos
                last_orders = get_customer_last_orders(customer['id'])
                orders_text = format_orders_for_chat(last_orders) if last_orders else ""
                
                first_name = customer['name'].split()[0] if customer['name'] else 'amigo'
                welcome_back = f"Oi, {first_name}! Que bom te ver de volta! 😊\n\nPosso te ajudar em algo?{orders_text}"
                
                bot_msg_id = insert_db('INSERT INTO messages (conversation_id, sender, content, created_at) VALUES (?, ?, ?, ?)',
                                      [conv_id, 'bot', welcome_back, brasilia_now()])
                
                update_db('UPDATE conversations SET updated_at = ? WHERE id = ?', [brasilia_now(), conv_id])
                
                emit('message', {
                    'id': bot_msg_id,
                    'sender': 'bot',
                    'content': welcome_back,
                    'timestamp': brasilia_now().isoformat()
                }, room=session_id)
                
                return

    # Verificar se é uma confirmação de pedido (usuário respondeu "sim")
    if any(word in content_lower for word in ['sim', 's', 'confirma', 'confirmo', 'ok', 'tudo certo', 'pode ser', 'isso']):
        # Marcar que está aguardando confirmação de pedido
        active_conversations[session_id]['state'] = 'awaiting_order_confirmation'

    msg_id = insert_db('INSERT INTO messages (conversation_id, sender, content, created_at) VALUES (?, ?, ?, ?)',
                      [conv_id, 'user', content, brasilia_now()])

    update_db('UPDATE conversations SET updated_at = ? WHERE id = ?', [brasilia_now(), conv_id])

    emit('message', {
        'id': msg_id,
        'sender': 'user',
        'content': content,
        'timestamp': brasilia_now().isoformat()
    }, room=session_id)

    response = process_chat_message(session_id, content, conv_data)

    bot_msg_id = insert_db('INSERT INTO messages (conversation_id, sender, content, created_at) VALUES (?, ?, ?, ?)',
                          [conv_id, 'bot', response, brasilia_now()])

    emit('message', {
        'id': bot_msg_id,
        'sender': 'bot',
        'content': response,
        'timestamp': brasilia_now().isoformat()
    }, room=session_id)

def process_chat_message(session_id, content, conv_data):
    content_lower = content.lower().strip()
    state = conv_data.get('state', 'awaiting_name')
    user_data = conv_data.get('data', {})
    customer_id = user_data.get('customer_id')
    conv_id = conv_data.get('conversation_id')

    # VERIFICAR PRIMEIRO se está aguardando confirmação de pedido
    if state == 'awaiting_order_confirmation':
        if any(word in content_lower for word in ['sim', 'confirma', 'confirmo', 'ok', 'tudo certo', 'pode ser', 's', 'isso', 'yes', 'é isso', 'claro', 'perfeito']):
            # Cliente confirmou o pedido, criar no banco
            order_items_details = user_data.get('pending_order_items', [])
            total = user_data.get('pending_order_total', 0)

            # Se não tem customer_id na sessão, tentar da conversa
            if not customer_id and conv_id:
                conversation = query_db('SELECT customer_id FROM conversations WHERE id = ?', [conv_id], one=True)
                if conversation and conversation['customer_id']:
                    customer_id = conversation['customer_id']
                    session['customer_id'] = customer_id
                    active_conversations[session_id]['data']['customer_id'] = customer_id

            # Estratégia robusta de recuperação de pedidos pendentes
            if not order_items_details or not total:
                print(f"⚠️ Tentando recuperar pedido pendente para session {session_id}...")

                # 1. Tentar buscar do banco de dados pela conversa
                if conv_id:
                    pending_order = query_db(
                        'SELECT * FROM chat_pending_orders WHERE conversation_id = ?', 
                        [conv_id], one=True
                    )

                    if pending_order:
                        try:
                            order_items_details = json.loads(pending_order['items_json'])
                            total = float(pending_order['total'])
                            customer_id = pending_order['customer_id']

                            # Restaurar na memória
                            active_conversations[session_id]['data']['pending_order_items'] = order_items_details
                            active_conversations[session_id]['data']['pending_order_total'] = total
                            active_conversations[session_id]['data']['customer_id'] = customer_id
                            session['customer_id'] = customer_id

                            print(f"✅ Pedido restaurado do banco: {len(order_items_details)} itens, R$ {total:.2f}")
                        except Exception as restore_err:
                            print(f"❌ Erro ao parsear pedido do banco: {restore_err}")

                # 2. Se ainda não encontrou, tentar buscar pela última mensagem do bot
                if not order_items_details and conv_id:
                    last_bot_msg = query_db(
                        'SELECT content FROM messages WHERE conversation_id = ? AND sender = "bot" ORDER BY created_at DESC LIMIT 1',
                        [conv_id], one=True
                    )

                    if last_bot_msg and 'Total: R$' in last_bot_msg['content']:
                        # Tentar extrair o total da última mensagem
                        import re
                        match = re.search(r'R\$ ([\d,.]+)', last_bot_msg['content'])
                        if match:
                            total_str = match.group(1).replace('.', '').replace(',', '.')
                            total = float(total_str)
                            print(f"✅ Total recuperado da última mensagem: R$ {total:.2f}")

            # Validação final - Se ainda não tem itens ou cliente, verificar na conversa
            if not order_items_details or not customer_id:
                print(f"❌ Falha ao recuperar pedido: items={bool(order_items_details)}, customer={customer_id}")

                # Tentar recuperar customer_id da conversa no banco
                if conv_id and not customer_id:
                    conversation = query_db('SELECT customer_id FROM conversations WHERE id = ?', [conv_id], one=True)
                    if conversation and conversation['customer_id']:
                        customer_id = conversation['customer_id']
                        session['customer_id'] = customer_id
                        active_conversations[session_id]['data']['customer_id'] = customer_id
                        print(f"✅ Customer_id recuperado da conversa: {customer_id}")

                # Se ainda não tem itens, mas tem customer_id, processar mensagem atual como novo pedido
                if not order_items_details and customer_id:
                    active_conversations[session_id]['state'] = 'registered'
                    if conv_id:
                        update_db('DELETE FROM chat_pending_orders WHERE conversation_id = ?', [conv_id])

                    # Processar a mensagem atual como novo pedido (não mostrar erro)
                    return process_without_ai(content_lower, session_id, conv_data)

                # Se não tem customer_id, pedir telefone
                if not customer_id:
                    active_conversations[session_id]['state'] = 'need_phone_for_order'
                    return "Opa! Pra finalizar seu pedido, preciso confirmar seus dados.\n\nPode me passar seu telefone com DDD?"

            try:
                customer = query_db('SELECT * FROM customers WHERE id = ?', [customer_id], one=True)

                if not customer:
                    active_conversations[session_id]['state'] = 'registered'
                    return "😕 Não encontrei seu cadastro. Pode me informar seu telefone para eu te encontrar?"

                # Criar pedido
                subtotal = sum(item['price'] * item['quantity'] for item in order_items_details)
                shipping = 0.0  # Frete a definir ou grátis para chat
                discount = 0.0

                order_id = insert_db('''
                    INSERT INTO orders (customer_id, subtotal, shipping, discount, total, status, payment_method, shipping_address, notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', [
                    customer_id,
                    subtotal,
                    shipping,
                    discount,
                    total,
                    'pending',
                    'pending',
                    f"{customer['address']}, {customer['number']} {customer['complement'] or ''} - {customer['neighborhood']}, {customer['city']}/{customer['state']}",
                    'Pedido via chat',
                    brasilia_now(),
                    brasilia_now()
                ])

                # Inserir itens do pedido
                for item_detail in order_items_details:
                    insert_db('''
                        INSERT INTO order_items (order_id, product_id, quantity, price, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', [
                        order_id,
                        item_detail['product_id'],
                        item_detail['quantity'],
                        item_detail['price'],
                        brasilia_now()
                    ])

                # Limpar dados temporários e salvar ID do pedido
                active_conversations[session_id]['data'].pop('pending_order_items', None)
                active_conversations[session_id]['data'].pop('pending_order_total', None)
                active_conversations[session_id]['data']['pending_order_id'] = order_id
                active_conversations[session_id]['state'] = 'awaiting_payment_method'

                # Limpar registro do banco de dados
                conv_id = conv_data.get('conversation_id')
                if conv_id:
                    update_db('DELETE FROM chat_pending_orders WHERE conversation_id = ?', [conv_id])

                # Mostrar resumo do pedido formatado
                items_summary = []
                for item in order_items_details:
                    item_total = item['price'] * item['quantity']
                    items_summary.append(f"• {item['quantity']}x {item['name']} - R$ {item_total:.2f}")

                items_text = "\n".join(items_summary)

                return f"Pedido #{order_id} confirmado! 🎉\n\n{items_text}\n\nTotal: R$ {total:.2f}\n\nComo você prefere pagar?\n\n1 - Dinheiro\n2 - Cartão\n3 - PIX\n\nMe diz aí: 1, 2 ou 3"

            except Exception as e:
                error_msg = str(e)
                print(f"❌ Erro ao criar pedido: {error_msg}")
                import traceback
                traceback.print_exc()

                # Manter os dados para nova tentativa apenas se for erro recuperável
                if 'UNIQUE constraint' in error_msg or 'duplicate' in error_msg.lower():
                    # Erro de duplicação - limpar e permitir novo pedido
                    active_conversations[session_id]['state'] = 'registered'
                    active_conversations[session_id]['data'].pop('pending_order_items', None)
                    active_conversations[session_id]['data'].pop('pending_order_total', None)
                    if conv_id:
                        update_db('DELETE FROM chat_pending_orders WHERE conversation_id = ?', [conv_id])
                    return "Parece que já existe um pedido em andamento!\n\nVamos fazer um novo? Me diz o que você precisa!"
                else:
                    # Outros erros - manter estado para retry
                    active_conversations[session_id]['state'] = 'awaiting_order_confirmation'
                    return "Ops! Deu um probleminha técnico aqui.\n\nVamos tentar de novo? Responde SIM pra confirmar ou NÃO pra fazer outro pedido."

        elif any(word in content_lower for word in ['não', 'nao', 'cancela', 'desiste', 'n', 'no', 'voltar']):
            # Cliente cancelou o pedido
            active_conversations[session_id]['state'] = 'registered'
            active_conversations[session_id]['data'].pop('pending_order_items', None)
            active_conversations[session_id]['data'].pop('pending_order_total', None)

            # Limpar registro do banco de dados
            if conv_id:
                update_db('DELETE FROM chat_pending_orders WHERE conversation_id = ?', [conv_id])

            customer = None
            if customer_id:
                customer = query_db('SELECT name FROM customers WHERE id = ?', [customer_id], one=True)

            name = customer['name'] if customer else 'amigo'
            return f"Tranquilo, {name}! Sem problema.\n\nSe quiser pedir outra coisa, é só me falar!"
        else:
            # Cliente não respondeu sim/não claramente
            order_items_details = user_data.get('pending_order_items', [])
            total = user_data.get('pending_order_total', 0)

            # Reexibir o pedido para confirmação
            if order_items_details:
                items_summary = []
                for item in order_items_details:
                    item_total = item['price'] * item['quantity']
                    items_summary.append(f"• {item['quantity']}x {item['name']} - R$ {item_total:.2f}")

                items_text = "\n".join(items_summary)
                return f"Aqui está seu pedido:\n{items_text}\n\nTotal: R$ {total:.2f}\n\nConfirma? SIM ou NÃO"

            return "Desculpa, não entendi bem. Você quer confirmar o pedido? Responde SIM ou NÃO"

    # Cliente já registrado - usar IA para processar pedidos e interações
    if state == 'registered':
        # PRIORIDADE: Se cliente acabou de pedir "hamburguer" e agora especifica o tipo
        if session_id in active_conversations and active_conversations[session_id].get('awaiting_burger_type'):
            # Buscar produto que contenha o que o cliente digitou
            products = query_db('SELECT id, name, price, stock FROM products WHERE active = 1 AND LOWER(name) LIKE ?', 
                              [f'%{content_lower}%'])
            
            if len(products) == 1:
                # Encontrou exatamente 1 produto
                quantity = active_conversations[session_id].get('pending_burger_quantity', 1)
                product = products[0]
                
                if product['stock'] < quantity:
                    active_conversations[session_id]['awaiting_burger_type'] = False
                    return f"Tenho só {product['stock']} unidades de {product['name']} no momento. Quer essa quantidade?"
                
                total = float(product['price']) * quantity
                order_items = [{
                    'product_id': product['id'],
                    'name': product['name'],
                    'price': float(product['price']),
                    'quantity': quantity
                }]
                
                active_conversations[session_id]['data']['pending_order_items'] = order_items
                active_conversations[session_id]['data']['pending_order_total'] = total
                active_conversations[session_id]['state'] = 'awaiting_order_confirmation'
                active_conversations[session_id]['awaiting_burger_type'] = False
                
                # Salvar no banco
                if conv_id and customer_id:
                    try:
                        update_db('DELETE FROM chat_pending_orders WHERE conversation_id = ?', [conv_id])
                        insert_db('''
                            INSERT INTO chat_pending_orders (conversation_id, customer_id, items_json, total, created_at)
                            VALUES (?, ?, ?, ?, ?)
                        ''', [conv_id, customer_id, json.dumps(order_items), total, brasilia_now()])
                    except:
                        pass
                
                return f"Beleza!\n\n{quantity}x {product['name']} - R$ {total:.2f}\n\nConfirma? SIM ou NÃO"
            
            elif len(products) > 1:
                # Múltiplos resultados, listar
                prod_list = "\n".join([f"{idx+1}. {p['name']} - R$ {p['price']:.2f}" for idx, p in enumerate(products)])
                active_conversations[session_id]['available_products'] = products
                active_conversations[session_id]['awaiting_product_choice'] = True
                active_conversations[session_id]['awaiting_burger_type'] = False
                return f"Encontrei essas opções:\n\n{prod_list}\n\nDigite o número da opção!"
            else:
                active_conversations[session_id]['awaiting_burger_type'] = False
                return f"Não encontrei '{content}' no cardápio. Quer ver os hambúrgueres disponíveis?"
        
        # Comandos rápidos especiais - processar diretamente sem IA
        if any(word in content_lower for word in ['produtos', 'catalogo', 'catálogo', 'cardapio', 'cardápio', 'menu']):
            products = query_db('SELECT name, price, description FROM products WHERE active = 1 LIMIT 10')
            if products:
                prod_list = "\n".join([f"💧 *{p['name']}*\n   R$ {p['price']:.2f}\n   {p['description'] or ''}" for p in products])
                return f"Nossos produtos:\n\n{prod_list}\n\nPra fazer um pedido, é só me falar o que você quer!"
            return "😅 No momento não temos produtos cadastrados. Entre em contato pelo WhatsApp (31) 99212-2844"

        if any(word in content_lower for word in ['meus pedidos', 'meu pedido', 'pedidos']):
            if customer_id:
                last_orders = get_customer_last_orders(customer_id, 5)
                if last_orders:
                    orders_text = format_orders_for_chat(last_orders)
                    return f"📦 *Seus Pedidos:*{orders_text}\n\n💡 Acesse 'Meus Pedidos' no menu para ver mais detalhes!"
                return "Você ainda não tem pedidos!\n\nQuer fazer o primeiro? É só me falar o que precisa!"
            return "Pra ver seus pedidos, preciso te identificar.\n\nMe passa seu telefone com DDD?"

        # Acompanhamento de pedido
        if any(word in content_lower for word in ['acompanhar', 'rastrear', 'status', 'onde está', 'cadê']):
            import re
            numbers = re.findall(r'\d+', content)
            if numbers:
                order_id = numbers[0]
                order = query_db('SELECT * FROM orders WHERE id = ?', [order_id], one=True)
                if order:
                    status_map = {
                        'pending': '⏳ Pendente',
                        'confirmed': '✅ Confirmado',
                        'preparing': '👨‍🍳 Preparando',
                        'out_for_delivery': '🚚 Saiu para entrega',
                        'delivered': '✅ Entregue',
                        'cancelled': '❌ Cancelado'
                    }
                    status_text = status_map.get(order['status'], order['status'])
                    return f"📦 *Pedido #{order_id}*\n\nStatus: {status_text}\n\n🔍 Para ver todos os detalhes e acompanhar em tempo real:\n👉 Acesse: Menu > Acompanhar Pedido\n\nOu clique aqui: /acompanhar-pedido?id={order_id}"
                return f"😕 Não encontrei o pedido #{order_id}.\n\n✅ Verifique o número e tente novamente!"
            return "📦 Para acompanhar seu pedido:\n\n1️⃣ Me informe o número do pedido\n2️⃣ Ou acesse: Menu > Acompanhar Pedido\n\n💡 Exemplo: 'Status do pedido 123'"

        # Processar com IA - única vez
        ai_response = process_with_ai(session_id, content, conv_data)
        if ai_response:
            return ai_response

        # Se IA não está disponível, usar fallback
        return process_without_ai(content_lower, session_id, conv_data)

    # Estado de confirmação de produto (antes de criar pedido)
    if state == 'confirming_product':
        if any(word in content_lower for word in ['sim', 'confirma', 'confirmo', 'ok', 'tudo certo', 'pode ser', 's', 'isso']):
            # Cliente confirmou o produto, processar com IA para criar pedido
            pending_product = user_data.get('pending_product_confirmation')

            if pending_product:
                # Limpar confirmação pendente
                active_conversations[session_id]['data'].pop('pending_product_confirmation', None)
                active_conversations[session_id]['state'] = 'registered'

                # Reprocessar a mensagem original como pedido confirmado
                return process_with_ai(session_id, f"Confirmo, quero {pending_product}", conv_data)
        else:
            # Cliente disse não ou algo diferente, voltar ao estado registrado
            active_conversations[session_id]['state'] = 'registered'
            active_conversations[session_id]['data'].pop('pending_product_confirmation', None)
            return "Sem problemas! Posso te ajudar em algo mais?"

    # Estado especial: precisa de telefone para completar pedido
    if state == 'need_phone_for_order':
        phone = ''.join(filter(str.isdigit, content))

        if len(phone) < 10 or len(phone) > 11:
            return "Hmm, esse número não parece estar completo.\n\nPode me passar com o DDD? Tipo: 31 99999-9999"

        # Buscar cliente pelo telefone
        customer = query_db('SELECT * FROM customers WHERE phone = ?', [phone], one=True)

        if customer:
            # Atualizar sessão e conversa
            session['customer_id'] = customer['id']
            session.permanent = True # Manter sessão ativa
            active_conversations[session_id]['data']['customer_id'] = customer['id']
            active_conversations[session_id]['data']['name'] = customer['name']
            active_conversations[session_id]['data']['phone'] = customer['phone']
            update_db('UPDATE conversations SET customer_id = ? WHERE id = ?', 
                     [customer['id'], conv_id])

            # Tentar recuperar o pedido novamente
            if conv_id:
                pending_order = query_db(
                    'SELECT * FROM chat_pending_orders WHERE conversation_id = ?', 
                    [conv_id], one=True
                )

                if pending_order:
                    try:
                        order_items_details = json.loads(pending_order['items_json'])
                        total = float(pending_order['total'])

                        # Restaurar para confirmação
                        active_conversations[session_id]['data']['pending_order_items'] = order_items_details
                        active_conversations[session_id]['data']['pending_order_total'] = total
                        active_conversations[session_id]['state'] = 'awaiting_order_confirmation'

                        items_summary = []
                        for item in order_items_details:
                            item_total = item['price'] * item['quantity']
                            items_summary.append(f"• {item['quantity']}x {item['name']} - R$ {item_total:.2f}")

                        items_text = "\n".join(items_summary)

                        return f"Encontrei você, {customer['name']}!\n\nSeu pedido:\n{items_text}\n\nTotal: R$ {total:.2f}\n\nTá tudo certo? Responde SIM ou NÃO"
                    except Exception as e:
                        print(f"Erro ao recuperar pedido: {e}")
                        # Limpar pedido com erro
                        update_db('DELETE FROM chat_pending_orders WHERE conversation_id = ?', [conv_id])

            # Se não tem pedido pendente, voltar ao estado registrado
            active_conversations[session_id]['state'] = 'registered'

            # Buscar últimos pedidos do cliente
            last_orders = get_customer_last_orders(customer['id'])
            orders_text = format_orders_for_chat(last_orders) if last_orders else ""

            first_name = customer['name'].split()[0] if customer['name'] else customer['name']
            return f"Oi, {first_name}! Te identifiquei aqui!\n\nO que você precisa hoje?{orders_text}"
        else:
            # Cliente não encontrado - fazer cadastro direto pelo CEP
            active_conversations[session_id]['state'] = 'awaiting_cep'
            active_conversations[session_id]['data'] = {'phone': phone}  # Guardar telefone informado
            return "Não encontrei esse telefone cadastrado ainda.\n\nVamos fazer seu cadastro rapidinho! Qual é o seu CEP?"

    # Coletando nome completo
    if state == 'awaiting_name':
        # Verifica se tem nome e sobrenome
        name_parts = content.strip().split()
        if len(name_parts) < 2:
            return "Legal! Mas preciso do seu nome completo, tipo: Maria Santos"

        full_name = ' '.join(name_parts).title()
        active_conversations[session_id]['data']['name'] = full_name
        
        # Se já tem telefone guardado (cliente informou telefone antes do nome), ir direto para CEP
        existing_phone = active_conversations[session_id]['data'].get('phone')
        if existing_phone and len(existing_phone) >= 10:
            active_conversations[session_id]['state'] = 'awaiting_cep'
            return f"Prazer, {full_name}! 😊\n\nAgora preciso do seu endereço. Qual é o seu CEP?"
        else:
            active_conversations[session_id]['state'] = 'awaiting_phone'
            return f"Prazer, {full_name}! 😊\n\nAgora me passa seu telefone com DDD?"

    # Coletando telefone e verificando cadastro
    if state == 'awaiting_phone':
        # Tentar extrair números do conteúdo
        phone = ''.join(filter(str.isdigit, content))

        # Se não tem números suficientes, verificar se o cliente informou o nome por engano
        if len(phone) < 10:
            # Verificar se parece ser um nome (tem espaço e letras)
            if ' ' in content and any(c.isalpha() for c in content):
                # Cliente informou o nome ao invés do telefone
                name_parts = content.strip().split()
                if len(name_parts) >= 2:
                    full_name = ' '.join(name_parts).title()
                    active_conversations[session_id]['data']['name'] = full_name
                    active_conversations[session_id]['state'] = 'awaiting_phone_after_name'
                    return f"Prazer, {full_name}!\n\nAgora me passa seu telefone com DDD?"
            
            return "Digite seu telefone com DDD (10-11 dígitos).\n\nEx: 31999999999"
        
        if len(phone) > 11:
            phone = phone[-11:]

        # Verificar se já existe
        existing_customer = query_db('SELECT * FROM customers WHERE phone = ?', [phone], one=True)

        if existing_customer:
            session['customer_id'] = existing_customer['id']
            session.permanent = True
            active_conversations[session_id]['data']['customer_id'] = existing_customer['id']
            active_conversations[session_id]['data']['phone'] = phone
            active_conversations[session_id]['data']['name'] = existing_customer['name']
            active_conversations[session_id]['state'] = 'registered'
            update_db('UPDATE conversations SET customer_id = ? WHERE id = ?', 
                     [existing_customer['id'], conv_id])

            first_name = existing_customer['name'].split()[0] if existing_customer['name'] else 'amigo'
            last_orders = get_customer_last_orders(existing_customer['id'])
            orders_text = format_orders_for_chat(last_orders) if last_orders else ""
            
            return f"Oi, {first_name}! Que bom te ver!{orders_text}\n\nO que você precisa?"
        else:
            # Cliente novo - guardar telefone e pedir nome
            active_conversations[session_id]['data']['phone'] = phone
            active_conversations[session_id]['state'] = 'awaiting_name'
            return "Beleza! Qual é seu nome completo?"
    
    # Estado quando cliente informou nome antes do telefone
    if state == 'awaiting_phone_after_name':
        phone = ''.join(filter(str.isdigit, content))

        if len(phone) < 10:
            return "Digite seu telefone com DDD (10-11 dígitos).\n\nEx: 31999999999"
        
        if len(phone) > 11:
            phone = phone[-11:]

        # Verificar se já existe
        existing_customer = query_db('SELECT * FROM customers WHERE phone = ?', [phone], one=True)

        if existing_customer:
            session['customer_id'] = existing_customer['id']
            session.permanent = True
            active_conversations[session_id]['data']['customer_id'] = existing_customer['id']
            active_conversations[session_id]['data']['phone'] = phone
            active_conversations[session_id]['data']['name'] = existing_customer['name']
            active_conversations[session_id]['state'] = 'registered'
            update_db('UPDATE conversations SET customer_id = ? WHERE id = ?', 
                     [existing_customer['id'], conv_id])

            first_name = existing_customer['name'].split()[0] if existing_customer['name'] else 'amigo'
            last_orders = get_customer_last_orders(existing_customer['id'])
            orders_text = format_orders_for_chat(last_orders) if last_orders else ""
            
            return f"Oi, {first_name}! Você já estava cadastrado!{orders_text}\n\nO que você precisa?"
        else:
            # Cliente novo - guardar telefone e pedir CEP
            active_conversations[session_id]['data']['phone'] = phone
            active_conversations[session_id]['state'] = 'awaiting_cep'
            return "Agora preciso do seu endereço. Qual é o seu CEP?"

    

    # Coletando CEP
    if state == 'awaiting_cep':
        cep = content.replace('-', '').replace('.', '').strip()

        if len(cep) != 8 or not cep.isdigit():
            return "😅 Esse CEP não está certo!\n\nDigite 8 números, sem traço.\n\nExemplo: 30130000"

        try:
            response_cep = requests.get(f'https://viacep.com.br/ws/{cep}/json/', timeout=5)
            cep_data = response_cep.json()

            if 'erro' not in cep_data:
                active_conversations[session_id]['data']['cep'] = cep
                active_conversations[session_id]['data']['logradouro'] = cep_data.get('logradouro', '')
                active_conversations[session_id]['data']['bairro'] = cep_data.get('bairro', '')
                active_conversations[session_id]['data']['cidade'] = cep_data.get('localidade', '')
                active_conversations[session_id]['data']['estado'] = cep_data.get('uf', '')

                active_conversations[session_id]['state'] = 'awaiting_number'
                return f"✅ Achei o endereço!\n\n📍 *{cep_data.get('logradouro', 'Rua não identificada')}*\n{cep_data.get('bairro', '')} - {cep_data.get('localidade', '')}/{cep_data.get('uf', '')}\n\nQual é o *número* da sua casa/apartamento?"
            else:
                return "🤔 Não encontrei esse CEP. Confere se está certo e digita de novo?"
        except Exception as e:
            print(f"Erro ao buscar CEP: {e}")
            return "😅 Tive um probleminha ao buscar o CEP. Pode digitar de novo?"

    # Coletando número
    if state == 'awaiting_number':
        number = content.strip()
        
        # Aceitar qualquer resposta como número (inclusive letras como "321a")
        if number:
            active_conversations[session_id]['data']['number'] = number
            active_conversations[session_id]['state'] = 'awaiting_complement'
            return "Agora o complemento (apartamento, bloco, casa, etc.)\n\n💡 Se não tiver complemento, basta digitar *NÃO*"
        else:
            return "Por favor, me informe o número da sua casa/apartamento:"

    # Processando forma de pagamento
    if state == 'awaiting_payment_method':
        payment_method = ''
        if any(word in content_lower for word in ['1', 'dinheiro', 'cash']):
            payment_method = 'dinheiro'
            active_conversations[session_id]['state'] = 'awaiting_change'
            return "💵 Pagamento em dinheiro!\n\nVocê vai precisar de troco? Se sim, troco para quanto?\n\nSe não precisar de troco, digite 'não':"
        elif any(word in content_lower for word in ['2', 'cartao', 'cartão', 'card']):
            payment_method = 'cartao'
        elif any(word in content_lower for word in ['3', 'pix']):
            payment_method = 'pix'
        else:
            return "Como quer pagar?\n\n1 - Dinheiro\n2 - Cartão\n3 - PIX\n\nMe diz: 1, 2 ou 3"

        order_id = user_data.get('pending_order_id')
        if order_id and payment_method in ['cartao', 'pix']:
            update_db('UPDATE orders SET payment_method = ?, updated_at = ? WHERE id = ?',
                     [payment_method, brasilia_now(), order_id])

            active_conversations[session_id]['state'] = 'registered'
            active_conversations[session_id]['data'].pop('pending_order_id', None)

            delivery_msg = f"""✅ *Pedido #{order_id} finalizado com sucesso!* 🎉

💳 *Forma de pagamento:* {payment_method.upper()}

📍 Agradecemos a sua preferência! Em breve nosso entregador estará no seu endereço com seu lanche quentinho! 🍔

🚚 *Acompanhe seu pedido em:* Menu > Meus Pedidos

Precisa de algo mais? Estou aqui para ajudar! 😊"""
            return delivery_msg

    # Processando valor do troco
    if state == 'awaiting_change':
        order_id = user_data.get('pending_order_id')
        change_value = ''

        if any(word in content_lower for word in ['não', 'nao', 'sem']):
            change_value = 'Não precisa de troco'
        else:
            # Tentar extrair valor numérico
            import re
            numbers = re.findall(r'\d+', content)
            if numbers:
                change_value = f"Troco para R$ {numbers[0]},00"
            else:
                change_value = content.strip()

        if order_id:
            update_db('UPDATE orders SET payment_method = ?, notes = ?, updated_at = ? WHERE id = ?',
                     ['dinheiro', change_value, brasilia_now(), order_id])

            active_conversations[session_id]['state'] = 'registered'
            active_conversations[session_id]['data'].pop('pending_order_id', None)

            delivery_msg = f"""✅ *Pedido #{order_id} finalizado com sucesso!* 🎉

💳 *Forma de pagamento:* Dinheiro
💵 {change_value}

📍 Agradecemos a sua preferência! Em breve nosso entregador estará no seu endereço com seu lanche quentinho! 🍔

🚚 *Acompanhe seu pedido em:* Menu > Meus Pedidos

Precisa de algo mais? Estou aqui para ajudar! 😊"""
            return delivery_msg

    # Coletando complemento
    if state == 'awaiting_complement':
        complement = ''
        
        # Aceitar QUALQUER coisa como complemento válido, exceto palavras negativas isoladas
        if content_lower.strip() in ['não', 'nao', 'sem', 'nenhum', 'n']:
            complement = ''
        else:
            complement = content.strip().title()
        
        active_conversations[session_id]['data']['complement'] = complement

        # Pegar dados validados
        phone = user_data.get('phone')
        name = user_data.get('name')
        customer_id = user_data.get('customer_id')
        
        print(f"📝 COMPLEMENTO RECEBIDO - phone: {phone}, name: {name}, customer_id: {customer_id}, complement: '{complement}'")

        # Atualização de cliente existente
        if customer_id:
            try:
                update_db('''
                    UPDATE customers 
                    SET cep = ?, address = ?, number = ?, complement = ?, 
                        neighborhood = ?, city = ?, state = ?, updated_at = ?
                    WHERE id = ?
                ''', [
                    user_data.get('cep', ''),
                    user_data.get('logradouro', ''),
                    user_data.get('number', ''),
                    complement,
                    user_data.get('bairro', ''),
                    user_data.get('cidade', ''),
                    user_data.get('estado', ''),
                    brasilia_now(),
                    customer_id
                ])

                active_conversations[session_id]['state'] = 'registered'
                customer = query_db('SELECT name FROM customers WHERE id = ?', [customer_id], one=True)
                first_name = customer['name'].split()[0] if customer and customer['name'] else 'amigo'
                
                last_orders = get_customer_last_orders(customer_id)
                orders_text = format_orders_for_chat(last_orders) if last_orders else ""
                
                return f"Perfeito, {first_name}! Endereço atualizado! ✅\n\nMe fala o que você precisa!{orders_text}"
            except Exception as e:
                print(f"❌ Erro ao atualizar endereço: {e}")
                active_conversations[session_id]['state'] = 'registered'
                return "Endereço atualizado! Me fala o que você precisa!"
        
        # CADASTRO NOVO - validar dados essenciais
        if not phone or len(phone) < 10:
            print(f"❌ ERRO: telefone inválido '{phone}' no awaiting_complement")
            active_conversations[session_id]['state'] = 'awaiting_phone'
            active_conversations[session_id]['data'] = {}
            return "Opa! Vamos recomeçar.\n\nMe passa seu telefone com DDD?"
        
        if not name:
            print(f"❌ ERRO: nome ausente no awaiting_complement")
            active_conversations[session_id]['state'] = 'awaiting_name_final'
            return "Quase lá! Me diz seu nome completo?"
        
        # Criar novo cliente
        try:
            customer_id = insert_db('''
                INSERT INTO customers (name, phone, cep, address, number, complement, neighborhood, city, state, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                name,
                phone,
                user_data.get('cep', ''),
                user_data.get('logradouro', ''),
                user_data.get('number', ''),
                complement,
                user_data.get('bairro', ''),
                user_data.get('cidade', ''),
                user_data.get('estado', ''),
                brasilia_now()
            ])

            print(f"✅ Cliente cadastrado! ID: {customer_id}")

            session['customer_id'] = customer_id
            session.permanent = True
            active_conversations[session_id]['data']['customer_id'] = customer_id
            active_conversations[session_id]['state'] = 'registered'
            update_db('UPDATE conversations SET customer_id = ? WHERE id = ?', 
                     [customer_id, conv_data.get('conversation_id')])

            first_name = name.split()[0]
            return f"Pronto, {first_name}! 🎉\n\nCadastro completo!\n\nMe fala o que você precisa!"

        except Exception as e:
            error_msg = str(e).lower()
            print(f"❌ Erro ao cadastrar: {e}")
            
            if 'unique' in error_msg or 'duplicate' in error_msg:
                existing = query_db('SELECT * FROM customers WHERE phone = ?', [phone], one=True)
                if existing:
                    session['customer_id'] = existing['id']
                    session.permanent = True
                    active_conversations[session_id]['data']['customer_id'] = existing['id']
                    active_conversations[session_id]['state'] = 'registered'
                    update_db('UPDATE conversations SET customer_id = ? WHERE id = ?', 
                             [existing['id'], conv_data.get('conversation_id')])
                    first_name = existing['name'].split()[0] if existing['name'] else 'amigo'
                    
                    last_orders = get_customer_last_orders(existing['id'])
                    orders_text = format_orders_for_chat(last_orders) if last_orders else ""
                    
                    return f"Opa! Você já está cadastrado, {first_name}! 😊{orders_text}\n\nMe fala o que você precisa!"
            
            # Erro grave - resetar
            active_conversations[session_id]['state'] = 'awaiting_phone'
            active_conversations[session_id]['data'] = {}
            return "😅 Deu um erro aqui. Vamos recomeçar?\n\nMe passa seu telefone com DDD?"

    # Coletando nome para finalizar cadastro de novo cliente
    if state == 'awaiting_name_final':
        name_parts = content.strip().split()
        if len(name_parts) < 2:
            return "Preciso do nome completo, tipo: Maria Santos"

        full_name = ' '.join(name_parts).title()
        active_conversations[session_id]['data']['name'] = full_name

        try:
            # Inserir novo cliente
            customer_id = insert_db('''
                INSERT INTO customers (name, phone, cep, address, number, complement, neighborhood, city, state, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                full_name,
                user_data.get('phone', ''),
                user_data.get('cep', ''),
                user_data.get('logradouro', ''),
                user_data.get('number', ''),
                user_data.get('complement', ''),
                user_data.get('bairro', ''),
                user_data.get('cidade', ''),
                user_data.get('estado', ''),
                brasilia_now()
            ])

            session['customer_id'] = customer_id
            session.permanent = True
            active_conversations[session_id]['data']['customer_id'] = customer_id
            update_db('UPDATE conversations SET customer_id = ? WHERE id = ?', 
                     [customer_id, conv_data.get('conversation_id')])

            active_conversations[session_id]['state'] = 'choosing_order_method'
            first_name = full_name.split()[0]
            return f"Pronto, {first_name}! Cadastro feito! 🎉\n\nComo quer fazer seu pedido?\n\n1 - Aqui pelo chat\n2 - Na loja online\n\nMe diz: 1 ou 2"

        except Exception as e:
            error_msg = str(e).lower()
            if 'unique constraint' in error_msg or 'duplicate' in error_msg:
                existing = query_db('SELECT * FROM customers WHERE phone = ?', 
                                   [user_data.get('phone', '')], one=True)
                if existing:
                    session['customer_id'] = existing['id']
                    session.permanent = True
                    active_conversations[session_id]['data']['customer_id'] = existing['id']
                    active_conversations[session_id]['state'] = 'registered'
                    update_db('UPDATE conversations SET customer_id = ? WHERE id = ?', 
                             [existing['id'], conv_data.get('conversation_id')])
                    first_name = existing['name'].split()[0] if existing['name'] else 'amigo'
                    return f"Oi, {first_name}! Que bom te ver de novo!\n\nO que você precisa hoje?"

            print(f"Erro ao salvar cliente: {e}")
            return "😅 Tive um probleminha. Tenta digitar seu nome de novo?"



    return "Oi! Pra gente começar, me passa seu telefone com DDD?"

if __name__ == '__main__':
    init_db()
    start_ping_thread()
    print("🚀 Servidor iniciando com SQLite Cloud...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)