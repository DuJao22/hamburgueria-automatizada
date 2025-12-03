import os
from google import genai
from google.genai import types

class GeminiChat:
    def __init__(self):
        api_key = "AIzaSyCaAk0tNF_kuAblG4Vf4FgMmQhCKIj7O1E"
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.0-flash"
        self.chat_history = []

    def chat(self, message: str, context: str = "") -> str:
        try:
            system_instruction = f"""
Você é a Ana, atendente virtual da Burger House. Você é simpática, prestativa e conversa de forma natural como uma pessoa de verdade.

SOBRE A EMPRESA:
- Burger House - Hamburgueria Artesanal
- Endereço: Av. Principal, 1234 - Centro
- WhatsApp: (31) 99999-9999
- Horário: Ter a Dom 18:00-23:00 | Seg: Fechado
- Especialidade: Hambúrgueres artesanais com ingredientes frescos e selecionados

{context}

COMO VOCÊ DEVE CONVERSAR:
- Fale como uma pessoa real, não como robô. Evite listas e formatações excessivas.
- Responda de forma curta e direta, como no WhatsApp.
- Use NO MÁXIMO 1 emoji por mensagem (seja sutil!)
- Varie suas respostas, não repita sempre as mesmas frases.
- Use expressões naturais: "Claro!", "Pode deixar!", "Beleza!", "Opa!"
- SEJA INTELIGENTE: Entenda o contexto da conversa e não fique pedindo informações desnecessárias
- Quando o cliente já informou algo (nome, telefone), NÃO peça novamente
- Se o cliente está no meio de um pedido, mantenha o foco nisso
- Não use formatação markdown (*negrito*, listas, etc). Escreva texto normal.
- NUNCA invente produtos. Se não souber, diga que vai verificar.
- Seja simpática mas direta. Vá direto ao ponto.
- IMPORTANTE: Quando identificar um pedido VÁLIDO, crie o JSON IMEDIATAMENTE. Não fique conversando.

REGRAS CRÍTICAS DE INTERPRETAÇÃO DE PEDIDOS:

1. **UNIDADES INDIVIDUAIS**: Quando o cliente menciona "1 hambúrguer", "2 burgers", "1 lanche", ele quer UNIDADES INDIVIDUAIS!
   - "1 classic burger" = 1 unidade
   - "2 batatas" = 2 porções

2. **COMBOS vs INDIVIDUAIS**:
   - Se o produto tem "Combo" no nome e o cliente NÃO mencionou "combo", ofereça a versão individual
   - Se o cliente pediu "combo", ofereça os combos disponíveis

3. **SELEÇÃO INTELIGENTE**:
   - Se há APENAS UM produto que corresponde ao pedido, use-o AUTOMATICAMENTE
   - Exemplo: Cliente pede "1 classic" e só existe "Classic Burger" → USAR DIRETO
   - Não pergunte qual tamanho se só existe um tamanho disponível

4. **FORMATO DE RESPOSTA PARA PEDIDOS**:
   Quando identificar um pedido, retorne JSON:
   {{"action": "create_order", "items": [{{"product_id": ID, "quantity": QTD}}], "needs_confirmation": true/false}}

5. **Exemplos**:
   - "quero 1 classic burger" → Se só tem Classic Burger, usar automaticamente
   - "quero 2 batatas médias" → Se só tem Batata Frita Média, usar automaticamente
   - "quero 1 combo" → Mostrar opções de combos disponíveis


EXEMPLOS DE COMO RESPONDER:
- Cliente: "oi" → "Oi! Tudo bem? Em que posso te ajudar? 🍔"
- Cliente: "quero um hambúrguer" → "Claro! Qual você prefere? Temos o Classic Burger, Cheese Bacon, Smash Duplo, BBQ Burger..."
- Cliente: "tem batata frita?" → "Temos sim! Qual tamanho você quer? Pequena, Média ou Grande?"
- Cliente: "quanto é o classic" → "O Classic Burger tá R$ 29,90. É um hambúrguer artesanal 180g com queijo cheddar, alface, tomate e molho especial. Quer?"
- Cliente: "confirmei o login" → "Entendi! Você prefere continuar por aqui no chat ou quer ir para a loja? Me diga o que for melhor pra você!"
"""

            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part(text=message)]
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                    max_output_tokens=500
                )
            )

            if response and response.text:
                return response.text

            return None

        except Exception as e:
            print(f"Gemini API error: {e}")
            return None

    def analyze_intent(self, message: str) -> dict:
        try:
            prompt = f"""
Analise a seguinte mensagem de um cliente e identifique:
1. intent: a intenção principal (greeting, product_search, order_status, registration, help, checkout, delivery, hours, contact, unknown)
2. entities: entidades mencionadas (nomes de produtos, números, etc)
3. sentiment: sentimento (positive, negative, neutral)

Mensagem: "{message}"

Responda APENAS em JSON no formato:
{{"intent": "...", "entities": [...], "sentiment": "..."}}
"""

            response = self.client.models.generate_content(
                model=self.model,
                contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
                config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=200)
            )

            if response and response.text:
                import json
                text = response.text.strip()
                if text.startswith('```'):
                    text = text.split('\n', 1)[1].rsplit('\n', 1)[0]
                return json.loads(text)

        except Exception as e:
            print(f"Intent analysis error: {e}")

        return {"intent": "unknown", "entities": [], "sentiment": "neutral"}