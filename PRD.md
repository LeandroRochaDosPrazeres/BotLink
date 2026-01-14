Analise e entenda 100% meu Markdown e melhore se necessário


# Product Requirement Document (PRD): BOTLink

| Metadado | Detalhe |
| :--- | :--- |
| **Projeto** | BOTLink - Automação Cognitiva de Candidaturas |
| **Versão** | 3.1.0 (Roadmap Completo Incluído) |
| **Status** | Especificação Aprovada para Desenvolvimento |
| **Data** | 14 de Janeiro de 2026 |
| **Stack Principal** | Python, Playwright (Camoufox), OpenAI (GPT-4o), SQLite |
| **Arquitetura** | Desktop Local-First (Segurança de IP) |

---

## 1. Introdução e Visão Estratégica
O **BOTLink** é um agente de software autônomo projetado para o ecossistema de recrutamento de 2026. Em um cenário onde "Candidaturas Simplificadas" (Easy Apply) geram volume massivo e bloqueios algorítmicos, a automação convencional (scripts lineares) tornou-se obsoleta e perigosa.

O BOTLink adota a **Automação Cognitiva**: um sistema capaz de navegar furtivamente (evitando detecção), interpretar semanticamente requisitos de vagas (via LLMs) e adaptar respostas com base em um perfil profissional estruturado, operando de forma indistinguível de um operador humano.

### 1.1 Declaração do Problema
1.  **Fricção:** Profissionais gastam horas repetindo dados em formulários idênticos.
2.  **Bloqueio:** Bots rápidos (spam) são banidos instantaneamente pelo LinkedIn.
3.  **Complexidade:** Scripts simples falham em perguntas abertas ("Descreva um projeto desafiador").

### 1.2 Solução Proposta
Uma aplicação desktop que gerencia a candidatura de ponta a ponta, respeitando limites estritos de volume (Rate Limiting) e utilizando IA para preenchimento contextual.

---

## 2. Decisões de Arquitetura e Stack Tecnológica

A escolha da tecnologia é fundamentada na necessidade de **Furtividade (Stealth)** e **Processamento de Dados**.

| Componente | Tecnologia Escolhida | Justificativa Técnica |
| :--- | :--- | :--- |
| **Linguagem** | **Python 3.10+** | Ecossistema nativo de IA/Data Science. Superior ao Node.js para parsing de PDF e integração com LLMs. |
| **Browser** | **Camoufox** | Fork do Firefox com patches em C++ para evasão de fingerprinting (User-Agent, WebGL, Canvas). Muito superior ao Selenium. |
| **Driver** | **Playwright** | Comunicação via WebSocket (rápida), suporte a *Shadow DOM* (usado pelo LinkedIn) e seletores robustos. |
| **IA / LLM** | **OpenAI API (GPT-4o)** | Capacidade de *Structured Outputs* (JSON Mode) essencial para mapear respostas a inputs HTML. |
| **Database** | **SQLite** | Zero-config, transacional, ideal para armazenamento local de logs e estado. |

---

## 3. Escopo do Produto

### 3.1 In-Scope (MVP)
* Interface Gráfica (GUI) Desktop (Sugestão: Flet ou CustomTkinter).
* Motor de navegação autônoma para vagas "Easy Apply".
* Parsing inteligente de currículo e cartas de apresentação.
* Sistema de segurança operacional (OpSec) com limites diários.
* Logs detalhados e auditoria de respostas da IA.

### 3.2 Out-of-Scope (Fase 1)
* Versão Web/SaaS (Risco de IP compartilhado).
* Solução automática de CAPTCHA (O usuário resolve manualmente se necessário).
* Automação de Networking (DMs, Conexões).

---

## 4. Requisitos de Interface (Front-End)

A interface deve ser minimalista, desacoplada da lógica e suportar temas visuais.

### 4.1 Configuração da Candidatura
* **[FE-01] Painel de Vagas:**
    * **Cargo(s):** Input de tags múltiplas (ex: `[Backend Python]`, `[DevOps]`).
    * **Localidade:** Input de texto (Cidade, Estado, País).
    * **Filtros:** Checkbox para `[x] Apenas Remoto`.
* **[FE-02] Credenciais & Sessão:**
    * Campos para Login/Senha (criptografados localmente).
    * Botão "Verificar Sessão" (para testar cookies existentes sem login).

### 4.2 Contexto do Candidato (Knowledge Base)
* **[FE-03] Upload de Currículo:**
    * Botão para anexar PDF/DOCX. O sistema deve extrair o texto para memória.
* **[FE-04] Perfil Estendido:**
    * **Resumo/Bio:** Área de texto grande para colar Carta de Apresentação e lista de projetos.
    * **Anexos Extras:** Lista para adicionar arquivos suplementares (Portfólio, Certificados) caso solicitados.

### 4.3 Controle e Monitoramento
* **[FE-05] Comandos:**
    * Botão `Iniciar BOT` (Verde).
    * Botão `Parar BOT` (Vermelho - Graceful Shutdown).
* **[FE-06] Dashboard de Logs:**
    * Tabela (Data Grid) com colunas: *Empresa, Vaga, Data, Status, Detalhes*.
    * Botão `Atualizar Log` (Refresh).
    * Ao clicar em falha, exibir modal com o motivo ou resposta da IA.
* **[FE-07] Personalização:**
    * Toggle Switch: **Dark Mode** / **Light Mode**.

---

## 5. Requisitos Funcionais (Back-End)

### 5.1 Motor de Navegação (Stealth)
* **[BE-01] Gestão de Cookies:** O sistema deve salvar `auth.json` após o primeiro login. Nas execuções seguintes, injeta os cookies para evitar telas de login.
* **[BE-02] Simulação Humana:**
    * Movimento do mouse via Curvas de Bezier.
    * Scroll aleatório na página da vaga antes de aplicar.
* **[BE-03] Upload Invisível:** Detectar `input[type='file']` ocultos e injetar o caminho do arquivo sem abrir janela do sistema operacional.

### 5.2 Motor Cognitivo (IA)
* **[BE-04] Parsing de Perguntas:** Extrair o texto da pergunta (`label`) e as opções disponíveis (`radio`, `select`).
* **[BE-05] Engenharia de Prompt:** Construir prompt contendo:
    * Contexto do Currículo + Bio.
    * Pergunta da vaga.
    * Restrições (ex: "Responda apenas com um número").
* **[BE-06] Saída JSON:** Forçar a resposta da IA em formato JSON estrito para garantir integração com o código Python.

### 5.3 Persistência
* **[BE-07] Banco de Dados:** Utilizar SQLite. Garantir unicidade de candidatura via `job_id` do LinkedIn.

---

## 6. Requisitos Não-Funcionais (OpSec & Segurança)

**Crítico:** O LinkedIn impõe limites rígidos. O desrespeito a estas regras causará bloqueio da conta.

| ID | Regra | Implementação Técnica |
| :--- | :--- | :--- |
| **RNF-01** | **Limite Diário (Hard Cap)** | O bot deve parar automaticamente ao atingir **40 a 50 candidaturas** em 24h. |
| **RNF-02** | **Warm-up de Conta** | Contas novas no bot devem seguir rampa: Dia 1 (10), Dia 2 (20), Dia 3 (30), Dia 4+ (40). |
| **RNF-03** | **Atrasos Aleatórios** | Entre cada ação (clique/digitação), aguardar `random(1.5, 4.0)` segundos. Entre candidaturas, aguardar `random(120, 600)` segundos. |
| **RNF-04** | **Jornada de Trabalho** | O bot deve pausar por 15-30 minutos a cada 10 candidaturas processadas. |
| **RNF-05** | **Tratamento de Erros** | Se houver 3 erros de "Elemento não encontrado" consecutivos, abortar sessão (possível mudança de layout ou soft-ban). |

---

## 7. Modelo de Dados (Schema SQLite)

```sql
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE candidaturas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT UNIQUE,            -- ID da vaga (ex: 37481923)
    empresa TEXT,
    titulo TEXT,
    localizacao TEXT,
    data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT CHECK(status IN ('SUCESSO', 'FALHA', 'PULADO')),
    motivo_log TEXT,               -- Ex: "IA respondeu X", "Erro de Timeout"
    tokens_ia INTEGER              -- Para controle de custo da API
);

CREATE TABLE estatisticas_diarias (
    data DATE PRIMARY KEY,
    quantidade INTEGER DEFAULT 0
);