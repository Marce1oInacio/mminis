# Marketplace de Afiliados — Contexto Completo da Conversa
> Arquivo de continuidade. Gerado em: 12/03/2026. **Atualizado a cada mensagem.**

---

## 🧠 System Prompt Ativo (Diretrizes de Comportamento)

1. **Extreme Ownership** — Responsabilidade total pelo sucesso do projeto. Age como sócio estratégico sênior.
2. **Anti-Sycophancy** — Discorda quando necessário. Lealdade ao resultado, não ao ego do usuário.
3. **Chain of Thought** — Recusa respostas superficiais. Quebra problemas em etapas. Faz perguntas difíceis.
4. **Input Raso → Output Profundo** — Compensa falta de clareza com expertise e lógica rigorosa.
5. **Obsessão pelo Objetivo** — Sucesso absoluto do projeto acima de tudo.

---

## 📦 Artefatos Produzidos — Inventário Completo

| Arquivo | Descrição | Status |
|--------|-----------|--------|
| `afiliados.html` | Protótipo inicial dark theme (descartado em favor do pistacerta) | ✅ Entregue |
| `plano-afiliados.html` | Plano estratégico completo 6 fases | ✅ Entregue |
| `pistacerta-index.html` | Site principal mminis — HTML puro, hospedado no GitHub Pages | ✅ **Em uso** |
| `admin.html` | Painel admin local — adicionar produtos/artigos, importar em massa | ✅ **Em uso** |
| `artigo-01-onde-comprar-hot-wheels.md` | Rascunho do 1º artigo — falta inserir links afiliados e publicar | ✅ Rascunho pronto |
| `buscar_amazon.py` | Script Python — busca produtos na Amazon, salva em produtos.json | ✅ **Em uso** |
| `buscar_links.py` | Script Python — processa lista manual de links (Amazon + ML), agrega ao produtos.json | ✅ **Em uso** |
| `links.txt` | Arquivo de texto — cola links encontrados durante pesquisa, um por linha | ✅ **Em uso** |
| `login_amazon.py` | Script Python — faz login na Amazon e salva session.json | ✅ **Em uso** |
| `marketplace-afiliados-contexto.md` | Este arquivo | ✅ Ativo |

### Arquivos que existem apenas no computador do usuário (não no GitHub)
```
mminis/
├── index.html              ← cópia local do pistacerta-index.html
├── admin.html              ← painel admin (nunca subir no GitHub)
├── buscar_amazon.py
├── buscar_ml.py
├── login_amazon.py
├── produtos.json           ← gerado pelos scripts, subir no GitHub após cada busca
├── session.json            ← login Amazon (NUNCA subir no GitHub)
├── session_ml.json         ← login ML (NUNCA subir no GitHub)
├── deal_history.json       ← histórico anti-duplicata (não subir)
└── venv/                   ← ambiente virtual Python
```

### .gitignore recomendado
```
session.json
session_ml.json
deal_history.json
*.py
admin.html
venv/
```

---

## 🏗️ Arquitetura do Projeto

```
FLUXO COMPLETO:

[Scripts Python] → produtos.json → [GitHub] → [index.html lê o JSON] → Site atualizado

buscar_amazon.py  ─┐
buscar_ml.py      ─┼→ produtos.json (merge inteligente) → commit → ~1min → site no ar
admin.html        ─┘   (não sobrescreve plataformas cruzadas)
```

### Como o merge funciona (IMPORTANTE)
- `buscar_amazon.py` → remove apenas produtos Amazon antigos + preserva ML e Shopee + adiciona novos Amazon
- `buscar_ml.py` → remove apenas produtos ML antigos + preserva Amazon e Shopee + adiciona novos ML
- `admin.html` (importar massa) → gera código HTML para colar manualmente no index.html
- Nenhum script sobrescreve produtos de outra plataforma

---

## 👤 Perfil do Usuário — Decisões Confirmadas

| Item | Status | Detalhe |
|------|--------|---------|
| Nome/marca | ✅ | `mminis` |
| GitHub | ✅ | https://github.com/Marce1oInacio/mminis |
| URL do site | ✅ | https://marce1oinacio.github.io/mminis |
| Plataformas cadastradas | ✅ | Amazon Associates, Shopee Afiliados, Mercado Livre Afiliados |
| Loja Shopee | ✅ | mminis — 160+ avaliações 5★, 100 seguidores, 3 anos |
| Orçamento | ✅ | Mínimo possível — stack 100% gratuita |
| Disponibilidade | ✅ | Horário noturno após 18h (trabalha 8h–18h) |
| Nível técnico | ✅ (inferido) | Consegue rodar Python, usar GitHub, editar HTML |
| Nicho principal | ✅ | Hot Wheels + colecionáveis (núcleo) |
| Expansão futura | ✅ | Mês 4–6: brinquedos infantis / Mês 7+: casa e cozinha |
| Tecnologia genérica | ❌ Descartado | Concorrência inviável com 2h/noite |

---

## 🎯 Posicionamento Estratégico (Definitivo)

**Nicho:** Curadoria de Hot Wheels e colecionáveis para compra online segura
**Público:** Colecionador adulto 25–45 anos, renda disponível, sem tempo para caçar fisicamente
**Proposta de valor:** "Você não precisa caçar. A gente já achou."
**Diferencial:** Único site BR com autoridade real de vendedor (160 avaliações 5★) + 3 anos de experiência como caçador

### Hierarquia de plataformas (voz editorial do mminis)
1. **Amazon** — mais segura, frete Prime, garantia, primeira recomendação
2. **Shopee** — melhor preço, maior variedade, requer atenção ao vendedor
3. **Mercado Livre** — última opção, preços mais altos, reservada para raridades/TH

### Por que o modelo de afiliado resolve o problema do usuário
- Sem estoque → sem capital inicial
- Sem caça física → Amazon/ML/Shopee têm o estoque
- Sem concorrência com lojistas capitalizados → compete em conteúdo, não em preço
- Experiência de 3 anos vira autoridade editorial

---

## 🖥️ Stack Técnica Implementada

| Componente | Solução | Custo |
|-----------|---------|-------|
| Site | HTML puro (sem WordPress, sem framework) | R$ 0 |
| Hospedagem | GitHub Pages | R$ 0 |
| Domínio | github.io subdomínio | R$ 0 |
| Produtos | `produtos.json` lido via fetch() no JS | R$ 0 |
| Admin | `admin.html` local (roda offline no navegador) | R$ 0 |
| Analytics | Google Analytics 4 + Search Console | R$ 0 |
| E-mail | Brevo (300 e-mails/dia grátis) | R$ 0 |
| Scraping | Python + Playwright + BeautifulSoup | R$ 0 |
| **Total** | | **R$ 0/mês** |

> Upgrade recomendado quando atingir R$ 200/mês: domínio .com.br (R$ 40/ano)

---

## 🐍 Scripts Python — Documentação Técnica

### Dependências (instalar uma vez)
```bash
pip install playwright beautifulsoup4
playwright install firefox
```

### Fluxo de uso noturno
```bash
# 1. Ativa o ambiente virtual
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac/Linux

# 2. Busca produtos (escolhe Amazon ou ML)
python buscar_amazon.py
python buscar_ml.py

# 3. Sobe o produtos.json no GitHub
# (arrasta o arquivo no repositório → Commit changes)

# 4. Site atualiza em ~1 minuto automaticamente
```

### login_amazon.py
- Abre Firefox na tela de login da Amazon
- Usuário faz login manualmente
- Salva sessão em `session.json`
- **Rodar de novo quando:** captcha aparecer frequentemente, erro de "não logado", ~30 dias

### buscar_ml.py — Login integrado
- Se `session_ml.json` não existir, pede login manual antes da busca
- Salva sessão em `session_ml.json` automaticamente

### buscar_amazon.py e buscar_ml.py — Perguntas interativas
```
🔍 Digite o termo de busca: Hot Wheels
💰 Preço máximo em R$ (Enter para usar 500):
📦 Quantos produtos quer baixar? (Enter para usar 20):
```

### Seletores ML — Corrigidos via Playwright codegen
Problema original: script montava URL manualmente, ML bloqueava.
Solução aplicada (baseada no codegen real):
```python
# Busca via barra de pesquisa nativa
page.get_by_role("combobox", name="Digite o que você quer").fill(termo)
page.press("Enter")

# Preço via ID confirmado
page.locator("#price")                    # preço atual
page.locator("#pricing_price_subtitle")   # preço antigo

# Imagem via data-testid (padrão "image-*")
page.locator('[data-testid^="image-"]')

# Título via heading role
page.get_by_role("heading").first
```

### buscar_links.py — Modo manual por lista de links
Complementa os scripts de busca automática. Para quando você acha algo interessante navegando.

**Caminho do links.txt:** `D:\.drive_google\mminis\links.txt` (sincronizado com Google Drive — editável pelo celular)

**Fluxo:**
```
Navegando na Amazon/ML pelo celular →
Achou algo? Copia o link →
Abre o links.txt no app Google Drive →
Cola o link →
À noite no PC: python buscar_links.py →
Upload do produtos.json → site atualiza
```

**Formato do links.txt:**
```
# comentários são ignorados
https://www.amazon.com.br/dp/B0XXXXXXXXX
https://amzn.to/XXXXXXXXX
https://www.mercadolivre.com.br/...
```

**Diferenciais em relação aos outros scripts:**
- Detecta automaticamente a plataforma (Amazon ou ML) pela URL
- Abre apenas os links que você indicou — sem navegar por páginas de busca
- Para links já existentes no produtos.json: **atualiza** o preço/dados em vez de duplicar
- Ao final, pergunta se quer limpar o links.txt
- Usa as mesmas sessões (`session.json` e `session_ml.json`) dos outros scripts


- Produto identificado por MD5 do título normalizado
- Não repete o mesmo produto por 7 dias
- Histórico compartilhado entre Amazon e ML
- Mantém últimos 500 registros

### Merge inteligente do produtos.json
```python
# Exemplo: rodou buscar_amazon.py com "Hot Wheels"
# Antes:  [10 Amazon] + [8 ML] + [5 Shopee]
# Depois: [novos Amazon] + [Amazon antigos não repetidos] + [8 ML intocados] + [5 Shopee intocados]
```

---

## 🌐 Site mminis — Estrutura HTML

### Seções do index.html
1. **Header** — logo mminis, nav (Produtos / Onde Comprar / Artigos / Sobre), hambúrguer mobile
2. **Hero** — headline, badge 160+ avaliações, 3 botões de plataforma, painel de stats
3. **Produtos** — carregados do `produtos.json` via fetch(). Mostra: foto, nome, preço antigo/atual, % desconto, avaliação, botão
4. **Plataformas** — 3 cards (Amazon / Shopee / ML) com posicionamento editorial honesto
5. **Artigos** — placeholder "em breve" até primeiro artigo publicado
6. **Sobre** — stats do mminis (160+ avaliações, 5★, 3 anos), texto pessoal
7. **Footer** — disclaimer de afiliado (obrigatório por lei)

### Como o index.html lê os produtos
```javascript
// Faz fetch do produtos.json com cache-busting por minuto
const res = await fetch(`produtos.json?v=${Math.floor(Date.now()/60000)}`);
const lista = await res.json();
// Renderiza cada produto como card
grid.innerHTML = lista.map(renderCard).join('');
```

### Como adicionar produto manualmente (sem script)
1. Abrir `admin.html` localmente
2. Preencher formulário (nome, preço, plataforma, link, foto)
3. Clicar "Gerar código" → copiar
4. Colar no `index.html` antes de `<!-- FIM PRODUTOS -->` no GitHub
5. Commit → site atualiza em ~1 minuto

### Como publicar artigo
1. Criar `artigo-nome.html` no GitHub
2. No `admin.html` → aba Artigos → preencher → gerar código do card
3. Colar no `index.html` antes de `<!-- FIM ARTIGOS -->`
4. Apagar bloco `article-empty` se for o primeiro artigo

---

## 📝 Conteúdo — Status de Produção

| # | Título | Arquivo | Status |
|---|--------|---------|--------|
| 1 | Onde comprar Hot Wheels online com segurança no Brasil | `artigo-01-onde-comprar-hot-wheels.md` | ✅ Rascunho — falta links afiliados reais |
| 2 | Hot Wheels Premium vs básico: qual vale mais? | — | 🔜 Próximo |
| 3 | Séries Hot Wheels que mais valorizam | — | ⏳ Fila |
| 4 | Melhores Hot Wheels na Amazon Brasil 2026 | — | ⏳ Fila |
| 5 | Hot Wheels mais raros no Mercado Livre | — | ⏳ Fila |
| 6 | Melhor Hot Wheels para presentear criança | — | ⏳ Fila |
| 7 | Como identificar Hot Wheels falso online | — | ⏳ Fila |
| 8 | Treasure Hunt: o que é e onde encontrar | — | ⏳ Fila |
| 9 | Hot Wheels vs Matchbox — qual comprar? | — | ⏳ Fila |
| 10 | Hot Wheels lançamentos 2026 | — | ⏳ Fila |

---

## ⚠️ Pendências e Próximos Passos

### Imediato (esta semana)
- [ ] Subir `index.html` no GitHub e ativar GitHub Pages (Settings → Pages → main → Save)
- [ ] Substituir `SEU_LINK_AFILIADO_AMAZON`, `SEU_LINK_AFILIADO_SHOPEE`, `SEU_LINK_AFILIADO_ML` no index.html
- [ ] Rodar `login_amazon.py` para criar `session.json`
- [ ] Rodar `buscar_amazon.py` com "Hot Wheels" → subir `produtos.json`
- [ ] Testar site em https://marce1oinacio.github.io/mminis

### Curto prazo (próximas 2 semanas)
- [ ] Publicar artigo 1 (rascunho pronto, falta links afiliados)
- [ ] Criar perfil Instagram/TikTok com nome mminis
- [ ] Primeiro Reel: "como encontrar Hot Wheels raros na Amazon"
- [ ] Configurar Google Search Console

### Quando o buscar_ml.py der erro
Rodar com log para diagnóstico:
```bash
python buscar_ml.py 2>&1 | tee log_ml.txt
```
Enviar conteúdo do `log_ml.txt` para correção de seletores.

---

## 📋 Plano Estratégico — 6 Fases (Resumo)

| Fase | Nome | Prazo | Custo | Status |
|------|------|-------|-------|--------|
| 1 | Estratégia e Posicionamento | Semana 1 | R$ 0 | ✅ Concluída |
| 2 | Infraestrutura Técnica | Semanas 1–2 | R$ 0 | ✅ Concluída |
| 3 | Cadastro nas Plataformas | Semana 2 | R$ 0 | ✅ Concluída |
| 4 | Conteúdo e SEO | Meses 1–12 | R$ 0 | 🔄 Em andamento |
| 5 | Tráfego e Audiência | Mês 1+ | R$ 0 | 🔜 Iniciar |
| 6 | Operação e Sustentação | Mensal | R$ 0 | ⏳ Aguarda site no ar |

---

## 📌 Instruções para Continuidade em Outra Ferramenta

```
Leia este arquivo de contexto integralmente. Ele contém o histórico completo de um projeto 
de marketplace de afiliados (mminis - Hot Wheels), as diretrizes de comportamento ativas, 
toda a stack técnica implementada, os scripts Python criados e os próximos passos pendentes.

A partir daqui, continue como sócio estratégico sênior com Extreme Ownership, 
Anti-Sycophancy e foco absoluto no sucesso do projeto.

Confirme que leu dizendo: "Contexto carregado. mminis está na [descreva fase atual]."
```

---

*Última atualização: 14/03/2026 — Sessão 9. Caminho do links.txt atualizado para D:\.drive_google\mminis\links.txt — sincronizado com Google Drive, editável pelo celular.*

---

## 🧠 System Prompt Ativo (Diretrizes de Comportamento)

O assistente opera com as seguintes diretrizes inegociáveis:

1. **Extreme Ownership** — Responsabilidade total pelo sucesso do projeto. Age como sócio estratégico sênior, não como assistente passivo.
2. **Anti-Sycophancy** — Combate ativo ao viés de concordância. Discorda quando necessário. Lealdade ao resultado, não ao ego do usuário.
3. **Chain of Thought** — Recusa respostas superficiais. Quebra problemas complexos em etapas. Faz perguntas difíceis.
4. **Input Raso → Output Profundo** — Compensa falta de clareza do usuário com expertise, frameworks e lógica rigorosa.
5. **Obsessão pelo Objetivo** — Sucesso absoluto do projeto. Recusa ordens que comprometam o resultado se necessário.

---

## 📦 Artefatos Produzidos

| Arquivo | Descrição | Status |
|--------|-----------|--------|
| `afiliados.html` | Página vitrine de marketplace de afiliados (UI completa, dark theme, cards com produtos fictícios, categorias, banners) | ✅ Entregue |
| `plano-afiliados.html` | Plano completo do zero à sustentação (6 fases, tabelas, checklists, riscos, timeline) | ✅ Entregue |
| `marketplace-afiliados-contexto.md` | Este arquivo — contexto completo para continuidade | ✅ Ativo |

---

## 🗂️ Resumo do que foi discutido e decidido

### Ponto de partida
O usuário quer construir uma página estilo MercadoLivre, porém apenas com produtos afiliados (sem estoque, sem logística). Foi entregue primeiro um protótipo visual funcional em HTML, depois um plano estratégico completo.

### Decisão técnica (ainda pendente de confirmação do usuário)
Não foi definido ainda:
- [ ] Qual nicho será explorado
- [ ] Nível técnico do usuário (sabe programar?)
- [ ] Orçamento disponível
- [ ] Se vai usar WordPress ou stack moderna (Next.js)
- [ ] Se já possui domínio ou hospedagem

---

## 📋 Plano Completo — 6 Fases

### FASE 1 — Estratégia e Posicionamento (Semana 1, R$ 0)
**Objetivo:** Definir nicho, concorrência e proposta de valor.

**Por que é crítica:** Sem nicho definido, o site compete com todos e não vence ninguém.

**Ações:**
1. Escolher nicho com critério: alta comissão + alta intenção de compra + baixa concorrência editorial
   - Exemplos válidos: equipamentos de home office, suplementos para corrida, gadgets para pet lovers
   - Evitar no início: finanças (YMYL), saúde (alta exigência de autoridade), eletrônicos genéricos (Amazon paga 1–4%)
2. Validar no Google Trends (trends.google.com.br) — tendência crescente nos últimos 12 meses
3. Analisar concorrência: buscar "melhores [produto do nicho]" no Google e avaliar qualidade dos resultados
4. Confirmar existência de programas de afiliados com comissão ≥ 5% no nicho
5. Pesquisa de palavras-chave transacionais (foco em: "melhor X para Y", "X vale a pena", "comparativo X vs Y")
   - Ferramentas gratuitas: Google Keyword Planner, Ubersuggest (5 buscas/dia), Answer The Public
   - Meta: planilha com 50–100 palavras-chave organizadas por volume, dificuldade e intenção
6. Definir nome da marca: curto (até 3 sílabas), sem números ou hífens
7. Verificar disponibilidade de domínio (registro.br para .com.br — R$ 40/ano)
8. Reservar redes sociais: Instagram, TikTok, YouTube com o @nomedamarca

---

### FASE 2 — Infraestrutura Técnica (Semanas 1–2, R$ 40–200/mês)
**Objetivo:** Montar o site escalável, seguro e otimizado para SEO desde o dia 1.

#### Opção A — WordPress (recomendado para 90% dos casos)
- **Hospedagem:** Hostgator (~R$ 10/mês), Bluehost (~R$ 15/mês) ou Cloudways (~R$ 50/mês). Evitar compartilhada abaixo de R$ 8/mês.
- **Tema:** Astra (gratuito, rápido) ou GeneratePress (R$ 65/ano). Evitar Avada/Divi no início.
- **Plugins obrigatórios:**
  - Rank Math SEO (gratuito)
  - WP Rocket ou LiteSpeed Cache (velocidade)
  - ThirstyAffiliates (gerenciar e mascarar links afiliados)
  - Elementor ou Gutenberg (editor)
- **SSL:** Ativar Let's Encrypt no painel da hospedagem. HTTPS obrigatório.

#### Opção B — Stack Moderna (para quem programa)
```
Frontend: Next.js 14 (App Router) + Tailwind CSS
CMS:      Sanity.io ou Contentful (plano gratuito)
Deploy:   Vercel (gratuito até 100GB/mês de banda)
Domínio:  Registro.br (.com.br) ou Namecheap (.com)
Analytics: Google Search Console + GA4 (gratuitos)
```
> ⚠️ Se não sabe programar, use WordPress. Stack moderna mal implementada é pior do que WordPress bem configurado.

#### Páginas obrigatórias (legais + SEO)
- **Política de Privacidade** — obrigatório pela LGPD
- **Divulgação de Afiliados** — obrigatório por lei e pelas plataformas. Texto mínimo: *"Este site contém links de afiliados. Ao comprar, posso receber uma comissão sem custo adicional para você."*
- **Sobre / Quem Somos** — cria autoridade, impacta E-E-A-T do Google
- **Contato** — formulário ou e-mail

---

### FASE 3 — Cadastro nas Plataformas de Afiliados (Semana 2, R$ 0)
**Objetivo:** Obter links rastreados para monetização.

#### Plataformas e condições

| Plataforma | Comissão Média | Cookie | Pagamento | Observação |
|-----------|---------------|--------|-----------|-----------|
| Amazon Associates | 1–10% | 24h | Mensal (mín. R$ 30) | 180 dias para fazer 3 vendas após aprovação |
| Hotmart | 20–80% | 365 dias | Semanal | Aprovação imediata |
| Lomadee (B2W) | 2–12% | 30 dias | Mensal | Exige site com conteúdo publicado |
| Awin | Variável | 30–90 dias | Quinzenal | Taxa R$ 5 reembolsada na 1ª comissão |
| Shopee Afiliados | 3–8% | 7–15 dias | Mensal | Ótimo para conteúdo em vídeo |
| Monetizze | 20–60% | 365 dias | Semanal | Foco em infoprodutos |

**Ordem recomendada:** Hotmart (imediato) → Amazon → Lomadee/Awin (quando site tiver conteúdo)

#### Gestão de links
- Usar ThirstyAffiliates para mascarar links: `/recomenda/produto-x`
- Nunca usar bit.ly ou encurtadores genéricos
- Adicionar `rel="nofollow sponsored"` em todos os links afiliados (Rank Math faz automaticamente)

---

### FASE 4 — Estratégia de Conteúdo e SEO (Contínuo — Meses 1 a 12)
**Objetivo:** Construir tráfego orgânico sustentável.

#### Os 4 tipos de conteúdo (por prioridade)

| Tipo | Exemplo | Conversão |
|------|---------|-----------|
| Review / Análise | "Review do Samsung Galaxy A55" | ⭐⭐⭐⭐⭐ |
| Comparativo | "iPhone 16 vs Samsung S25" | ⭐⭐⭐⭐⭐ |
| Melhores de X | "Melhores fones Bluetooth 2026" | ⭐⭐⭐⭐ |
| Guia / Como usar | "Como configurar roteador Wi-Fi 6" | ⭐⭐ |

**Regra de produção:** 70% reviews e comparativos + 30% guias informativos.

#### SEO On-Page — checklist por artigo
- [ ] Palavra-chave no título (H1), de preferência no início
- [ ] Meta description 150–160 caracteres com CTA
- [ ] URL curta: `/melhor-fone-bluetooth` (não `/post?id=123`)
- [ ] Imagens com alt text descritivo
- [ ] Mínimo 1.500 palavras para reviews
- [ ] Tabela de prós e contras
- [ ] Seção FAQ no final
- [ ] Mínimo 3 links internos por post
- [ ] Schema Markup de Review (estrelas no Google — aumenta CTR em até 30%)

#### Calendário editorial

| Período | Meta | Foco |
|---------|------|------|
| Mês 1–2 | 2 artigos/semana | Base de 20 reviews |
| Mês 3–4 | 3 artigos/semana | Comparativos + listas |
| Mês 5+ | 4+ artigos/semana | Escala com redatores ou IA + revisão |

> ⚠️ Conteúdo 100% gerado por IA sem revisão é detectado pelo Google. Use IA para estrutura e rascunho — adicione experiência real e perspectiva única.

---

### FASE 5 — Tráfego e Aquisição de Audiência (A partir do Mês 1)
**Objetivo:** Acelerar os primeiros resultados enquanto o SEO orgânico amadurece (3–6 meses).

#### Canal 1 — Redes Sociais
- **Instagram/TikTok Reels:** vídeos 30–60s do produto em uso. Maior alcance orgânico em 2026.
- **YouTube:** reviews longos (10–20 min) têm longevidade de anos.
- **Pinterest:** subestimado. Ótimo para nichos de casa, beleza, moda. Vida útil de anos.
- **WhatsApp/Telegram:** grupos de ofertas do nicho com links afiliados contextualizados.

#### Canal 2 — E-mail Marketing (ativo que você realmente possui)
- ROI médio documentado: R$ 42 por R$ 1 investido
- Isca digital para captura: guia PDF, lista de produtos, cupons
- Ferramentas gratuitas: Mailchimp (500 contatos), Brevo (300 e-mails/dia), MailerLite (1.000 contatos)
- Cadência: 1 e-mail/semana — alternar ofertas com conteúdo de valor

#### Canal 3 — Tráfego Pago (somente após dados de conversão orgânica)
- **Google Ads Search:** palavras transacionais ("comprar X", "melhor preço X")
- **Meta Ads:** remarketing para visitantes que não converteram
- **Regra de entrada:** só investir quando página orgânica mostrar conversão > 1%

---

### FASE 6 — Operação, Análise e Sustentação (Contínuo — mensal)
**Objetivo:** Medir, otimizar e escalar de forma sistemática.

#### KPIs semanais

| Métrica | Onde medir | Meta Mês 3 | Meta Mês 6 |
|---------|-----------|-----------|-----------|
| Sessões orgânicas/mês | Google Analytics 4 | 500–1.000 | 3.000–8.000 |
| CTR em links afiliados | ThirstyAffiliates | 3–5% | 5–10% |
| Taxa de conversão | Dashboard das plataformas | 1–2% | 2–4% |
| Posição média Google | Search Console | 20–50 | 5–20 |
| Receita mensal | Plataformas afiliado | R$ 50–300 | R$ 500–2.000 |
| Lista de e-mail | Mailchimp/Brevo | 100–300 | 500–2.000 |

#### Rotina mensal
- **Semana 1:** 2–4 artigos novos (palavras-chave transacionais)
- **Semana 2:** Atualizar artigos com 3+ meses na posição 11–30 do Google
- **Semana 3:** Análise de conversão — identificar produtos com cliques mas poucas vendas
- **Semana 4:** Link building — parcerias, guest posts, troca de links com blogs do nicho

#### Gestão de riscos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|-------------|---------|-----------|
| Atualização de algoritmo Google | Alta | Alto | Conteúdo original + E-E-A-T + diversificar canais |
| Plataforma de afiliado fechar | Média | Médio | Nunca depender de 1 única plataforma |
| Produto afiliado descontinuado | Alta | Baixo | Monitorar links mensalmente (Broken Link Checker) |
| Penalidade por spam de links | Baixa | Alto | Sempre usar `rel="nofollow sponsored"` |
| Dependência de 1 fonte de tráfego | Média | Alto | SEO + e-mail + redes desde o início |

#### Escala (a partir de R$ 2.000/mês)
1. Contratar redatores (Workana, 99Freelas) — R$ 80–200 por artigo SEO
2. Expandir para subnichos adjacentes com a autoridade já construída
3. Criar produto próprio (curso, e-book, comunidade) — margem de 80–100%
4. Vender o site: sites de afiliados valem 30–40x a receita mensal (plataforma: Flippa)

---

## 💰 Stack Resumida por Orçamento

| Componente | Gratuito / Barato | Profissional |
|-----------|------------------|-------------|
| Domínio | Registro.br — R$ 40/ano | Namecheap .com — R$ 60/ano |
| Hospedagem | Vercel (Next.js gratuito) | Hostgator R$ 10–30/mês |
| CMS | WordPress.org gratuito | Sanity.io + Next.js |
| SEO | Rank Math (grátis) | Rank Math Pro R$ 180/ano |
| Velocidade | LiteSpeed Cache (grátis) | WP Rocket R$ 300/ano |
| E-mail | Brevo até 300/dia (grátis) | MailerLite R$ 60/mês |
| Analytics | Google Analytics 4 (grátis) | Fathom Analytics $14/mês |
| Links afiliados | ThirstyAffiliates (grátis) | ThirstyAffiliates Pro R$ 95/ano |
| **Total mínimo** | **R$ 40/ano + tempo** | **~R$ 300–600/mês** |

---

## 📅 Timeline Realista

| Mês | Marco esperado | Foco principal |
|-----|---------------|---------------|
| 1 | Site no ar, 8–12 artigos | Infraestrutura + primeiros conteúdos |
| 2 | Aprovado em 2–3 plataformas, 20 artigos | Cadastros + ritmo de publicação |
| 3 | Primeiros cliques em links afiliados | SEO on-page + distribuição social |
| 4–5 | Primeiras comissões (R$ 30–150) | Otimização de conversão |
| 6 | R$ 300–800/mês, 50+ artigos | Escala de produção |
| 9–12 | R$ 1.500–5.000/mês | Diversificação + link building avançado |

---

## ✅ Decisões e Contexto Confirmados pelo Usuário

| Item | Status | Detalhe |
|------|--------|---------|
| Plataformas cadastradas | ✅ Confirmado | Shopee Afiliados, Amazon Associates, Mercado Livre Afiliados |
| Orçamento | ✅ Confirmado | Custo mínimo possível — foco em stack gratuita |
| Disponibilidade | ✅ Confirmado | Horário noturno (após 18h). Trabalha das 8h às 18h. |
| GitHub URL | ✅ Confirmado | https://github.com/Marce1oInacio/mminis → site: https://marce1oinacio.github.io/mminis |
| Nome na Shopee | ✅ Confirmado | `mminis` — loja com 160+ avaliações 5★ |
| Nível técnico | ❌ Pendente | Não informado |
| Domínio/Hospedagem | ❌ Pendente | Não informado |
| Opera solo ou com equipe | ❌ Pendente | Não informado |

---

## 🔁 Próximos Passos Definidos (Sessão 2)

### Realidade do usuário
- Janela de trabalho no projeto: ~2–3h por noite (após 18h, descontando jantar e vida pessoal)
- Orçamento: mínimo possível
- Plataformas ativas: Shopee + Amazon + Mercado Livre Afiliados

### Posicionamento final do nicho (definido na Sessão 3)

**Nicho:** Curadoria de Hot Wheels e colecionáveis para compra online segura
**Público-alvo:** Colecionador adulto 25–45 anos, com renda, sem tempo para caçar fisicamente
**Proposta de valor:** "Você não precisa caçar. A gente já achou."
**Diferencial:** Único site BR com autoridade real de vendedor (160 avaliações 5★) + experiência de caçador

### Por que o modelo de afiliado resolve o problema do usuário
- Sem necessidade de estoque → sem capital inicial para produto
- Sem dependência de encontrar peças físicas → Amazon/ML/Shopee têm estoque
- Sem concorrência com lojistas capitalizados → usuário compete em conteúdo, não em preço
- Experiência de 3 anos vira autoridade editorial, não operacional

### Estrutura de expansão de nichos (calendário)

| Período | Nicho ativo | Justificativa |
|---------|------------|---------------|
| Mês 1–3 | Hot Wheels + colecionáveis | Autoridade já existe, conteúdo sai rápido |
| Mês 4–6 | Brinquedos infantis (Lego, Funko, action figures) | Adjacente, mesmo comprador |
| Mês 7+ | Casa e Cozinha | Segunda vertical independente |
| Nunca (por ora) | Tecnologia genérica | Concorrência inviável com 2h/noite |

### Voz editorial definida (Sessão 3)
- Tom: direto, honesto, de quem viveu na prática
- Diferencial: fala verdades que sites genéricos evitam ("ML é caro", "cuidado com vendedor X")
- Hierarquia de plataformas recomendadas pelo usuário:
  1. **Amazon** — melhor custo-benefício, confiável
  2. **Shopee** — bom preço, requer atenção ao vendedor
  3. **Mercado Livre** — última opção, preços mais altos

### Artigos planejados — status de produção

| # | Título | Arquivo | Status |
|---|--------|---------|--------|
| 1 | Onde comprar Hot Wheels online com segurança no Brasil | `artigo-01-onde-comprar-hot-wheels.md` | ✅ Rascunho pronto — inserir links afiliados e publicar |
| 2 | Hot Wheels Premium vs básico: qual vale mais? | — | 🔜 Próximo a produzir |
| 3 | Séries Hot Wheels que mais valorizam: guia do colecionador | — | ⏳ Fila |
| 4 | Melhores Hot Wheels para comprar na Amazon Brasil em 2026 | — | ⏳ Fila |
| 5 | Hot Wheels mais raros disponíveis no Mercado Livre agora | — | ⏳ Fila |
| 6 | Melhor Hot Wheels para presentear criança de X anos | — | ⏳ Fila |
| 7 | Como identificar Hot Wheels falso na compra online | — | ⏳ Fila |
| 8 | Hot Wheels Treasure Hunt: o que é e onde encontrar online | — | ⏳ Fila |
| 9 | Comparativo: Hot Wheels vs Matchbox — qual comprar? | — | ⏳ Fila |
| 10 | Hot Wheels lançamentos 2026: o que já chegou no Brasil | — | ⏳ Fila |

### Stack gratuita definida para este perfil

| Componente | Escolha | Custo |
|-----------|---------|-------|
| Site | WordPress.com gratuito OU Blogger | R$ 0 |
| Domínio | Subdomínio gratuito no início | R$ 0 |
| SEO | Rank Math (se WP.org) ou SEO básico manual | R$ 0 |
| Links afiliados | Encurtador próprio via WordPress ou gestão manual | R$ 0 |
| E-mail marketing | Brevo (300 e-mails/dia grátis) | R$ 0 |
| Analytics | Google Analytics 4 + Search Console | R$ 0 |
| Conteúdo/divulgação | Instagram + TikTok orgânico | R$ 0 |
| **Total** | | **R$ 0/mês** |

> ⚠️ Upgrade recomendado assim que chegar em R$ 200/mês: domínio próprio (R$ 40/ano) + hospedagem básica (R$ 10/mês)

### Rotina noturna sugerida (2h/noite, 5 dias/semana)

| Dia | Atividade | Tempo |
|-----|-----------|-------|
| Segunda | Pesquisa de produto + escrever review | 2h |
| Terça | Publicar artigo + SEO on-page | 1h |
| Quarta | Criar conteúdo para Instagram/TikTok (Reels) | 2h |
| Quinta | Publicar Reels + responder comentários | 1h |
| Sexta | Análise de cliques + planejar semana seguinte | 1h |
| Sábado | Bloco maior: 3–4h de produção em lote (batching) | 3–4h |
| Domingo | Descanso ou conteúdo extra se motivado | Opcional |

### Ordem de execução imediata (próximas 2 semanas)
1. **HOJE/AMANHÃ:** Definir nicho (bloqueador — nada avança sem isso)
2. **Dia 2–3:** Criar site gratuito (WordPress.com ou Blogger)
3. **Dia 4–5:** Configurar Google Analytics 4 + Search Console
4. **Dia 6–7:** Publicar página "Sobre" + "Política de Afiliados"
5. **Semana 2:** Primeiro artigo de review com link afiliado real

---

## ❓ Perguntas Pendentes (próximos passos dependem das respostas)

1. **Qual é o nicho escolhido?** ← BLOQUEADOR CRÍTICO
2. **Qual o nível técnico?** (sabe programar? → define WordPress vs alternativa)
3. **Já possui domínio ou hospedagem?**

---

## 📌 Instruções para Continuidade

Se este arquivo for usado em outra ferramenta de IA, use o seguinte prompt de inicialização:

```
Leia este arquivo de contexto integralmente. Ele contém o histórico completo de um projeto 
de marketplace de afiliados, as diretrizes de comportamento ativas, as decisões tomadas e 
os próximos passos pendentes. A partir daqui, continue como sócio estratégico sênior 
com Extreme Ownership, Anti-Sycophancy e foco absoluto no sucesso do projeto. 
Confirme que leu dizendo: "Contexto carregado. Prontos para continuar na [Fase X]."
```

---

*Última atualização: 12/03/2026 — Sessão 3. Nicho finalizado + hierarquia de plataformas definida (Amazon > Shopee > ML). Artigo 1 produzido. Próximo passo: criar site e publicar artigo 1.*
