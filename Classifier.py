# streamlit_app.py
import streamlit as st
import openai
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="Classificador de Projetos", layout="wide")
st.title("🔎 Classificador de Projetos I&D por Domínio Prioritário")

# File upload
uploaded_file = st.file_uploader("📤 Carregue o ficheiro Excel com os projetos e dominios", type=["xlsx"])

if uploaded_file:
    # Read Excel file
    xls = pd.ExcelFile(uploaded_file)
    try:
        projetos_df = xls.parse("Projetos")
        dominios_df = xls.parse("Dominios")
    except Exception as e:
        st.error(f"Erro ao ler as folhas 'Projetos' ou 'Dominios': {e}")
        st.stop()

    if "Sumario Executivo" not in projetos_df.columns:
        st.error("A folha 'Projetos' precisa da coluna 'Sumario Executivo'.")
        st.stop()

    # Prepare domains
    domain_options = []
    for _, row in dominios_df.iterrows():
        domain_options.append(f"{row['Domain']} - {row['Descrição']}")

    def classify_project(summary):
        prompt = f"""
        Atribua o seguinte projeto de I&D a um dos seguintes domínios prioritários com base no seu resumo.

        Domínios disponíveis:
        {chr(10).join(domain_options)}

        Resumo do projeto:
        """
        prompt += f"""\n{summary}\n
        Responda apenas com o nome do domínio mais adequado."""

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "És um classificador de projetos de I&D em Portugal."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Erro: {e}"

    if st.button("🚀 Classificar Projetos"):
        results = []
        for idx, row in projetos_df.iterrows():
            summary = row["Sumario Executivo"]
            domain = classify_project(summary)
            results.append({
                "ID": idx + 1,
                "Sumario Executivo": summary,
                "Domínio Classificado": domain
            })

        result_df = pd.DataFrame(results)

        # Display result
        st.success("Classificação concluída!")
        st.dataframe(result_df)

        # Download Excel
        output = pd.ExcelWriter("classified_projects.xlsx", engine='xlsxwriter')
        projetos_df.to_excel(output, index=False, sheet_name='Projetos')
        dominios_df.to_excel(output, index=False, sheet_name='Dominios')
        result_df.to_excel(output, index=False, sheet_name='Classificação')
        output.close()

        with open("classified_projects.xlsx", "rb") as f:
            st.download_button(
                label="📥 Descarregar ficheiro Excel com classificação",
                data=f,
                file_name="classified_projects.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
