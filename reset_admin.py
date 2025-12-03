
import hashlib
import sqlitecloud
import os
from dotenv import load_dotenv

load_dotenv()

SQLITECLOUD_URL = os.environ.get('SQLITECLOUD_URL')

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Conectar ao banco
conn = sqlitecloud.connect(SQLITECLOUD_URL)

# Senha: admin123
new_password_hash = hash_password('admin123')

print(f"Hash gerado para 'admin123': {new_password_hash}")

# Atualizar ou inserir admin
try:
    # Tentar atualizar
    conn.execute(
        "UPDATE users SET password = ? WHERE username = 'admin'",
        [new_password_hash]
    )
    
    # Se não atualizou nada, inserir
    result = conn.execute("SELECT COUNT(*) as count FROM users WHERE username = 'admin'").fetchone()
    
    if result[0] == 0:
        conn.execute(
            "INSERT INTO users (username, password, email, is_admin) VALUES (?, ?, ?, ?)",
            ['admin', new_password_hash, 'admin@arigua.com.br', 1]
        )
        print("✅ Admin criado com sucesso!")
    else:
        print("✅ Senha do admin atualizada com sucesso!")
    
    conn.commit()
    
except Exception as e:
    print(f"❌ Erro: {e}")
finally:
    conn.close()

print("\n📝 Credenciais do Admin:")
print("   Usuário: admin")
print("   Senha: admin123")
