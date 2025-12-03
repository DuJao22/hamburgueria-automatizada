# Ariguá Distribuidora & Ponto D'Água - Sistema de Vendas

## Visão Geral
Sistema completo de e-commerce para distribuidora de galões de água mineral e bebidas, com chat integrado, assistente virtual com IA (Google Gemini), e painel administrativo profissional.

**Desenvolvido por:** João Layon - Full Stack Developer

## Informações da Empresa
- **Nome:** Ariguá Distribuidora & Ponto D'Água
- **Endereço:** R. Rio Xingu, 753 - Riacho, Contagem - MG, 32265-290
- **Telefones:** (31) 3044-5050 | 3044-5060 | 3041-4327 | 3044-7704
- **WhatsApp:** (31) 99212-2844
- **Horário:**
  - Segunda a Sexta: 08:30 - 17:30
  - Sábado: 08:30 - 12:30
  - Domingo: Fechado

## Tecnologias
- **Backend:** Python Flask + Flask-SocketIO
- **Banco de Dados:** SQLite Cloud (hospedado na nuvem)
- **IA:** Google Gemini (integração opcional)
- **Frontend:** HTML5 + CSS3 + JavaScript vanilla
- **Gráficos:** Chart.js
- **WebSocket:** Socket.IO para chat em tempo real
- **Keep-Alive:** Sistema de ping automático a cada 5 minutos

## Estrutura do Projeto

```
├── app.py                 # Aplicação principal Flask
├── gemini_integration.py  # Integração com Google Gemini AI
├── schema.sql             # Schema do banco de dados
├── database.db            # Banco de dados SQLite
├── templates/
│   ├── base.html          # Template base
│   ├── index.html         # Página inicial
│   ├── chat.html          # Interface do chat
│   ├── loja.html          # Catálogo de produtos
│   ├── carrinho.html      # Carrinho de compras
│   ├── login.html         # Login de clientes
│   ├── admin_login.html   # Login administrativo
│   └── admin/
│       ├── base.html      # Template base admin
│       ├── dashboard.html # Dashboard interativo
│       ├── produtos.html  # Gestão de produtos
│       ├── pedidos.html   # Gestão de pedidos
│       ├── clientes.html  # Gestão de clientes
│       ├── conversas.html # Histórico de conversas
│       └── relatorios.html# Relatórios e métricas
├── static/
│   ├── css/               # Estilos CSS
│   ├── images/            # Logo e imagens
│   │   └── logo-arigua.png
│   └── js/                # JavaScript
│       └── admin/         # Scripts do painel admin
```

## Funcionalidades

### Chat Inteligente
- Interface estilo WhatsApp
- Botões flutuantes de ação rápida (WhatsApp, chat, carrinho)
- Responsivo para celulares
- Integração com IA Gemini (se configurado)
- Cadastro de clientes via chat
- Auto-fill de CEP via ViaCEP

### E-commerce
- Catálogo de produtos (galões de água, bebidas)
- Carrinho de compras persistente
- Busca de produtos
- Sistema de pedidos
- Botão de pedido via WhatsApp

### Painel Administrativo
- Dashboard interativo com gráficos
- Gestão de produtos e categorias
- Gestão de pedidos com status
- Visualização de clientes
- Histórico de conversas
- Relatórios de vendas, clientes e carrinhos abandonados

## Credenciais de Acesso Admin

- **URL:** /admin/login
- **Usuário:** admin
- **Senha:** admin123

## APIs Principais

### Públicas
- `GET /api/products` - Lista produtos
- `GET /api/categories` - Lista categorias
- `GET /api/cep/<cep>` - Busca CEP (ViaCEP)
- `GET/POST/PUT/DELETE /api/cart` - Gerencia carrinho

### Administrativas (requer login)
- `GET /api/admin/dashboard` - Dados do dashboard
- `GET/POST/PUT/DELETE /api/admin/products` - Produtos
- `GET/POST/PUT/DELETE /api/admin/categories` - Categorias
- `GET/PUT /api/admin/orders` - Pedidos
- `GET /api/admin/customers` - Clientes
- `GET /api/admin/conversations` - Conversas
- `GET /api/admin/reports/*` - Relatórios

## Configuração

### Variáveis de Ambiente
- `SQLITECLOUD_URL` - URL de conexão do SQLite Cloud (obrigatório)
- `SESSION_SECRET` - Chave secreta para sessões
- `GEMINI_API_KEY` - Chave da API do Google Gemini (opcional)

### Executar
```bash
python app.py
```

O servidor inicia em `http://0.0.0.0:5000`

## Deploy no Render

### Configuração do Web Service
| Campo | Valor |
|-------|-------|
| **Name** | `arigua-distribuidora` |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:10000 app:app` |

### Variáveis de Ambiente no Render
| Key | Value |
|-----|-------|
| `PYTHON_VERSION` | `3.11` |
| `SQLITECLOUD_URL` | (sua URL do SQLite Cloud) |
| `SESSION_SECRET` | (chave secreta) |
| `GEMINI_API_KEY` | (sua chave da API Gemini) |

## Identidade Visual
- **Cores principais:** Azul (#0D3B66, #1a5490)
- **Cor de destaque:** Verde WhatsApp (#25D366)
- **Logo:** static/images/logo-arigua.png

## Observações
- O banco SQLite é inicializado automaticamente
- Produtos e categorias de exemplo são criados na inicialização
- A integração com Gemini é opcional - funciona sem ela
- WhatsApp integrado para pedidos diretos
