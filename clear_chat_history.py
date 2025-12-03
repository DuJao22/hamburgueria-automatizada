
import sqlitecloud

SQLITECLOUD_URL = "sqlitecloud://cmq6frwshz.g4.sqlite.cloud:8860/burger_house.db?apikey=Dor8OwUECYmrbcS5vWfsdGpjCpdm9ecSDJtywgvRw8k"

def clear_chat_and_customers():
    """Limpa todo o histórico de chat e dados de clientes"""
    try:
        conn = sqlitecloud.connect(SQLITECLOUD_URL)
        
        print("🔄 Iniciando limpeza do banco de dados...")
        
        # Limpar pedidos pendentes do chat
        conn.execute("DELETE FROM chat_pending_orders")
        print("✅ Pedidos pendentes do chat removidos")
        
        # Limpar mensagens
        conn.execute("DELETE FROM messages")
        print("✅ Mensagens removidas")
        
        # Limpar conversas
        conn.execute("DELETE FROM conversations")
        print("✅ Conversas removidas")
        
        # Limpar tokens de login
        conn.execute("DELETE FROM login_tokens")
        print("✅ Tokens de login removidos")
        
        # Limpar itens do carrinho
        conn.execute("DELETE FROM cart_items")
        print("✅ Itens do carrinho removidos")
        
        # Limpar itens de pedidos
        conn.execute("DELETE FROM order_items")
        print("✅ Itens de pedidos removidos")
        
        # Limpar logs de pedidos
        conn.execute("DELETE FROM order_logs")
        print("✅ Logs de pedidos removidos")
        
        # Limpar pedidos
        conn.execute("DELETE FROM orders")
        print("✅ Pedidos removidos")
        
        # Limpar clientes
        conn.execute("DELETE FROM customers")
        print("✅ Clientes removidos")
        
        # Resetar sequências (autoincrement)
        conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('messages', 'conversations', 'customers', 'orders', 'order_items', 'cart_items', 'login_tokens', 'chat_pending_orders', 'order_logs')")
        print("✅ Sequências resetadas")
        
        conn.commit()
        conn.close()
        
        print("\n🎉 Limpeza concluída com sucesso!")
        print("📊 Histórico de chat e dados de clientes foram completamente removidos.")
        
    except Exception as e:
        print(f"❌ Erro ao limpar banco de dados: {e}")

if __name__ == "__main__":
    resposta = input("⚠️  ATENÇÃO: Isso vai apagar TODOS os dados de clientes, conversas e pedidos!\nTem certeza? (digite 'SIM' para confirmar): ")
    
    if resposta.upper() == 'SIM':
        clear_chat_and_customers()
    else:
        print("❌ Operação cancelada.")
