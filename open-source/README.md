# CodeTutor AI

Aprenda a programar entendendo seus erros.

Tutor de programação open-source desenvolvido para o desafio **Best Open-Source AI Project**. Usa o modelo open-weight `qwen2.5-coder:1.5b`, executado localmente com Ollama, sem API comercial.

## O problema

Muitos estudantes usam IA para receber respostas prontas e acabam não compreendendo o raciocínio. Resolver um exercício sem entender os erros dificulta a aprendizagem.

## Nossa solução

O CodeTutor AI analisa o código como texto e orienta o estudante em português do Brasil. Ele não executa o código enviado.

| Modo | Como ajuda |
| --- | --- |
| Quero uma dica | Identifica o provável problema, dá pistas e faz perguntas, sem fornecer o código corrigido. |
| Explique meu código | Explica o código por linhas ou blocos e apresenta os conceitos utilizados. |
| Encontrar erro | Explica possíveis erros, suas causas e apresenta uma correção com código. |
| Melhorar código | Sugere boas práticas, legibilidade, organização e otimizações simples em texto. |

### Modo Pistas

1. **Pista 1 — leve:** o que observar.
2. **Pista 2 — intermediária:** orientação mais específica, incluindo a pista anterior no pedido.
3. **Pista 3 — quase solução:** orientação próxima da solução, ainda sem entregar o código final.

Após a terceira pista, aparece **Ver solução**, que solicita a análise no modo debug. Falhas na requisição não avançam o nível. Alterar o código, a linguagem ou o modo reinicia as pistas.

## GitHub Repository Analyzer

Na aba **Analisar GitHub**, cole a URL de um repositório público GitHub, como `https://github.com/usuario/projeto`, e clique em **Analisar repositório**.

O CodeTutor:

1. baixa o código;
2. identifica arquivos Python;
3. executa análise estática;
4. identifica problemas;
5. usa Qwen2.5-Coder para explicar os problemas didaticamente.

> **O CodeTutor NÃO executa o código do repositório.** Os arquivos são baixados, lidos como texto e analisados com o módulo `ast` da biblioteca padrão. Nada é importado, avaliado ou executado (`exec`, `eval`, `os.system` e `subprocess` não são usados sobre o código baixado).

### Não é apenas um chatbot

```text
Análise estática Python
        +
IA open-weight (Qwen2.5-Coder local)
        +
Tutor pedagógico
```

A **análise estática** identifica sinais objetivos, com arquivo e linha. A **IA** transforma esses sinais em explicações didáticas: por que o problema acontece, como investigar e como corrigir. Assim o modelo pequeno não precisa ler o repositório inteiro, e o relatório se apoia em evidências reais.

### Fluxo

```text
URL GitHub → validação → API do GitHub (branch padrão) → download do ZIP
→ diretório temporário (proteção Zip Slip) → arquivos .py → análise estática
→ contexto resumido → Qwen2.5-Coder → relatório → diretório temporário apagado
```

### O que a análise estática detecta

| Severidade | Sinais |
| --- | --- |
| CRÍTICO | Erros de sintaxe (`ast.parse`), `eval`, `exec`, `pickle.load(s)`, `os.system`, `subprocess` com `shell=True`, senhas/chaves fixas em variáveis com nomes suspeitos (o valor é mascarado) |
| IMPORTANTE | `except:` sem tipo, `except Exception:` genérico |
| MELHORIA | Funções com mais de 60 linhas, arquivos com mais de 800 linhas, `TODO`/`FIXME`, imports duplicados, `import *`, imports possivelmente não usados, `print()` em projeto que parece backend |

Também são extraídos funções, classes, métodos e imports de cada arquivo para dar contexto ao relatório. Em arquivos de teste, valores fixos de senha/chave viram MELHORIA, pois costumam ser dados de teste.

### O que a IA recebe

Para caber no modelo `qwen2.5-coder:1.5b`, o repositório inteiro **não** é enviado. O contexto contém: estrutura resumida do projeto, bibliotecas importadas, erros de sintaxe, até 30 alertas ordenados por severidade e até 8 trechos de código (±3 linhas) ao redor dos problemas.

### Limites e segurança

- Somente URLs `https://github.com/usuario/repositorio`; o hostname é validado com `urllib.parse`. URLs com `localhost`, `127.0.0.1`, `file://`, `ftp://`, porta, usuário/senha ou outros domínios são recusadas.
- Os redirecionamentos do download são seguidos manualmente e só podem ir para `github.com` ou `codeload.github.com`.
- ZIP de no máximo 60 MB; todos os caminhos são validados antes da extração (Zip Slip), e só os arquivos `.py` selecionados são extraídos.
- `MAX_REPO_FILES = 30`, `MAX_FILE_SIZE = 50000` caracteres por arquivo e `MAX_TOTAL_CHARS = 150000` no total.
- Arquivos principais (`main.py`, `app.py`, `server.py`, `api.py`, `routes.py`, `models.py`, `services.py`, `utils.py`, `config.py`, `settings.py`) são priorizados; testes ficam por último.
- São ignorados `.venv`, `venv`, `env`, `__pycache__`, `.git`, `node_modules`, `dist`, `build`, `site-packages`, `migrations` e `__init__.py` vazios.
- Tudo acontece em `tempfile.TemporaryDirectory()`, apagado ao final mesmo em caso de erro.
- A API pública do GitHub permite cerca de 60 consultas por hora por IP. Se o limite for atingido, defina a variável de ambiente opcional `GITHUB_TOKEN` antes de iniciar o servidor.
- A sintaxe é verificada com a versão do Python que executa o servidor; código escrito para uma versão mais nova pode aparecer como erro de sintaxe.

### Endpoint

`POST /api/analyze-repository`

```json
{ "repository_url": "https://github.com/usuario/projeto" }
```

Resposta (resumida):

```json
{
  "repository": "usuario/projeto",
  "language": "Python",
  "branch": "main",
  "files_found": 18,
  "files_analyzed": 14,
  "syntax_errors": 2,
  "warnings": 6,
  "syntax_error_details": [{ "file": "app/main.py", "line": 32, "type": "SyntaxError", "message": "invalid syntax" }],
  "warning_details": [{ "file": "utils.py", "line": 28, "type": "Uso de eval", "severity": "CRÍTICO", "message": "..." }],
  "notes": [],
  "report": "# Relatório CodeTutor ..."
}
```

Erros retornam mensagens amigáveis para: URL inválida, repositório não encontrado ou privado, nenhum arquivo Python, GitHub indisponível ou limite de requisições, falha no download, repositório grande demais, Ollama offline, modelo não instalado e tempo limite.

## Diferenciais

- IA open-weight executada localmente.
- Código enviado somente ao Ollama local, sem API paga.
- Ensino por pistas progressivas e foco em iniciantes.
- Análise de repositórios GitHub combinando análise estática e IA, sem executar o código.
- Três exemplos prontos, dois em Python e um em JavaScript.
- Interface escura responsiva, Markdown e cópia dos blocos de código.
- Software open-source com licença MIT.

## Tecnologias

Python, FastAPI, Uvicorn, httpx, Pydantic, HTML, CSS, JavaScript puro, Ollama e Qwen2.5-Coder. Sem framework de frontend, CDN ou biblioteca CSS externa.

## Arquitetura

```text
Browser
   ↓
Frontend (HTML / CSS / JavaScript)
   ↓
FastAPI ──→ GitHub (somente na análise de repositório)
   ↓
Ollama (localhost:11434)
   ↓
Qwen2.5-Coder 1.5B
```

```text
open-source/
├── main.py              # API, prompts e integração com o Ollama
├── github_analyzer.py   # download seguro e análise estática de repositórios
├── requirements.txt
├── README.md
├── LICENSE
├── .gitignore
└── static/
    ├── index.html
    ├── style.css
    └── app.js
```

## Instalação Windows

Pré-requisitos: Python 3.10 ou superior e Ollama instalado. É necessária internet para instalar dependências e baixar o modelo; depois o tutor pode funcionar localmente sem internet.

No terminal, entre na pasta `open-source` e baixe o modelo:

```powershell
cd open-source
ollama pull qwen2.5-coder:1.5b
```

Mantenha o Ollama aberto. Se ele não estiver rodando, use outro terminal:

```powershell
ollama serve
```

Crie o ambiente e instale as dependências:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Execute a aplicação:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Acesse **http://127.0.0.1:8000**. Não abra o HTML diretamente: a interface usa as rotas do servidor. A documentação interativa fica em **http://127.0.0.1:8000/docs**.

## Como testar e demonstrar

1. Verifique o indicador verde **IA local conectada**. `GET /api/health` verifica o Ollama e informa se o modelo está instalado.
2. Clique em **Carregar exemplo**; cliques seguintes alternam entre os três exemplos.
3. Selecione **Quero uma dica** e clique em **Analisar com IA**. Confira os três níveis com **Quero outra pista** e, ao final, **Ver solução**.
4. Teste também **Explique meu código**, **Encontrar erro** e **Melhorar código**.
5. No modo debug, use **Copiar** no bloco de código da resposta.
6. Altere o código ou a linguagem e confirme que as pistas anteriores foram reiniciadas.
7. Envie um campo vazio e mais de 15.000 caracteres: devem aparecer mensagens amigáveis.
8. Pare o Ollama e faça outra análise: a página deve continuar funcionando e informar o erro. O status é atualizado a cada 15 segundos.
9. Abra a aba **Analisar GitHub**, cole `https://github.com/pallets/itsdangerous` e clique em **Analisar repositório**. Confira o resumo (arquivos, erros de sintaxe e alertas), a lista da análise estática e o relatório. Gerar o relatório pode levar de 30 segundos a alguns minutos, dependendo do computador.
10. Teste `https://gitlab.com/a/b` (URL inválida) e um repositório inexistente (não encontrado). A análise de repositório precisa de internet para acessar o GitHub.

Exemplo de chamada direta em PowerShell:

```powershell
$body = @{ language = 'python'; mode = 'hint'; code = 'print(1 / 0)'; hint_level = 1 } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/analyze -Method Post -ContentType 'application/json' -Body $body
```

Verificação de sintaxe:

```powershell
.\.venv\Scripts\python.exe -m py_compile main.py github_analyzer.py
```

Análise de repositório pelo PowerShell:

```powershell
$body = @{ repository_url = 'https://github.com/pallets/itsdangerous' } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/analyze-repository -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 300
```

## Decisões técnicas e limites

- O backend envia `POST /api/chat` com `stream: false`, prompt pedagógico, linguagem, modo e código. O timeout HTTP é de 90 segundos; a interface também limita a espera.
- Os caminhos estáticos são resolvidos a partir de `main.py`.
- O código é limitado a 15.000 caracteres e nunca é executado com `exec`, `eval`, subprocessos ou comandos do sistema.
- O renderer escapa HTML e preserva o texto dos blocos de código. Suporta títulos, listas simples ordenadas e não ordenadas, parágrafos, negrito e inline code; não implementa todo o Markdown.
- Os três níveis são um fluxo pedagógico da interface; o modo debug também pode ser escolhido diretamente.
- A IA pode errar e descumprir instruções. As regras pedagógicas são orientações ao modelo, não garantias sobre cada resposta. A qualidade e o tempo de geração precisam ser avaliados com o modelo real no computador da demonstração.
- Se aparecer **Modelo não encontrado**, execute `ollama pull qwen2.5-coder:1.5b`. Se aparecer **Ollama desconectado**, abra o Ollama ou execute `ollama serve`.

## Licença

MIT para o código deste projeto; consulte `LICENSE`. O modelo e o Ollama possuem suas próprias licenças.
