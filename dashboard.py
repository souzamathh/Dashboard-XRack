import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os
import numpy as np
import hashlib

# Sistema de autenticação
def check_password():
    """Retorna True se a senha estiver correta"""
    
    def password_entered():
        """Verifica se a senha inserida está correta"""
        if hashlib.sha256(st.session_state["password"].encode()).hexdigest() == hashlib.sha256("xrack18361832".encode()).hexdigest():
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Remove a senha da sessão por segurança
        else:
            st.session_state["password_correct"] = False

    # Retorna True se a senha já foi validada
    if st.session_state.get("password_correct", False):
        return True

    # Mostra input para senha
    st.text_input(
        "Digite a senha:",
        type="password",
        on_change=password_entered,
        key="password"
    )
    
    if "password_correct" in st.session_state:
        if not st.session_state["password_correct"]:
            st.error("Senha incorreta")
    
    return False

# Verificar senha antes de mostrar o dashboard
if not check_password():
    st.stop()

# Configuração da página (remover o caminho local do ícone)
st.set_page_config(
    page_title="Dashboard",
    # page_icon="🏪",  # Use emoji ou remova a linha
    layout="wide",
    initial_sidebar_state="expanded"
)

# Na função load_data(), substitua o caminho fixo por:
@st.cache_data
def load_data():
    # Procurar pelo arquivo na pasta atual
    possible_files = [
        "MercadoTurbo_Financeiro_01_07_2025_a_31_07_2025.xlsx",
        "dados.xlsx",  # nome alternativo
        # adicione outros nomes possíveis
    ]
    
    file_path = None
    for filename in possible_files:
        if os.path.exists(filename):
            file_path = filename
            break
    
    if not file_path:
        st.error("Arquivo de dados não encontrado!")
        return pd.DataFrame()

# Configuração da página
st.set_page_config(
    page_title="Dashboard",
    page_icon="C:\Tecnologia\BI\Vendas\Logo X PNG 2.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Função para carregar dados
@st.cache_data
def load_data():
    file_path = r"MercadoTurbo_Financeiro_01_07_2025_a_31_07_2025.xlsx"
    
    try:
        # Tentar identificar automaticamente a linha de cabeçalho (primeira que contenha 'Data')
        df = None
        for header_row in range(5):  # tentar nas 5 primeiras linhas
            tmp = pd.read_excel(file_path, header=header_row)
            if any(str(col).strip().lower() == 'data' for col in tmp.columns):
                df = tmp.copy()
                break
        if df is None:
            # Fallback: lê normalmente
            df = pd.read_excel(file_path)
        # Remover colunas sem nome (geralmente índices vazios do Excel)
        df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed')]
        
        # Limpeza e formatação dos dados
        # Converter colunas monetárias
        money_columns = ['Valor Unit.', 'Faturamento', 'Custo (-)', 'Imposto (-)', 
                        'Tarifa de Venda (-)', 'Frete Comprador (-)', 'Frete Vendedor (-)', 
                        'Margem Contrib. (=)']
        
        for col in money_columns:
            if col in df.columns:
                # Verifica o tipo da coluna para evitar remover casas decimais de valores já numéricos
                if df[col].dtype == 'O':
                    # Limpeza de strings monetárias no formato brasileiro
                    df[col] = (
                        df[col]
                        .astype(str)
                        .str.replace('R$ ', '', regex=False)
                        .str.replace('.', '', regex=False)
                        .str.replace(',', '.', regex=False)
                    )
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                else:
                    # Já é numérico, apenas garante coerção e trata NaNs
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Converter percentuais
        if 'MC em %' in df.columns:
            if df['MC em %'].dtype == 'O':
                df['MC em %'] = (
                    df['MC em %']
                    .astype(str)
                    .str.replace('%', '', regex=False)
                    .str.replace(',', '.', regex=False)
                )
                df['MC em %'] = pd.to_numeric(df['MC em %'], errors='coerce').fillna(0) / 100
            else:
                # Se já estiver numérica (0 a 1), apenas garante coerção
                df['MC em %'] = pd.to_numeric(df['MC em %'], errors='coerce').fillna(0)
        
        # Normalizar nomes das colunas para facilitar busca
        df.columns = [col.strip() for col in df.columns]
        # Procurar coluna de data (case insensitive, sem espaços)
        data_candidates = [col for col in df.columns if col.strip().lower() == 'data']
        if not data_candidates:
            st.error(f"Erro: Coluna 'Data' não encontrada no arquivo. Colunas disponíveis: {list(df.columns)}")
            return pd.DataFrame()
        # Renomear para 'Data' se necessário
        if data_candidates[0] != 'Data':
            df = df.rename(columns={data_candidates[0]: 'Data'})
        # Converter para datetime
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        if df['Data'].isna().all():
            st.error("Erro: Nenhuma data válida encontrada na coluna 'Data'.")
            return pd.DataFrame()
        if df['Data'].isna().any():
            st.warning("Aviso: Algumas datas não puderam ser convertidas e serão removidas.")
        df = df.dropna(subset=['Data'])
        # Colunas auxiliares
        df['Ano'] = df['Data'].dt.year
        df['Mes'] = df['Data'].dt.month
        df['Dia'] = df['Data'].dt.day
        df['Semana'] = df['Data'].dt.isocalendar().week
        
        # Garantir que Qtd. seja numérica
        if 'Qtd.' in df.columns:
            df['Qtd.'] = pd.to_numeric(df['Qtd.'], errors='coerce').fillna(0)
        
        # Criar coluna de ID único se não existir
        if 'ID da venda' not in df.columns:
            df['ID da venda'] = range(1, len(df) + 1)
        
        return df
    
    except FileNotFoundError:
        st.error("Arquivo não encontrado! Verifique se o arquivo existe no caminho especificado.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo: {str(e)}")
        return pd.DataFrame()

# Função para filtrar dados por período
def filter_by_period(df, period_type, start_date=None, end_date=None):
    if df.empty:
        return df
    
    today = datetime.now().date()
    
    if period_type == "Personalizado":
        if start_date and end_date:
            return df[(df['Data'].dt.date >= start_date) & (df['Data'].dt.date <= end_date)]
    elif period_type == "Últimos 7 dias":
        start = today - timedelta(days=7)
        return df[df['Data'].dt.date >= start]
    elif period_type == "Últimos 15 dias":
        start = today - timedelta(days=15)
        return df[df['Data'].dt.date >= start]
    elif period_type == "Últimos 30 dias":
        start = today - timedelta(days=30)
        return df[df['Data'].dt.date >= start]
    elif period_type == "Mês atual":
        return df[(df['Data'].dt.month == today.month) & (df['Data'].dt.year == today.year)]
    elif period_type == "Diário":
        return df[df['Data'].dt.date == today]
    
    return df

# Função para calcular período anterior
def get_previous_period_data(df, current_df, period_type):
    if df.empty or current_df.empty:
        return pd.DataFrame()
    
    current_start = current_df['Data'].min()
    current_end = current_df['Data'].max()
    period_length = (current_end - current_start).days
    
    if period_length == 0:
        period_length = 1  # Para períodos de um dia
    
    previous_start = current_start - timedelta(days=period_length + 1)
    previous_end = current_start - timedelta(days=1)
    
    return df[(df['Data'] >= previous_start) & (df['Data'] <= previous_end)]

# Título principal
st.title("📊 Dashboard")
st.markdown("---")

# Carregar dados
df = load_data()

if df.empty:
    st.stop()

# Sidebar para filtros
st.sidebar.title("🔍 Filtros")

# Filtro de período
period_options = ["Todos os dados", "Últimos 7 dias", "Últimos 15 dias", 
                 "Últimos 30 dias", "Mês atual", "Diário", "Personalizado"]
period_type = st.sidebar.selectbox("Período:", period_options)

# Filtro de data personalizada
if period_type == "Personalizado":
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("Data início:", df['Data'].min().date())
    with col2:
        end_date = st.date_input("Data fim:", df['Data'].max().date())
else:
    start_date = end_date = None

# Filtros adicionais
canal_options = ["Todos"] + sorted(df['Canal de Venda'].dropna().unique().tolist())
canal_selected = st.sidebar.selectbox("Canal de Venda:", canal_options)

conta_options = ["Todas"] + sorted(df['Conta'].dropna().unique().tolist())
conta_selected = st.sidebar.selectbox("Conta:", conta_options)

# Aplicar filtros
filtered_df = df.copy()

if period_type != "Todos os dados":
    filtered_df = filter_by_period(df, period_type, start_date, end_date)

if canal_selected != "Todos":
    filtered_df = filtered_df[filtered_df['Canal de Venda'] == canal_selected]

if conta_selected != "Todas":
    filtered_df = filtered_df[filtered_df['Conta'] == conta_selected]

# Obter dados do período anterior para comparação
previous_df = get_previous_period_data(df, filtered_df, period_type)

# Métricas principais
st.header("📈 Visão Geral")

col1, col2, col3, col4 = st.columns(4)

with col1:
    # Corrigido: contar registros únicos de vendas
    total_vendas = filtered_df.shape[0]  # Número total de linhas/registros
    prev_vendas = previous_df.shape[0] if not previous_df.empty else 0
    growth_vendas = ((total_vendas - prev_vendas) / prev_vendas * 100) if prev_vendas > 0 else 0
    st.metric("Total de Vendas", f"{total_vendas:,}", f"{growth_vendas:+.1f}%")

with col2:
    # Corrigido: somar faturamento total
    total_faturamento = filtered_df['Faturamento'].sum()
    prev_faturamento = previous_df['Faturamento'].sum() if not previous_df.empty else 0
    growth_faturamento = ((total_faturamento - prev_faturamento) / prev_faturamento * 100) if prev_faturamento > 0 else 0
    st.metric("Faturamento", f"R$ {total_faturamento:,.2f}", f"{growth_faturamento:+.1f}%")

with col3:
    # Corrigido: somar margem de contribuição
    total_margem = filtered_df['Margem Contrib. (=)'].sum()
    prev_margem = previous_df['Margem Contrib. (=)'].sum() if not previous_df.empty else 0
    growth_margem = ((total_margem - prev_margem) / prev_margem * 100) if prev_margem > 0 else 0
    st.metric("MC (R$)", f"R$ {total_margem:,.2f}", f"{growth_margem:+.1f}%")

with col4:
    # CORRIGIDO: calcular MC% = (Margem Total / Faturamento Total) * 100
    avg_margem_perc = (total_margem / total_faturamento * 100) if total_faturamento > 0 else 0
    
    # Período anterior - mesmo cálculo
    prev_faturamento_total = previous_df['Faturamento'].sum() if not previous_df.empty else 0
    prev_margem_total = previous_df['Margem Contrib. (=)'].sum() if not previous_df.empty else 0
    prev_avg_margem = (prev_margem_total / prev_faturamento_total * 100) if prev_faturamento_total > 0 else 0
    
    growth_avg_margem = avg_margem_perc - prev_avg_margem
    st.metric("MC (%)", f"{avg_margem_perc:.1f}%", f"{growth_avg_margem:+.1f}%")

st.markdown("---")

# Métricas adicionais por Canal e Conta
st.subheader("Por Canal e Conta")

if not filtered_df.empty:
    # Resumo por canal - PERÍODO ATUAL
    resumo_canal = filtered_df.groupby('Canal de Venda').agg({
        'Faturamento': 'sum',
        'Qtd.': 'sum',
        'Margem Contrib. (=)': 'sum'
    })
    
    # Resumo por conta e canal - PERÍODO ATUAL
    resumo_conta_canal = filtered_df.groupby(['Canal de Venda', 'Conta']).agg({
        'Faturamento': 'sum',
        'Qtd.': 'sum',
        'Margem Contrib. (=)': 'sum'
    })
    
    # Resumo por canal - PERÍODO ANTERIOR
    resumo_canal_prev = pd.DataFrame()
    resumo_conta_canal_prev = pd.DataFrame()
    
    if not previous_df.empty:
        resumo_canal_prev = previous_df.groupby('Canal de Venda').agg({
            'Faturamento': 'sum',
            'Qtd.': 'sum',
            'Margem Contrib. (=)': 'sum'
        })
        
        resumo_conta_canal_prev = previous_df.groupby(['Canal de Venda', 'Conta']).agg({
            'Faturamento': 'sum',
            'Qtd.': 'sum',
            'Margem Contrib. (=)': 'sum'
        })
    
    # Primeira linha - Totais por Canal
    col1, col2 = st.columns(2)
    
    with col1:
        ml_fat = resumo_canal.loc['Mercado Livre', 'Faturamento'] if 'Mercado Livre' in resumo_canal.index else 0
        ml_qtd = resumo_canal.loc['Mercado Livre', 'Qtd.'] if 'Mercado Livre' in resumo_canal.index else 0
        ml_margem = resumo_canal.loc['Mercado Livre', 'Margem Contrib. (=)'] if 'Mercado Livre' in resumo_canal.index else 0
        
        # Calcular MC% corretamente
        ml_mc_perc = (ml_margem / ml_fat * 100) if ml_fat > 0 else 0
        
        # Período anterior - Mercado Livre
        ml_fat_prev = resumo_canal_prev.loc['Mercado Livre', 'Faturamento'] if not resumo_canal_prev.empty and 'Mercado Livre' in resumo_canal_prev.index else 0
        ml_growth = ((ml_fat - ml_fat_prev) / ml_fat_prev * 100) if ml_fat_prev > 0 else 0
        
        st.metric("🟡 Mercado Livre", f"R$ {ml_fat:,.2f}", f"{ml_growth:+.1f}%")
        st.markdown(f'<div style="margin-top: -10px; margin-bottom: 30px; opacity: 0.6; font-size: 0.8em;"><strong>MC:</strong> R$ {ml_margem:,.2f} <strong>({ml_mc_perc:.1f}%)</strong></div>', unsafe_allow_html=True)
    
    with col2:
        shopee_fat = resumo_canal.loc['Shopee', 'Faturamento'] if 'Shopee' in resumo_canal.index else 0
        shopee_qtd = resumo_canal.loc['Shopee', 'Qtd.'] if 'Shopee' in resumo_canal.index else 0
        shopee_margem = resumo_canal.loc['Shopee', 'Margem Contrib. (=)'] if 'Shopee' in resumo_canal.index else 0
        
        # Calcular MC% corretamente
        shopee_mc_perc = (shopee_margem / shopee_fat * 100) if shopee_fat > 0 else 0
        
        # Período anterior - Shopee
        shopee_fat_prev = resumo_canal_prev.loc['Shopee', 'Faturamento'] if not resumo_canal_prev.empty and 'Shopee' in resumo_canal_prev.index else 0
        shopee_growth = ((shopee_fat - shopee_fat_prev) / shopee_fat_prev * 100) if shopee_fat_prev > 0 else 0
        
        st.metric("🔴 Shopee", f"R$ {shopee_fat:,.2f}", f"{shopee_growth:+.1f}%")
        st.markdown(f'<div style="margin-top: -10px; margin-bottom: 30px; opacity: 0.6; font-size: 0.8em;"><strong>MC:</strong> R$ {shopee_margem:,.2f} <strong>({shopee_mc_perc:.1f}%)</strong></div>', unsafe_allow_html=True)
    
    # Linhas seguintes - Por Conta e Canal
    col1, col2 = st.columns(2)
    
    with col1:
        try:
            ml_xr_fat = resumo_conta_canal.loc[('Mercado Livre', 'XRack'), 'Faturamento']
            ml_xr_qtd = resumo_conta_canal.loc[('Mercado Livre', 'XRack'), 'Qtd.']
            ml_xr_margem = resumo_conta_canal.loc[('Mercado Livre', 'XRack'), 'Margem Contrib. (=)']
            
            # Calcular MC% corretamente
            ml_xr_mc_perc = (ml_xr_margem / ml_xr_fat * 100) if ml_xr_fat > 0 else 0
            
            # Período anterior - ML XRack
            ml_xr_fat_prev = 0
            if not resumo_conta_canal_prev.empty and ('Mercado Livre', 'XRack') in resumo_conta_canal_prev.index:
                ml_xr_fat_prev = resumo_conta_canal_prev.loc[('Mercado Livre', 'XRack'), 'Faturamento']
            ml_xr_growth = ((ml_xr_fat - ml_xr_fat_prev) / ml_xr_fat_prev * 100) if ml_xr_fat_prev > 0 else 0
            
            st.metric("🟡 XRack", f"R$ {ml_xr_fat:,.2f}", f"{ml_xr_growth:+.1f}%")
            st.markdown(f'<div style="margin-top: -10px; margin-bottom: 30px; opacity: 0.6; font-size: 0.8em;"><strong>MC:</strong> R$ {ml_xr_margem:,.2f} <strong>({ml_xr_mc_perc:.1f}%)</strong></div>', unsafe_allow_html=True)
        except KeyError:
            st.metric("🟡 XRack", "R$ 0,00", "0.0%")
            st.markdown('<div style="margin-top: -10px; margin-bottom: 30px; opacity: 0.6; font-size: 0.8em;"><strong>MC:</strong> R$ 0,00 <strong>(0.0%)</strong></div>', unsafe_allow_html=True)
    
    with col2:
        try:
            ml_ev_fat = resumo_conta_canal.loc[('Mercado Livre', 'EvolutionX'), 'Faturamento']
            ml_ev_qtd = resumo_conta_canal.loc[('Mercado Livre', 'EvolutionX'), 'Qtd.']
            ml_ev_margem = resumo_conta_canal.loc[('Mercado Livre', 'EvolutionX'), 'Margem Contrib. (=)']
            
            # Calcular MC% corretamente
            ml_ev_mc_perc = (ml_ev_margem / ml_ev_fat * 100) if ml_ev_fat > 0 else 0
            
            # Período anterior - ML EvolutionX
            ml_ev_fat_prev = 0
            if not resumo_conta_canal_prev.empty and ('Mercado Livre', 'EvolutionX') in resumo_conta_canal_prev.index:
                ml_ev_fat_prev = resumo_conta_canal_prev.loc[('Mercado Livre', 'EvolutionX'), 'Faturamento']
            ml_ev_growth = ((ml_ev_fat - ml_ev_fat_prev) / ml_ev_fat_prev * 100) if ml_ev_fat_prev > 0 else 0
            
            st.metric("🟡 EvolutionX", f"R$ {ml_ev_fat:,.2f}", f"{ml_ev_growth:+.1f}%")
            st.markdown(f'<div style="margin-top: -10px; margin-bottom: 20px; opacity: 0.6; font-size: 0.8em;"><strong>MC:</strong> R$ {ml_ev_margem:,.2f} <strong>({ml_ev_mc_perc:.1f}%)</strong></div>', unsafe_allow_html=True)
        except KeyError:
            st.metric("🟡 EvolutionX", "R$ 0,00", "0.0%")
            st.markdown('<div style="margin-top: -10px; margin-bottom: 20px; opacity: 0.6; font-size: 0.8em;"><strong>MC:</strong> R$ 0,00 <strong>(0.0%)</strong></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        try:
            sh_xr_fat = resumo_conta_canal.loc[('Shopee', 'XRack'), 'Faturamento']
            sh_xr_qtd = resumo_conta_canal.loc[('Shopee', 'XRack'), 'Qtd.']
            sh_xr_margem = resumo_conta_canal.loc[('Shopee', 'XRack'), 'Margem Contrib. (=)']
            
            # Calcular MC% corretamente
            sh_xr_mc_perc = (sh_xr_margem / sh_xr_fat * 100) if sh_xr_fat > 0 else 0
            
            # Período anterior - Shopee XRack
            sh_xr_fat_prev = 0
            if not resumo_conta_canal_prev.empty and ('Shopee', 'XRack') in resumo_conta_canal_prev.index:
                sh_xr_fat_prev = resumo_conta_canal_prev.loc[('Shopee', 'XRack'), 'Faturamento']
            sh_xr_growth = ((sh_xr_fat - sh_xr_fat_prev) / sh_xr_fat_prev * 100) if sh_xr_fat_prev > 0 else 0
            
            st.metric("🔴 XRack", f"R$ {sh_xr_fat:,.2f}", f"{sh_xr_growth:+.1f}%")
            st.markdown(f'<div style="margin-top: -10px; margin-bottom: 20px; opacity: 0.6; font-size: 0.8em;"><strong>MC:</strong> R$ {sh_xr_margem:,.2f} <strong>({sh_xr_mc_perc:.1f}%)</strong></div>', unsafe_allow_html=True)
        except KeyError:
            st.metric("🔴 XRack", "R$ 0,00", "0.0%")
            st.markdown('<div style="margin-top: -10px; margin-bottom: 20px; opacity: 0.6; font-size: 0.8em;"><strong>MC:</strong> R$ 0,00 <strong>(0.0%)</strong></div>', unsafe_allow_html=True)
    
    with col2:
        try:
            sh_ev_fat = resumo_conta_canal.loc[('Shopee', 'EvolutionX'), 'Faturamento']
            sh_ev_qtd = resumo_conta_canal.loc[('Shopee', 'EvolutionX'), 'Qtd.']
            sh_ev_margem = resumo_conta_canal.loc[('Shopee', 'EvolutionX'), 'Margem Contrib. (=)']
            
            # Calcular MC% corretamente
            sh_ev_mc_perc = (sh_ev_margem / sh_ev_fat * 100) if sh_ev_fat > 0 else 0
            
            # Período anterior - Shopee EvolutionX
            sh_ev_fat_prev = 0
            if not resumo_conta_canal_prev.empty and ('Shopee', 'EvolutionX') in resumo_conta_canal_prev.index:
                sh_ev_fat_prev = resumo_conta_canal_prev.loc[('Shopee', 'EvolutionX'), 'Faturamento']
            sh_ev_growth = ((sh_ev_fat - sh_ev_fat_prev) / sh_ev_fat_prev * 100) if sh_ev_fat_prev > 0 else 0
            
            st.metric("🔴 EvolutionX", f"R$ {sh_ev_fat:,.2f}", f"{sh_ev_growth:+.1f}%")
            st.markdown(f'<div style="margin-top: -10px; margin-bottom: 20px; opacity: 0.6; font-size: 0.8em;"><strong>MC:</strong> R$ {sh_ev_margem:,.2f} <strong>({sh_ev_mc_perc:.1f}%)</strong></div>', unsafe_allow_html=True)
        except KeyError:
            st.metric("🔴 EvolutionX", "R$ 0,00", "0.0%")
            st.markdown('<div style="margin-top: -10px; margin-bottom: 20px; opacity: 0.6; font-size: 0.8em;"><strong>MC:</strong> R$ 0,00 <strong>(0.0%)</strong></div>', unsafe_allow_html=True)

st.markdown("---")

# Opção de visualização (Faturamento vs Margem)
view_option = st.radio("Visualizar por:", ["Faturamento", "Margem de Contribuição"], horizontal=True)
value_column = 'Faturamento' if view_option == "Faturamento" else 'Margem Contrib. (=)'

# Abas para diferentes relatórios
tab1, tab2, tab3, tab4 = st.tabs([
    "💲 Faturamento", "📈 Desempenho por SKU", "🚚 Canal de Envio", "🏛️ Impostos"
])

with tab1:
    st.subheader("Vendas")
    
    # Agrupar por mês - Corrigido
    monthly_sales = filtered_df.groupby([filtered_df['Data'].dt.to_period('M')]).agg({
        value_column: 'sum',
        'ID da venda': 'count'
    }).reset_index()
    monthly_sales['Data_str'] = monthly_sales['Data'].astype(str)
    
    if not monthly_sales.empty:
        # Gráfico de vendas mensais
        fig_monthly = make_subplots(
            rows=2, cols=1,
            subplot_titles=[f'{view_option} Mensal', 'Quantidade de Vendas Mensais'],
            vertical_spacing=0.1
        )
        
        fig_monthly.add_trace(
            go.Bar(x=monthly_sales['Data_str'], y=monthly_sales[value_column], 
                   name=view_option, marker_color='#1f77b4'),
            row=1, col=1
        )
        
        fig_monthly.add_trace(
            go.Scatter(x=monthly_sales['Data_str'], y=monthly_sales['ID da venda'], 
                      mode='lines+markers', name='Quantidade', marker_color='#ff7f0e'),
            row=2, col=1
        )
        
        fig_monthly.update_layout(
            height=700, 
            showlegend=True,
            margin=dict(t=60, b=60, l=60, r=60)
        )
        fig_monthly.update_yaxes(title_text="Valor (R$)", row=1, col=1)
        fig_monthly.update_yaxes(title_text="Quantidade", row=2, col=1)
        
        st.plotly_chart(fig_monthly, use_container_width=True)
        
        # Tabela de vendas mensais
        display_monthly = monthly_sales.drop('Data', axis=1).rename(columns={'Data_str': 'Mês'})
        st.dataframe(display_monthly.style.format({value_column: 'R$ {:,.2f}'}), use_container_width=True)
    else:
        st.info("Nenhum dado encontrado para o período selecionado.")

    st.subheader("Pedidos")
    
    if not filtered_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Status dos pedidos
            if 'Status Pedido' in filtered_df.columns:
                status_count = filtered_df['Status Pedido'].value_counts()
                
                if not status_count.empty:
                    fig_status = px.pie(
                        values=status_count.values, names=status_count.index,
                        title='Status dos Pedidos'
                    )
                    st.plotly_chart(fig_status, use_container_width=True)
        
        with col2:
            # Pedidos por canal
            canal_count = filtered_df['Canal de Venda'].value_counts()
            
            if not canal_count.empty:
                fig_canal = px.bar(
                    x=canal_count.index, y=canal_count.values,
                    title='Pedidos por Canal de Venda'
                )
                st.plotly_chart(fig_canal, use_container_width=True)
        
        # Evolução diária de pedidos - Corrigido
        daily_orders = filtered_df.groupby(filtered_df['Data'].dt.date).agg({
            'ID da venda': 'count',
            'Faturamento': 'sum'
        }).reset_index()
        
        if not daily_orders.empty:
            fig_daily = make_subplots(
                rows=1, cols=2,
                subplot_titles=['Pedidos Diários (Qtd.)', 'Faturamento Diário (R$)']
            )
            
            fig_daily.add_trace(
                go.Scatter(x=daily_orders['Data'], y=daily_orders['ID da venda'], 
                          mode='lines+markers', name='Pedidos'),
                row=1, col=1
            )
            
            fig_daily.add_trace(
                go.Scatter(x=daily_orders['Data'], y=daily_orders['Faturamento'], 
                          mode='lines+markers', name='Faturamento', line=dict(color='orange')),
                row=1, col=2
            )
            
            fig_daily.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_daily, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Diário por Conta e Canal")
        
        # Criar relatório diário por conta e canal
        relatorio_diario = filtered_df.groupby([
            filtered_df['Data'].dt.date, 'Canal de Venda', 'Conta'
        ]).agg({
            'ID da venda': 'count',
            'Faturamento': 'sum'
        }).reset_index()
        relatorio_diario.columns = ['Data', 'Canal de Venda', 'Conta', 'Qtd. Vendas', 'Faturamento']
        
        if not relatorio_diario.empty:
            # Criar pivot para formato de tabela cruzada
            pivot_qtd = relatorio_diario.pivot_table(
                index='Data',
                columns=['Canal de Venda', 'Conta'],
                values='Qtd. Vendas',
                fill_value=0,
                aggfunc='sum'
            )
            
            pivot_fat = relatorio_diario.pivot_table(
                index='Data',
                columns=['Canal de Venda', 'Conta'],
                values='Faturamento',
                fill_value=0,
                aggfunc='sum'
            )
            
            # Adicionar totais por canal
            if not pivot_qtd.empty:
                # QUANTIDADE - Armazenar colunas originais antes de adicionar totais
                original_qtd_cols = pivot_qtd.columns.tolist()
                
                # Adicionar totais por canal
                for canal in pivot_qtd.columns.get_level_values(0).unique():
                    canal_cols = [col for col in pivot_qtd.columns if col[0] == canal]
                    pivot_qtd[(canal, 'Total')] = pivot_qtd[canal_cols].sum(axis=1)
                
                # Total Geral usando APENAS as colunas originais (sem os totais por canal)
                pivot_qtd[('Total Geral', '')] = pivot_qtd[original_qtd_cols].sum(axis=1)
                
                st.write("**Vendas Diárias (Qtd.)**")
                st.dataframe(pivot_qtd.style.format('{:,.0f}'), use_container_width=True)
                
                # FATURAMENTO - Armazenar colunas originais antes de adicionar totais
                original_fat_cols = pivot_fat.columns.tolist()
                
                # Adicionar totais por canal
                for canal in pivot_fat.columns.get_level_values(0).unique():
                    canal_cols = [col for col in pivot_fat.columns if col[0] == canal]
                    pivot_fat[(canal, 'Total')] = pivot_fat[canal_cols].sum(axis=1)
                
                # Total Geral usando APENAS as colunas originais (sem os totais por canal)
                pivot_fat[('Total Geral', '')] = pivot_fat[original_fat_cols].sum(axis=1)
                
                st.write("**Faturamento Diário (R$)**")
                st.dataframe(pivot_fat.style.format('R$ {:,.2f}'), use_container_width=True)
        else:
            st.info("Nenhum dado encontrado para o relatório diário.")
    else:
        st.info("Nenhum dado encontrado para o período selecionado.")

    

with tab2:
    st.subheader("Desempenho de Vendas por SKU")
    
    # Novo filtro de pesquisa para SKUs e Descrição
    col_search1, col_search2, col_select = st.columns([1, 1, 2])

    with col_search1:
        search_term = st.text_input("Buscar SKU:", key="sku_search")

    with col_search2:
        desc_search_term = st.text_input("Buscar Descrição:", key="desc_search")

    # Garantir que os SKUs sejam tratados como texto e criar mapeamento consistente
    filtered_df_copy = filtered_df.copy()
    filtered_df_copy['SKU'] = filtered_df_copy['SKU'].astype(str)
    filtered_df_copy['Descrição do Produto'] = filtered_df_copy['Descrição do Produto'].astype(str).fillna('Sem descrição')

    # Criar lista de SKUs únicos com suas descrições (usando SKUs como string)
    sku_desc_mapping = filtered_df_copy.groupby('SKU')['Descrição do Produto'].first().to_dict()
    available_skus = sorted(filtered_df_copy['SKU'].unique())

    # Filtrar SKUs baseado na busca por SKU ou Descrição
    if search_term or desc_search_term:
        filtered_skus = []
        for sku in available_skus:
            try:
                sku_match = search_term.upper() in sku.upper() if search_term else True
                desc_match = desc_search_term.upper() in sku_desc_mapping[sku].upper() if desc_search_term else True
                if sku_match and desc_match:
                    filtered_skus.append(sku)
            except KeyError:
                # Pular SKUs que não têm descrição mapeada
                continue
        available_skus = filtered_skus

    with col_select:
        # Criar opções que mostram SKU + Descrição com tratamento de erro
        sku_options = []
        for sku in available_skus:
            try:
                desc = sku_desc_mapping.get(sku, 'Sem descrição')
                if len(desc) > 50:
                    option = f"{sku} - {desc[:50]}..."
                else:
                    option = f"{sku} - {desc}"
                sku_options.append(option)
            except (KeyError, TypeError):
                # Se houver erro, usar apenas o SKU
                sku_options.append(f"{sku} - Sem descrição")
        
        selected_sku_options = st.multiselect(
            "Selecionar SKUs:",
            options=sku_options,
            default=sku_options[:5] if len(sku_options) <= 5 else sku_options[:3],
            key="sku_multiselect"
        )
        
        # Extrair apenas os SKUs das opções selecionadas
        selected_skus = [option.split(" - ")[0] for option in selected_sku_options]

    # Filtrar dados pelos SKUs selecionados
    if selected_skus:
        filtered_sku_df = filtered_df[filtered_df['SKU'].astype(str).isin(selected_skus)]
    else:
        filtered_sku_df = filtered_df

    st.markdown("---")
    
    # Resto do código continua normalmente...
    if not filtered_df.empty:
        
        # NOVO: Gráficos de SKUs por mês com filtro

        # Adicionar descrição aos dados filtrados
        filtered_sku_df_with_desc = filtered_sku_df.copy()
        sku_desc_map = filtered_sku_df.groupby('SKU')['Descrição do Produto'].first().to_dict()
        filtered_sku_df_with_desc['SKU_Desc'] = filtered_sku_df_with_desc['SKU'].map(sku_desc_map)

        if not filtered_sku_df.empty and selected_skus:
            # SKUs por quantidade mensal
            
            sku_monthly_qty = filtered_sku_df_with_desc.groupby([filtered_sku_df_with_desc['Data'].dt.to_period('M'), 'SKU_Desc']).agg({
                'Qtd.': 'sum'
            }).reset_index()
            sku_monthly_qty['Mês'] = sku_monthly_qty['Data'].dt.strftime('%B')
            
            if not sku_monthly_qty.empty:
                fig_sku_qty = px.bar(
                    sku_monthly_qty, x='Mês', y='Qtd.', color='SKU_Desc',  # ← Corrigido
                    title='Quantidade',
                    labels={'Mês': 'Mês', 'Qtd.': 'Qtd.', 'SKU_Desc': 'SKU - Descrição'}  # ← Corrigido
                )

                fig_sku_qty.update_layout(height=600)
                st.plotly_chart(fig_sku_qty, use_container_width=True)
            
            # SKUs por faturamento mensal
            sku_monthly_revenue = filtered_sku_df_with_desc.groupby([filtered_sku_df_with_desc['Data'].dt.to_period('M'), 'SKU_Desc']).agg({
                'Faturamento': 'sum'
            }).reset_index()
            sku_monthly_revenue['Mês'] = sku_monthly_revenue['Data'].dt.strftime('%B')
            
            if not sku_monthly_revenue.empty:
                fig_sku_revenue = px.bar(
                    sku_monthly_revenue, x='Mês', y='Faturamento', color='SKU_Desc',  # ← Corrigido
                    title='Faturamento',
                    labels={'Mês': 'Mês', 'Faturamento': 'R$', 'SKU_Desc': 'SKU - Descrição'}  # ← Corrigido
                )

                fig_sku_revenue.update_layout(height=600)
                st.plotly_chart(fig_sku_revenue, use_container_width=True)
        else:
            st.info("Selecione pelo menos um SKU para visualizar a evolução mensal.")  
        
        # NOVO: Gráficos de barras agrupadas por SKU
    st.markdown("---")

    if not filtered_sku_df.empty and selected_skus:
        # Preparar dados para gráficos agrupados
        monthly_comparison = filtered_sku_df.groupby([
            filtered_sku_df['Data'].dt.to_period('M'), 'SKU', 'Descrição do Produto'
        ]).agg({
            'Qtd.': 'sum',
            'Faturamento': 'sum'
        }).reset_index()
        
        # Converter período para string legível
        monthly_comparison['Mês'] = monthly_comparison['Data'].dt.strftime('%b %Y')
        
        # Criar coluna combinada SKU + Descrição (abreviada)
        monthly_comparison['SKU_Label'] = monthly_comparison.apply(
            lambda row: f"{row['SKU']} - {row['Descrição do Produto'][:100]}{'...' if len(row['Descrição do Produto']) > 100 else ''}", 
            axis=1
        )
        
        if not monthly_comparison.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                # Gráfico de Quantidade Agrupado
                fig_qty_grouped = px.bar(
                    monthly_comparison, 
                    x="Mês", 
                    y="Qtd.", 
                    color="SKU_Label",
                    barmode="group",
                    title="Quantidade",
                    labels={
                        'Mês': 'Mês',
                        'Qtd.': 'Quantidade',
                        'SKU_Label': 'SKU - Descrição'
                    },
                    # Ordenar meses cronologicamente
                    category_orders={
                        "Mês": sorted(monthly_comparison['Mês'].unique(), 
                                    key=lambda x: monthly_comparison[monthly_comparison['Mês'] == x]['Data'].iloc[0])
                    }
                )
                fig_qty_grouped.update_layout(
                    height=500,
                    legend=dict(
                        orientation="v",
                        yanchor="top",
                        y=1,
                        xanchor="left",
                        x=1.02
                    ),
                    margin=dict(r=200)  # Margem direita para a legenda
                )
                st.plotly_chart(fig_qty_grouped, use_container_width=True)
            
            with col2:
                # Gráfico de Faturamento Agrupado
                fig_revenue_grouped = px.bar(
                    monthly_comparison, 
                    x="Mês", 
                    y="Faturamento", 
                    color="SKU_Label",
                    barmode="group",
                    title="Faturamento",
                    labels={
                        'Mês': 'Mês',
                        'Faturamento': 'Faturamento (R$)',
                        'SKU_Label': 'SKU - Descrição'
                    },
                    # Ordenar meses cronologicamente
                    category_orders={
                        "Mês": sorted(monthly_comparison['Mês'].unique(), 
                                    key=lambda x: monthly_comparison[monthly_comparison['Mês'] == x]['Data'].iloc[0])
                    }
                )
                fig_revenue_grouped.update_layout(
                    height=500,
                    legend=dict(
                        orientation="v",
                        yanchor="top",
                        y=1,
                        xanchor="left",
                        x=1.02
                    ),
                    margin=dict(r=200)  # Margem direita para a legenda
                )
                st.plotly_chart(fig_revenue_grouped, use_container_width=True)
            
            # ADICIONAL: Versão com facetas por Canal de Venda (se houver múltiplos canais)
            if len(filtered_sku_df['Canal de Venda'].unique()) > 1:
                st.markdown("---")
                st.subheader("Por Canal de Venda")
                
                # Preparar dados com canal
                monthly_channel_comparison = filtered_sku_df.groupby([
                    filtered_sku_df['Data'].dt.to_period('M'), 'SKU', 'Canal de Venda', 'Descrição do Produto'
                ]).agg({
                    'Qtd.': 'sum',
                    'Faturamento': 'sum'
                }).reset_index()
                
                monthly_channel_comparison['Mês'] = monthly_channel_comparison['Data'].dt.strftime('%b %Y')
                monthly_channel_comparison['SKU_Label'] = monthly_channel_comparison.apply(
                    lambda row: f"{row['SKU']} - {row['Descrição do Produto'][:15]}{'...' if len(row['Descrição do Produto']) > 15 else ''}", 
                    axis=1
                )
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Quantidade com facetas por canal
                    fig_qty_facet = px.bar(
                        monthly_channel_comparison,
                        x="Mês", 
                        y="Qtd.", 
                        color="SKU_Label",
                        facet_col="Canal de Venda",
                        barmode="group",
                        title="Quantidade",
                        labels={
                            'Mês': 'Mês',
                            'Qtd.': 'Quantidade',
                            'SKU_Label': 'SKU - Descrição',
                            'Canal de Venda': 'Canal'
                        },
                        category_orders={
                            "Mês": sorted(monthly_channel_comparison['Mês'].unique(), 
                                        key=lambda x: monthly_channel_comparison[monthly_channel_comparison['Mês'] == x]['Data'].iloc[0])
                        }
                    )
                    fig_qty_facet.update_layout(height=500)
                    st.plotly_chart(fig_qty_facet, use_container_width=True)
                
                with col2:
                    # Faturamento com facetas por canal
                    fig_revenue_facet = px.bar(
                        monthly_channel_comparison,
                        x="Mês", 
                        y="Faturamento", 
                        color="SKU_Label",
                        facet_col="Canal de Venda",
                        barmode="group",
                        title="Faturamento",
                        labels={
                            'Mês': 'Mês',
                            'Faturamento': 'Faturamento (R$)',
                            'SKU_Label': 'SKU - Descrição',
                            'Canal de Venda': 'Canal'
                        },
                        category_orders={
                            "Mês": sorted(monthly_channel_comparison['Mês'].unique(), 
                                        key=lambda x: monthly_channel_comparison[monthly_channel_comparison['Mês'] == x]['Data'].iloc[0])
                        }
                    )
                    fig_revenue_facet.update_layout(height=500)
                    st.plotly_chart(fig_revenue_facet, use_container_width=True)

            # Tabela completa

            st.markdown("---")
            
            st.subheader("Margem de Contribuição por SKU")
            
        else:
            st.info("Nenhum dado encontrado para o período selecionado.")

        if not filtered_df.empty:
            # Filtro de pesquisa para a tabela
            col_search_sku, col_search_desc = st.columns(2)

            with col_search_sku:
                table_sku_search = st.text_input("Buscar SKU:", key="table_sku_search")

            with col_search_desc:
                table_desc_search = st.text_input("Buscar Descrição:", key="table_desc_search")
            
            # Aplicar filtros de pesquisa na tabela
            table_filtered_df = filtered_df.copy()

            if table_sku_search:
                table_filtered_df = table_filtered_df[
                    table_filtered_df['SKU'].astype(str).str.contains(table_sku_search, case=False, na=False)
                ]

            if table_desc_search:
                table_filtered_df = table_filtered_df[
                    table_filtered_df['Descrição do Produto'].astype(str).str.contains(table_desc_search, case=False, na=False)
                ]
            
            # Definir todas as colunas disponíveis na ordem correta
            all_columns = [
                'SKU', 'Descrição do Produto', 'Faturamento', 'Qtd.', 'Valor Unit.',
                'Custo (-) Total', 'Custo (-) Unitário', 'Imposto (-) Total', 'Imposto (-) Unitário',
                'Frete Vendedor (-)', 'Tarifa de Venda (-) Total', 'Tarifa de Venda (-) Unitária',
                'Margem Contrib. (=) Total', 'Margem Contrib. (=) Unitária', 'MC em %'
            ]
            
            # Colunas visíveis por padrão (com as modificações solicitadas)
            default_visible_columns = [
                'Descrição do Produto', 'Faturamento', 'Qtd.', 'Valor Unit.',
                'Custo (-) Unitário', 'Imposto (-) Unitário', 'Tarifa de Venda (-) Unitária',
                'Margem Contrib. (=) Unitária', 'MC em %'
            ]
            
            # Seletor de colunas (expansível)
            with st.expander("Selecione as colunas para exibir"):
                selected_columns = st.multiselect(
                    "Escolha as colunas:",
                    options=all_columns,
                    default=default_visible_columns,
                    key="table_columns"
                )
            
            # Agrupar dados por SKU com cálculos corretos
            resumo_sku = table_filtered_df.groupby('SKU').agg({
                'Descrição do Produto': 'first',
                'Faturamento': 'sum',
                'Qtd.': 'sum',
                'Valor Unit.': 'mean',
                'Custo (-)': ['sum', 'mean'],
                'Imposto (-)': ['sum', 'mean'],
                'Frete Vendedor (-)': 'mean',
                'Tarifa de Venda (-)': ['sum', 'mean'],
                'Margem Contrib. (=)': ['sum', 'mean']
            }).reset_index()

            # Achatar colunas multi-nível
            resumo_sku.columns = [
                'SKU', 'Descrição do Produto',
                'Faturamento', 'Qtd.', 'Valor Unit.',
                'Custo (-) Total', 'Custo (-) Unitário',
                'Imposto (-) Total', 'Imposto (-) Unitário',
                'Frete Vendedor (-)', 
                'Tarifa de Venda (-) Total', 'Tarifa de Venda (-) Unitária',
                'Margem Contrib. (=) Total', 'Margem Contrib. (=) Unitária'
            ]
            
            # CORREÇÃO: Calcular MC em % corretamente baseado nos totais agrupados
            # MC% = (Margem Total / Faturamento Total) * 100
            resumo_sku['MC em %'] = np.where(
                resumo_sku['Faturamento'] > 0,
                (resumo_sku['Margem Contrib. (=) Total'] / resumo_sku['Faturamento']) * 100,
                0
            )

            # Filtrar apenas as colunas selecionadas mantendo a ordem original
            ordered_selected_columns = [col for col in all_columns if col in selected_columns]
            display_resumo = resumo_sku[ordered_selected_columns]

            def color_mc(val):
                if pd.isna(val):
                    return ''
                if val <= 20:
                    return 'background-color:#FF0000'
                elif val < 30:
                    return 'background-color:#C7AF00'
                elif val < 40:
                    return 'background-color:#00C700'
                else:
                    return 'background-color:#00D9FF'

            # Criar dicionário de formatação dinâmico baseado nas colunas selecionadas
            format_dict = {}
            for col in selected_columns:
                if col in ['Faturamento', 'Custo (-) Total', 'Custo (-) Unitário', 'Imposto (-) Total', 
                        'Imposto (-) Unitário', 'Valor Unit.', 'Frete Vendedor (-)',
                        'Tarifa de Venda (-) Total', 'Tarifa de Venda (-) Unitária',
                        'Margem Contrib. (=) Total', 'Margem Contrib. (=) Unitária']:
                    format_dict[col] = 'R$ {:,.2f}'
                elif col == 'Qtd.':
                    format_dict[col] = '{:,.0f}'
                elif col == 'MC em %':
                    format_dict[col] = '{:.1f}%'

            # Aplicar formatação e coloração
            if 'MC em %' in selected_columns:
                styled = display_resumo.style.format(format_dict).applymap(color_mc, subset=['MC em %'])
            else:
                styled = display_resumo.style.format(format_dict)

            # Exibir tabela
            st.dataframe(styled, use_container_width=True, hide_index=True)

            st.markdown("""
            **Legenda:**
            - 🔴 ≤ 20%
            - 🟡 > 20% e < 30%
            - 🟢 ≥ 30% e < 40%
            - 🔵 ≥ 40%
            """)
        else:
            st.info("Nenhum dado encontrado para o período selecionado.")
        
        st.subheader("📈 Top SKUs por Mês")

        if not filtered_df.empty:
            mensal_sku = filtered_df.groupby([filtered_df['Data'].dt.to_period('M'), 'SKU']).agg({
                'Descrição do Produto': 'first',  # Adicionar esta linha
                'Faturamento': 'sum',
                'Qtd.': 'sum'
            }).reset_index()
            mensal_sku['Mês'] = mensal_sku['Data'].dt.strftime('%b %Y')

            # Criar coluna combinada para exibição
            # Converter SKU para string e criar coluna combinada
            # Converter para string e tratar valores nulos
            mensal_sku['SKU'] = mensal_sku['SKU'].astype(str)
            mensal_sku['Descrição do Produto'] = mensal_sku['Descrição do Produto'].fillna('Sem descrição').astype(str)

            # Criar coluna combinada com tratamento de tamanho
            mensal_sku['SKU_Desc'] = mensal_sku.apply(
                lambda row: f"{row['SKU']} - {row['Descrição do Produto'][:30]}{'...' if len(row['Descrição do Produto']) > 30 else ''}", 
                axis=1
            )
            if not mensal_sku.empty:
                top_rev = mensal_sku.nlargest(20, 'Faturamento')
                top_qtd = mensal_sku.nlargest(20, 'Qtd.')

                col1, col2 = st.columns(2)

                with col1:
                    fig_rev = px.bar(top_rev, x='Faturamento', y='SKU_Desc', color='Mês', orientation='h',  # Alterar 'SKU' para 'SKU_Desc'
                                    title='Top 20 SKUs por Faturamento (Mensal)',
                                    labels={'Faturamento': 'Faturamento (R$)', 'SKU_Desc': 'SKU - Descrição'})
                    fig_rev.update_layout(height=800)
                    st.plotly_chart(fig_rev, use_container_width=True)

                with col2:
                    fig_qtd = px.bar(top_qtd, x='Qtd.', y='SKU_Desc', color='Mês', orientation='h',  # Alterar 'SKU' para 'SKU_Desc'
                                    title='Top 20 SKUs por Quantidade (Mensal)',
                                    labels={'Qtd.': 'Quantidade', 'SKU_Desc': 'SKU - Descrição'})
                    fig_qtd.update_layout(height=800)
                    st.plotly_chart(fig_qtd, use_container_width=True)
            else:
                st.info("Nenhum dado encontrado para o período selecionado.")
        else:
            st.info("Nenhum dado encontrado para o período selecionado.")

with tab3:
    st.subheader("Canal de Envio")
    
    if not filtered_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # NOVO: Gráfico de pizza da distribuição de fretes por quantidade de pedidos
            if 'Frete' in filtered_df.columns:
                frete_distribution = filtered_df['Frete'].value_counts()
                
                if not frete_distribution.empty:
                    fig_frete_dist = px.pie(
                        values=frete_distribution.values, 
                        names=frete_distribution.index,
                        title='Distribuição de Fretes por Quantidade de Pedidos'
                    )
                    st.plotly_chart(fig_frete_dist, use_container_width=True)   
                else:
                    st.info("Nenhum dado encontrado para o período selecionado.")         
                

with tab4:
    st.subheader("Análise de Impostos")
    
    if not filtered_df.empty:
        # CORREÇÃO: Filtrar pedidos com lógica específica por mês
        if 'Status Pedido' in filtered_df.columns:
            # Criar dataframe para análise com lógica condicional por mês
            def apply_tax_filter(df):
                """Aplica filtro de impostos baseado no mês específico"""
                result_df = pd.DataFrame()
                
                for period, group in df.groupby(df['Data'].dt.to_period('M')):
                    # Exceções: Abril, Maio e Junho de 2025 - considerar todos os pedidos
                    if (period.year == 2025 and period.month in [4, 5, 6]):
                        # Para estes meses, usar todos os pedidos
                        filtered_group = group.copy()
                        filter_info = "todos os pedidos"
                    else:
                        # Para outros meses, usar apenas pedidos pagos
                        filtered_group = group[group['Status Pedido'] == 'Pago'].copy()
                        filter_info = "apenas pedidos pagos"
                    
                    # Adicionar informação do filtro aplicado
                    filtered_group['Filtro_Aplicado'] = filter_info
                    result_df = pd.concat([result_df, filtered_group], ignore_index=True)
                
                return result_df
            
            tax_filtered_df = apply_tax_filter(filtered_df)
            
            if tax_filtered_df.empty:
                st.warning("Nenhum dado encontrado após aplicar os filtros de impostos.")
                st.info("Verificando status disponíveis:")
                st.write(filtered_df['Status Pedido'].value_counts())
            else:
                # Mostrar informações sobre os filtros aplicados
                filter_summary = tax_filtered_df.groupby([
                    tax_filtered_df['Data'].dt.to_period('M').astype(str), 'Filtro_Aplicado'
                ]).size().reset_index(name='Quantidade')
                
                with st.expander("ℹ️"):
                    st.dataframe(filter_summary, use_container_width=True, hide_index=True)
                    st.caption("**Abril, Maio e Junho/2025:** Todos os pedidos | **Demais meses:** Apenas pedidos pagos")
                
                st.info(f"Analisando {len(tax_filtered_df)} pedidos de um total de {len(filtered_df)} pedidos (com filtros específicos por mês).")
                
                # Impostos por período - COM FILTROS ESPECÍFICOS POR MÊS
                tax_analysis = tax_filtered_df.groupby(tax_filtered_df['Data'].dt.to_period('M')).agg({
                    'Imposto (-)': 'sum',
                    'Faturamento': 'sum'
                }).reset_index()
                
                tax_analysis['Data_str'] = tax_analysis['Data'].astype(str)
                
                # CORREÇÃO: Calcular percentual correto de impostos sobre faturamento
                tax_analysis['% Imposto'] = np.where(
                    tax_analysis['Faturamento'] > 0,
                    (tax_analysis['Imposto (-)'] / tax_analysis['Faturamento'] * 100),
                    0
                )
                
                if not tax_analysis.empty:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig_tax_value = px.bar(
                            tax_analysis, x='Data_str', y='Imposto (-)',
                            title='Impostos por Mês (R$)',
                            labels={'Data_str': 'Mês', 'Imposto (-)': 'Impostos (R$)'}
                        )
                        fig_tax_value.update_layout(
                            yaxis_tickformat=',.2f',
                            yaxis_title='Impostos (R$)'
                        )
                        st.plotly_chart(fig_tax_value, use_container_width=True)
                    
                    with col2:
                        fig_tax_perc = px.line(
                            tax_analysis, x='Data_str', y='% Imposto',
                            title='Impostos sobre Faturamento Bruto (%)',
                            markers=True,
                            labels={'Data_str': 'Mês', '% Imposto': 'Percentual de Impostos (%)'}
                        )
                        fig_tax_perc.update_layout(
                            yaxis_tickformat='.2f',
                            yaxis_title='Percentual de Impostos (%)'
                        )
                        st.plotly_chart(fig_tax_perc, use_container_width=True)
                
                # Impostos por canal e conta - COM FILTROS ESPECÍFICOS POR MÊS
                tax_breakdown = tax_filtered_df.groupby(['Canal de Venda', 'Conta']).agg({
                    'Imposto (-)': 'sum',
                    'Faturamento': 'sum',
                    'ID da venda': 'count'
                }).reset_index()
                
                # Renomear coluna para clareza
                tax_breakdown = tax_breakdown.rename(columns={'ID da venda': 'Qtd. Pedidos'})
                
                # Calcular percentual correto
                tax_breakdown['% Imposto'] = np.where(
                    tax_breakdown['Faturamento'] > 0,
                    (tax_breakdown['Imposto (-)'] / tax_breakdown['Faturamento'] * 100),
                    0
                )
                
                if not tax_breakdown.empty:
                    st.subheader("Impostos por Canal de Venda e Conta")
                    st.caption("*Abril, Maio e Junho/2025: todos os pedidos | Demais meses: apenas pedidos pagos")
                    st.dataframe(
                        tax_breakdown.style.format({
                            'Imposto (-)': 'R$ {:,.2f}',
                            'Faturamento': 'R$ {:,.2f}',
                            '% Imposto': '{:.2f}%',
                            'Qtd. Pedidos': '{:,.0f}'
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Adicionar resumo estatístico
                    st.subheader("Resumo")
                    
                    total_impostos = tax_filtered_df['Imposto (-)'].sum()
                    total_faturamento = tax_filtered_df['Faturamento'].sum()
                    percentual_medio = (total_impostos / total_faturamento * 100) if total_faturamento > 0 else 0
                    total_pedidos_filtrados = len(tax_filtered_df)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Impostos", f"R$ {total_impostos:,.2f}")
                    
                    with col2:
                        st.metric("Faturamento Bruto", f"R$ {total_faturamento:,.2f}")
                    
                    with col3:
                        st.metric("% Médio de Impostos", f"{percentual_medio:.2f}%")
                    
                    with col4:
                        st.metric("Pedidos Analisados", f"{total_pedidos_filtrados:,}")
                
        else:
            st.error("Coluna 'Status Pedido' não encontrada no dataset.")
            st.info("Colunas disponíveis:")
            st.write(list(filtered_df.columns))
    else:
        st.info("Nenhum dado encontrado para o período selecionado.")