import streamlit as st
import pandas as pd
import json

# Função para carregar JSON de forma segura
def safe_json_loads(x):
    try:
        return json.loads(x) if isinstance(x, str) else (x if isinstance(x, dict) else {})
    except json.JSONDecodeError:
        return {}

# Função principal para limpeza e formatação do DataFrame
def process_json(json_file, start_date, end_date):
    try:
        raw_data = json.load(json_file)
        df = pd.json_normalize(raw_data)
    except Exception as e:
        st.error(f"Erro ao carregar JSON: {e}")
        return pd.DataFrame()

    # Remover colunas duplicadas
    df = df.loc[:, ~df.columns.duplicated()]

    # Expandir a coluna 'variables' caso exista
    if 'variables' in df.columns:
        variables_expanded = df['variables'].apply(safe_json_loads).apply(pd.Series)
        df = pd.concat([df.drop(columns=['variables'], errors='ignore'), variables_expanded], axis=1)

    # Unificar a data de log caso haja múltiplas colunas relacionadas
    if 'logged_at' in df.columns and 'logged_at.$date' in df.columns:
        df['logged_at'] = df['logged_at'].combine_first(df['logged_at.$date'])
        df = df.drop(columns=['logged_at.$date'], errors='ignore')
    
    # Garantir que as colunas desejadas existam
    desired_columns = ['custumerPhone', 'error', 'name', 'idHubNegocio', 'chip_resgate', 'logged_at']
    existing_columns = [col for col in desired_columns if col in df.columns]
    
    if not existing_columns:
        st.warning("Nenhuma das colunas esperadas foi encontrada no JSON.")
        return pd.DataFrame()

    df = df[existing_columns]
    
    # Converter logged_at para datetime
    try:
        df['logged_at'] = pd.to_datetime(df['logged_at'], errors='coerce')
    except Exception as e:
        st.warning(f"Erro ao converter logged_at para datetime: {e}")
        return pd.DataFrame()
    
    # Filtrar pelo intervalo de datas
    try:
        start_date = pd.to_datetime(start_date, format='%d/%m/%Y')
        end_date = pd.to_datetime(end_date, format='%d/%m/%Y')
    except Exception as e:
        st.error(f"Erro ao processar as datas inseridas: {e}")
        return pd.DataFrame()
    
    df = df.dropna(subset=['logged_at'])  # Remover valores nulos na coluna de data
    df = df[(df['logged_at'] >= start_date) & (df['logged_at'] <= end_date)]
    
    return df

# Interface Streamlit
st.title("Processador de Arquivo JSON")

# Upload do arquivo JSON
uploaded_file = st.file_uploader("Faça o upload do arquivo JSON", type="json")

# Campo para seleção de datas
start_date = st.text_input("Data inicial (dd/mm/aaaa)", "25/11/2024")
end_date = st.text_input("Data final (dd/mm/aaaa)", "27/11/2024")

if uploaded_file and start_date and end_date:
    try:
        # Processar o arquivo
        cleaned_df = process_json(uploaded_file, start_date, end_date)
        
        if not cleaned_df.empty:
            # Exibir o DataFrame
            st.write("Dados processados:")
            st.dataframe(cleaned_df)

            # Download do CSV
            csv = cleaned_df.to_csv(index=False, encoding='utf-8')
            st.download_button(
                label="Baixar CSV",
                data=csv,
                file_name="cleaned_data.csv",
                mime="text/csv",
            )
        else:
            st.warning("Nenhum dado correspondente ao intervalo de datas foi encontrado.")
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
