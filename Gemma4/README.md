# 📄 Extrator Inteligente de Documentos Visuais (Gemma 4)

Um micro-aplicativo open-source desenvolvido em Python e Streamlit que utiliza o poder do modelo multimodal **Gemma 4** (via Gemini API) para automatizar a extração de dados estruturados a partir de imagens e PDFs (notas fiscais, recibos e relatórios). 

Este projeto foi criado como um Produto Mínimo Viável (MVP) escalável para demonstrar como IA de pesos abertos pode eliminar o trabalho manual de digitação (Data Entry) em processos corporativos.

---

## 🎯 Objetivos do Projeto

* **Automação Rápida:** Reduzir o tempo gasto com a leitura e digitação manual de dados de documentos.
* **Prototipagem Ágil:** Provar valor tecnológico em poucos dias utilizando a stack de Inteligência Artificial do Google.
* **Acurácia e Controle:** Manter o ser humano no ciclo (Human-in-the-Loop) permitindo revisão e edição manual antes do envio para o banco de dados.

---

## ✨ Principais Funcionalidades

* **Suporte Multimodal:** Lê nativamente imagens (`.png`, `.jpg`, `.jpeg`) e arquivos `.pdf` (convertendo-os automaticamente).
* **Processamento em Lote (Batch):** Permite o upload simultâneo de múltiplos documentos, processando-os em fila com barra de progresso.
* **Saída Estruturada (JSON):** O modelo é guiado por prompts rígidos para devolver apenas dados em chave-valor.
* **Tabela de Edição Interativa:** Os resultados são exibidos em uma interface de planilha onde o usuário pode corrigir eventuais erros da IA diretamente na tela.
* **Múltiplas Exportações:** Consolidação dos dados lidos em planilhas Excel (`.xlsx`) ou armazenamento incremental em CSV local (simulando um Banco de Dados/ERP).

---

## 🛠️ Tecnologias Utilizadas

* **[Python 3.9+](https://www.python.org/):** Linguagem base do projeto.
* **[Streamlit](https://streamlit.io/):** Framework para criação rápida da interface web.
* **[Google GenAI SDK](https://ai.google.dev/):** Comunicação oficial com a API de inferência do Gemma 4.
* **[Pandas](https://pandas.pydata.org/):** Manipulação, tratamento de dados e conversão de DataFrames.
* **[PyMuPDF (fitz)](https://pymupdf.readthedocs.io/):** Leitura de PDFs de alta performance.
* **[OpenPyXL](https://openpyxl.readthedocs.io/):** Motor de escrita e exportação para formatos Excel.

---

## ⚙️ Pré-requisitos e Instalação

### 1. Obtenha a sua API Key
Para utilizar o modelo Gemma 4, você precisará de uma chave de API gratuita:
1. Acesse o [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Clique em **"Create API Key"** e copie a chave gerada (iniciada com `AIzaSy...`).

### 2. Configure o Ambiente Local
No terminal da sua máquina, clone este repositório e acesse a pasta do projeto:

```bash
git clone [https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git](https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git)
cd NOME_DO_REPOSITORIO