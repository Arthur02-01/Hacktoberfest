import json
import io
import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
from PIL import Image

# -----------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA E ESTILO.
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="MVP - Extrator de Documentos (Gemma 4)",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Extrator Inteligente de Documentos Visuais")
st.caption("Solução automatizada baseada no modelo multimodal Gemma 4")

# -----------------------------------------------------------------------------
# AUTENTICAÇÃO E CONFIGURAÇÃO DA API
# -----------------------------------------------------------------------------
st.sidebar.header("⚙️ Configurações")

# Permite usar a chave via barra lateral ou arquivo seguro de ambiente
api_key_input = st.sidebar.text_input(
    "Gemini API Key:",
    type="password",
    help="Insira sua chave do Google AI Studio para autenticar."
)

if not api_key_input:
    st.info("👈 Insira sua **Gemini API Key** na barra lateral para liberar o sistema.")
    st.stop()

@st.cache_resource
def get_genai_client(api_key: str):
    """Instancia e armazena em cache o cliente da API para economizar recursos."""
    return genai.Client(
        api_key=api_key.strip(),
        http_options=types.HttpOptions(timeout=60000)
    )

try:
    client = get_genai_client(api_key_input)
except Exception as e:
    st.error(f"Erro de conexão com o cliente API: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# INTERFACE PRINCIPAL (LAYOUT EM COLUNAS)
# -----------------------------------------------------------------------------
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.subheader("1. Enviar Documento")
    uploaded_file = st.file_uploader(
        "Selecione uma Imagem de Documento, Recibo ou Nota",
        type=["png", "jpg", "jpeg"]
    )

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption=f"Arquivo: {uploaded_file.name}", use_container_width=True)

with col_right:
    st.subheader("2. Dados Extraídos")
    
    if uploaded_file:
        btn_extract = st.button("🚀 Processar Documento", type="primary", use_container_width=True)

        if btn_extract:
            with st.spinner("O Gemma 4 está analisando a imagem e extraindo os dados..."):
                
                # Prompt estrito instruindo o modelo a responder APENAS em formato JSON válido
                prompt_estruturado = """
                Analise esta imagem de documento/recibo e extraia os dados estritamente no seguinte formato JSON puro.
                Não inclua nenhuma introdução, explicação ou marcadores de código além do próprio JSON.

                Campos obrigatórios no JSON:
                {
                    "empresa_emissora": "Nome da empresa/emissor ou Desconhecido",
                    "data": "Data do documento no formato DD/MM/AAAA ou N/A",
                    "valor_total": "Valor total com moeda (ex: R$ 150,00) ou N/A",
                    "cnpj_cpf": "Número de identificação fiscal (se houver) ou N/A",
                    "itens": [
                        {"descricao": "Item 1", "valor": "R$ X"},
                        {"descricao": "Item 2", "valor": "R$ Y"}
                    ],
                    "observacoes": "Quaisquer observações relevantes ou N/A"
                }
                """

                try:
                    response = client.models.generate_content(
                        model='gemma-4-26b-a4b-it',
                        contents=[image, prompt_estruturado]
                    )

                    raw_text = response.text.strip()
                    
                    # Limpeza para remover marcações de código markdown se o modelo retornar ```json
                    if raw_text.startswith("```"):
                        lines = raw_text.splitlines()
                        raw_text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

                    # Parse do texto retornado para dicionário Python
                    datos_json = json.loads(raw_text)

                    # Exibição dos dados organizados na tela
                    st.success("✅ Extração concluída com sucesso!")

                    # Exibe resumo em métricas
                    c1, c2 = st.columns(2)
                    c1.metric("Emissor", datos_json.get("empresa_emissora", "N/A"))
                    c2.metric("Valor Total", datos_json.get("valor_total", "N/A"))

                    st.markdown("---")
                    st.write("**Data:**", datos_json.get("data", "N/A"))
                    st.write("**CNPJ/CPF:**", datos_json.get("cnpj_cpf", "N/A"))
                    st.write("**Observações:**", datos_json.get("observacoes", "N/A"))

                    # Tabela de itens
                    itens = datos_json.get("itens", [])
                    if itens:
                        st.write("**Itens / Serviços Identificados:**")
                        df_itens = pd.DataFrame(itens)
                        st.dataframe(df_itens, use_container_width=True)

                    # ---------------------------------------------------------
                    # OPÇÕES DE EXPORTAÇÃO E DOWNLOAD
                    # ---------------------------------------------------------
                    st.markdown("---")
                    st.subheader("3. Exportar Resultados")

                    json_string = json.dumps(datos_json, indent=4, ensure_ascii=False)
                    
                    st.download_button(
                        label="📥 Baixar em formato JSON",
                        data=json_string,
                        file_name=f"extracao_{uploaded_file.name}.json",
                        mime="application/json",
                        use_container_width=True
                    )

                except json.JSONDecodeError:
                    st.warning("⚠️ O modelo processou o documento, mas a saída não foi em JSON estrito. Exibindo texto bruto:")
                    st.text(response.text)
                except Exception as e:
                    st.error(f"Ocorreu um erro durante a leitura: {e}")
    else:
        st.info("Envie um documento no painel da esquerda para habilitar o processamento.")