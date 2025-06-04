import streamlit as st
import openai
import pandas as pd
import os

# Use Streamlit Secrets for OpenAI key (configured in Streamlit Cloud)
openai.api_key = st.secrets["OPENAI_API_KEY"]

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

    # Prepare domains by grouping rows until an empty 'Dominios' value is found
    domain_options = []
    current_domain = None
    current_description = []

    for _, row in dominios_df.iterrows():
        domain = row["Dominios"]
        description = str(row["Descrição"]).strip() if not pd.isna(row["Descrição"]) else ""

        if pd.notna(domain) and domain.strip():
            # Save the previous domain if we have one
            if current_domain:
                full_description = " ".join(current_description).strip()
                domain_options.append(f"{current_domain} - {full_description}")
            # Start new domain
            current_domain = domain.strip()
            current_description = [description] if description else []
        else:
            # Continuation of the current domain description
            if description:
                current_description.append(description)

    # Save the last domain
    if current_domain:
        full_description = " ".join(current_description).strip()
        domain_options.append(f"{current_domain} - {full_description}")

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
