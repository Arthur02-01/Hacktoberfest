import streamlit as st
from google import genai
from PIL import Image

# COLOQUE SUA CHAVE AQUI DENTRO DAS ASPAS (Exemplo: "AIzaSyD...")
MINHA_CHAVE = "SUA_CHAVE_API"

st.set_page_config(page_title="Extrator Visual Gemma 4", layout="centered")
st.title("📄 Extrator de Dados Visuais com Gemma 4")

# Força o cliente a usar a chave fixa, sem depender da interface do Streamlit
try:
    client = genai.Client(api_key=MINHA_CHAVE)
except Exception as e:
    st.error(f"Erro ao inicializar o cliente: {e}")

uploaded_file = st.file_uploader("Escolha uma imagem (PNG, JPG)", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Documento Enviado", use_container_width=True)

    if st.button("Extrair Dados"):
        with st.spinner("O Gemma 4 está analisando o documento..."):
            prompt = """
            Análise esta imagem e extraia os seguintes dados em formato de lista simples:
            - Nome da Empresa/Emissor
            - Data
            - Valor Total
            - Principais Itens/Serviços
            """
            
            try:
                response = client.models.generate_content(
                    model='gemma-4-26b-a4b-it',
                    contents=[image, prompt]
                )
                st.success("Extração Concluída!")
                st.write(response.text)
            except Exception as e:
                st.error("Erro na comunicação com a API:")
                st.code(str(e))