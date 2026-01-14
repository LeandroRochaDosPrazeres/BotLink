# BOTLink - Automação Cognitiva de Candidaturas

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-Latest-green?logo=playwright&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-purple?logo=openai&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

**Agente autônomo para automação de candidaturas no LinkedIn com IA**

</div>

---

## 🎯 O que é o BOTLink?

O BOTLink é um sistema de **Automação Cognitiva** que:
- 🤖 Navega furtivamente pelo LinkedIn evitando detecção
- 🧠 Usa GPT-4o para responder perguntas de candidatura
- 📄 Extrai informações do seu currículo automaticamente
- 🛡️ Respeita limites rígidos para evitar bloqueios

## 🚀 Instalação

### Pré-requisitos

- Python 3.10 ou superior
- Conta no LinkedIn
- API Key do OpenAI (GPT-4o)

### Passos

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/botlink.git
cd botlink

# Crie um ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Instale as dependências
pip install -r requirements.txt

# Instale os navegadores do Playwright
playwright install firefox

# Configure as variáveis de ambiente
cp .env.example .env
# Edite .env e adicione sua OPENAI_API_KEY
```

## 📋 Uso

### Executando a GUI

```bash
python -m src.main
```

### Configuração Inicial

**Acesse no navegador:** `http://localhost:8553`

1. **Upload de Currículo**: Carregue seu CV (PDF ou DOCX)
2. **Credenciais**: Configure seu login do LinkedIn
3. **Filtros**: Defina os cargos e localização desejados
4. **Iniciar**: Clique em "Iniciar BOT"

## ⚙️ OpSec (Segurança Operacional)

O BOTLink implementa medidas rigorosas para evitar bloqueios:

| Regra | Descrição |
|-------|-----------|
| **Limite Diário** | Máximo 40-50 candidaturas por dia |
| **Warm-up** | Contas novas: 10 → 20 → 30 → 40/dia |
| **Delays** | 1.5-4.0s entre ações, 2-10min entre candidaturas |
| **Pausas** | 15-30min a cada 10 candidaturas |
| **Abort** | Para após 3 erros consecutivos |

## 🏗️ Arquitetura

```
src/
├── domain/          # Entidades e lógica de negócio
├── application/     # Casos de uso
├── infrastructure/  # Adaptadores (Browser, AI, DB)
└── presentation/    # GUI (Flet)
```

Seguindo **Clean Architecture** com separação clara de responsabilidades.

## 🧪 Testes

```bash
# Rodar todos os testes
python -m pytest tests/ -v

# Com cobertura
python -m pytest tests/ --cov=src --cov-report=html
```

## 📝 Variáveis de Ambiente

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `OPENAI_API_KEY` | Sua API key do OpenAI | - |
| `BOTLINK_DAILY_LIMIT` | Limite diário de candidaturas | 50 |
| `BOTLINK_HEADLESS` | Rodar navegador sem janela | false |
| `BOTLINK_LOG_LEVEL` | Nível de log (DEBUG/INFO) | INFO |

## ⚠️ Aviso Legal

Este software é fornecido para fins educacionais. O uso de automação em plataformas pode violar seus termos de serviço. Use por sua conta e risco.

## 📄 Licença

MIT License - veja [LICENSE](LICENSE) para detalhes.
