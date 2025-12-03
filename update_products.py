#!/usr/bin/env python3
"""
Script para atualizar produtos e categorias para hamburgueria
Desenvolvido por João Layon
"""

import os
import sqlitecloud

def get_db_connection():
    """Conectar ao SQLite Cloud"""
    connection_string = os.environ.get('SQLITECLOUD_URL') or os.environ.get('SQLITECLOUD_CONNECTION_STRING')
    if not connection_string:
        print("❌ SQLITECLOUD_URL não definida")
        return None
    
    try:
        conn = sqlitecloud.connect(connection_string)
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return None

def update_categories(conn):
    """Atualizar categorias para hamburgueria"""
    categories = [
        (1, 'Hambúrgueres', 'Hambúrgueres artesanais com blend exclusivo', 1),
        (2, 'Combos', 'Combos completos com hambúrguer, batata e bebida', 1),
        (3, 'Acompanhamentos', 'Batatas fritas, onion rings e outros acompanhamentos', 1),
        (4, 'Bebidas', 'Refrigerantes, sucos e outras bebidas', 1),
        (5, 'Sobremesas', 'Milkshakes, brownies e sobremesas especiais', 1)
    ]
    
    for cat in categories:
        try:
            conn.execute('''
                INSERT OR REPLACE INTO categories (id, name, description, active) 
                VALUES (?, ?, ?, ?)
            ''', cat)
        except Exception as e:
            print(f"⚠️ Erro ao atualizar categoria {cat[1]}: {e}")
    
    conn.commit()
    print("✅ Categorias atualizadas!")

def update_products(conn):
    """Atualizar produtos para hamburgueria"""
    products = [
        (1, 'Classic Burger', 'Hambúrguer artesanal 180g, queijo cheddar, alface, tomate, cebola e molho especial', 29.90, 1, 100, 1, 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400'),
        (2, 'Cheese Bacon Burger', 'Hambúrguer 180g, queijo cheddar duplo, bacon crocante e molho barbecue', 34.90, 1, 100, 1, 'https://images.unsplash.com/photo-1553979459-d2229ba7433b?w=400'),
        (3, 'Smash Burger Duplo', 'Dois hambúrgueres smash 90g, queijo americano, cebola caramelizada', 32.90, 1, 100, 1, 'https://images.unsplash.com/photo-1594212699903-ec8a3eca50f5?w=400'),
        (4, 'BBQ Burger', 'Hambúrguer 180g, queijo provolone, onion rings, molho BBQ defumado', 36.90, 1, 100, 1, 'https://images.unsplash.com/photo-1572802419224-296b0aeee0d9?w=400'),
        (5, 'Veggie Burger', 'Hambúrguer vegetariano de grão-de-bico, queijo, alface, tomate e maionese de ervas', 28.90, 1, 80, 1, 'https://images.unsplash.com/photo-1520072959219-c595dc870360?w=400'),
        (6, 'Double Burger', 'Dois hambúrgueres 150g, queijo cheddar triplo, bacon e molho especial', 42.90, 1, 100, 1, 'https://images.unsplash.com/photo-1551782450-17144efb9c50?w=400'),
        
        (7, 'Combo Classic', 'Classic Burger + Batata Frita média + Refrigerante 350ml', 44.90, 2, 100, 1, 'https://images.unsplash.com/photo-1610614819513-58e34989848b?w=400'),
        (8, 'Combo Cheese Bacon', 'Cheese Bacon Burger + Batata Frita grande + Refrigerante 500ml', 52.90, 2, 100, 1, 'https://images.unsplash.com/photo-1586816001966-79b736744398?w=400'),
        (9, 'Combo Family', '2 Classic Burgers + 2 Cheese Bacon + Batata grande + 4 Refrigerantes', 139.90, 2, 50, 1, 'https://images.unsplash.com/photo-1550547660-d9450f859349?w=400'),
        (10, 'Combo Kids', 'Mini Burger + Batata pequena + Suco de laranja + Brinde', 29.90, 2, 80, 1, 'https://images.unsplash.com/photo-1596956470007-2bf6095e7e16?w=400'),
        
        (11, 'Batata Frita Pequena', 'Porção de batata frita crocante - 150g', 12.90, 3, 200, 1, 'https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=400'),
        (12, 'Batata Frita Média', 'Porção de batata frita crocante - 250g', 18.90, 3, 200, 1, 'https://images.unsplash.com/photo-1630384060421-cb20d0e0649d?w=400'),
        (13, 'Batata Frita Grande', 'Porção de batata frita crocante - 400g', 24.90, 3, 200, 1, 'https://images.unsplash.com/photo-1529589510304-b7e994a92f60?w=400'),
        (14, 'Onion Rings', 'Anéis de cebola empanados e fritos - 200g', 16.90, 3, 150, 1, 'https://images.unsplash.com/photo-1639024471283-03518883512d?w=400'),
        (15, 'Batata com Cheddar e Bacon', 'Batata frita com cheddar cremoso e bacon crocante', 28.90, 3, 100, 1, 'https://images.unsplash.com/photo-1585109649139-366815a0d713?w=400'),
        
        (16, 'Coca-Cola 350ml', 'Refrigerante Coca-Cola lata 350ml', 6.90, 4, 300, 1, 'https://images.unsplash.com/photo-1554866585-cd94860890b7?w=400'),
        (17, 'Coca-Cola 500ml', 'Refrigerante Coca-Cola garrafa 500ml', 8.90, 4, 300, 1, 'https://images.unsplash.com/photo-1629203851122-3726ecdf080e?w=400'),
        (18, 'Guaraná Antarctica 350ml', 'Refrigerante Guaraná Antarctica lata 350ml', 5.90, 4, 300, 1, 'https://images.unsplash.com/photo-1625772299848-391b6a87d7b3?w=400'),
        (19, 'Suco de Laranja Natural', 'Suco de laranja natural - 300ml', 9.90, 4, 100, 1, 'https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=400'),
        (20, 'Água Mineral 500ml', 'Água mineral sem gás 500ml', 4.90, 4, 300, 1, 'https://images.unsplash.com/photo-1560023907-5f339617ea30?w=400'),
        
        (21, 'Milkshake Chocolate', 'Milkshake cremoso de chocolate - 400ml', 18.90, 5, 80, 1, 'https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=400'),
        (22, 'Milkshake Morango', 'Milkshake cremoso de morango - 400ml', 18.90, 5, 80, 1, 'https://images.unsplash.com/photo-1579954115545-a95591f28bfc?w=400'),
        (23, 'Milkshake Ovomaltine', 'Milkshake cremoso de ovomaltine - 400ml', 19.90, 5, 80, 1, 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400'),
        (24, 'Brownie com Sorvete', 'Brownie de chocolate com sorvete de creme e calda', 16.90, 5, 60, 1, 'https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=400'),
        (25, 'Petit Gateau', 'Bolo de chocolate com centro cremoso e sorvete', 21.90, 5, 50, 1, 'https://images.unsplash.com/photo-1624353365286-3f8d62daad51?w=400')
    ]
    
    for prod in products:
        try:
            conn.execute('''
                INSERT OR REPLACE INTO products (id, name, description, price, category_id, stock, active, image_url) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', prod)
        except Exception as e:
            print(f"⚠️ Erro ao atualizar produto {prod[1]}: {e}")
    
    conn.commit()
    print("✅ Produtos atualizados!")

def delete_old_products(conn):
    """Desativar produtos antigos (IDs maiores que 25)"""
    try:
        conn.execute('UPDATE products SET active = 0 WHERE id > 25')
        conn.commit()
        print("✅ Produtos antigos desativados!")
    except Exception as e:
        print(f"⚠️ Erro ao desativar produtos antigos: {e}")

def main():
    print("🍔 Atualizando banco de dados para Burger House...")
    
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        update_categories(conn)
        update_products(conn)
        delete_old_products(conn)
        print("\n🎉 Banco de dados atualizado com sucesso!")
    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
