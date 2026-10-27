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

## Diferenciais

- IA open-weight executada localmente.
- Código enviado somente ao Ollama local, sem API paga.
- Ensino por pistas progressivas e foco em iniciantes.
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
FastAPI
   ↓
Ollama (localhost:11434)
   ↓
Qwen2.5-Coder 1.5B
```

```text
open-source/
├── main.py
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
py -m venv .venv
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

Exemplo de chamada direta em PowerShell:

```powershell
$body = @{ language = 'python'; mode = 'hint'; code = 'print(1 / 0)'; hint_level = 1 } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/analyze -Method Post -ContentType 'application/json' -Body $body
```

Verificação de sintaxe:

```powershell
.\.venv\Scripts\python.exe -m py_compile main.py
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
