import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
from streamlit_option_menu import option_menu

# --- CONFIGURAÇÃO DE ALTO NÍVEL ---
st.set_page_config(page_title="EggGestão Midnight Pro v2", layout="wide", page_icon="🥚")

# --- CSS DARK TOTAL ---
st.markdown("""
    <style>
    .stApp { background-color: #0F172A !important; color: #F8FAFC !important; }
    h1, h2, h3, h4, h5, h6, p, label, span, div { color: #F8FAFC !important; }
    [data-testid="stSidebar"] { background-color: #020617 !important; border-right: 1px solid #1E293B; }
    div[data-testid="stMetric"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        padding: 20px !important;
        border-radius: 15px !important;
    }
    div[data-testid="stMetricValue"] > div { color: #FBBF24 !important; font-weight: 800 !important; }
    .stButton>button {
        background: linear-gradient(135deg, #FBBF24 0%, #D97706 100%) !important;
        color: #0F172A !important; font-weight: 700 !important; border: none !important;
        border-radius: 10px !important; width: 100% !important;
    }
    .card-dark { background-color: #1E293B; padding: 20px; border-radius: 15px; border: 1px solid #334155; margin-bottom: 20px; }
    .stDataFrame { background-color: #1E293B !important; }
    </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('ovos_midnight_v2.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY, nome TEXT, tel TEXT, endereco TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS estoque (produto TEXT PRIMARY KEY, qtd INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vendas (id INTEGER PRIMARY KEY, cli_id INTEGER, data TEXT, prod TEXT, valor REAL, qtd INTEGER, total REAL, pago REAL, pendente REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS despesas (id INTEGER PRIMARY KEY, data TEXT, descricao TEXT, valor REAL)''')
    
    prods = ["Branco Extra", "Vermelho Extra", "Branco Grande", "Vermelho Grande", "Branco Médio", "Vermelho Médio", "Branco Jumbo", "Vermelho Jumbo"]
    for p in prods:
        c.execute("INSERT OR IGNORE INTO estoque (produto, qtd) VALUES (?, 0)", (p,))
    conn.commit()
    return conn

conn = init_db()

# --- FUNÇÕES AUXILIARES ---
def get_estoque_disponivel():
    return pd.read_sql_query("SELECT produto, qtd FROM estoque WHERE qtd > 0", conn)

def excluir_venda(venda_id, produto, qtd_retorno):
    conn.execute("DELETE FROM vendas WHERE id = ?", (venda_id,))
    conn.execute("UPDATE estoque SET qtd = qtd + ? WHERE produto = ?", (qtd_retorno, produto))
    conn.commit()
    st.toast("Venda removida e estoque estornado!", icon="🗑️")
    st.rerun()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h1 style='color:#FBBF24; text-align:center;'>🥚 EGG Midnight</h1>", unsafe_allow_html=True)
    menu = option_menu(None, ["Home", "Vendas", "Estoque", "Financeiro", "Clientes"],
        icons=['house', 'cart3', 'box', 'currency-dollar', 'person-badge'],
        styles={"nav-link-selected": {"background-color": "#FBBF24", "color": "#0F172A"}})

# --- HOME ---
if menu == "Home":
    st.markdown("<h2 style='color:#FBBF24;'>📊 Painel de Controle</h2>", unsafe_allow_html=True)
    
    df_v = pd.read_sql_query("SELECT * FROM vendas", conn)
    df_d = pd.read_sql_query("SELECT * FROM despesas", conn)
    
    receita = df_v['total'].sum() if not df_v.empty else 0
    despesas = df_d['valor'].sum() if not df_d.empty else 0
    lucro = receita - despesas
    pendente = df_v['pendente'].sum() if not df_v.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Receita Total", f"R$ {receita:,.2f}")
    c2.metric("Despesas", f"R$ {despesas:,.2f}", delta_color="inverse")
    c3.metric("Lucro Estimado", f"R$ {lucro:,.2f}")
    c4.metric("Contas a Receber", f"R$ {pendente:,.2f}")

    # Gráfico de Calendário de Receita
    if not df_v.empty:
        st.markdown("### 📅 Calendário de Receita (Últimos 30 dias)")
        df_v['data'] = pd.to_datetime(df_v['data'])
        df_daily = df_v.groupby('data')['total'].sum().reset_index()
        fig = px.bar(df_daily, x='data', y='total', title="Faturamento Diário",
                     color_discrete_sequence=['#FBBF24'], template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

# --- VENDAS (SISTEMA INTELIGENTE) ---
elif menu == "Vendas":
    st.markdown("<h2 style='color:#FBBF24;'>🛒 Nova Venda</h2>", unsafe_allow_html=True)
    
    df_est_disp = get_estoque_disponivel()
    df_cli = pd.read_sql_query("SELECT * FROM clientes", conn)

    if df_cli.empty:
        st.warning("Cadastre um cliente antes de vender.")
    elif df_est_disp.empty:
        st.error("❌ ESTOQUE ZERADO! Abasteça o estoque primeiro.")
    else:
        with st.form("venda_form"):
            col1, col2 = st.columns(2)
            cliente = col1.selectbox("Selecione o Cliente", df_cli['nome'].tolist())
            produto = col2.selectbox("Produto Disponível (Estoque)", df_est_disp['produto'].tolist())
            
            qtd_max = int(df_est_disp[df_est_disp['produto'] == produto]['qtd'].values[0])
            
            c1, c2, c3 = st.columns(3)
            qtd = c1.number_input(f"Quantidade (Max: {qtd_max})", min_value=1, max_value=qtd_max, step=1)
            preco = c2.number_input("Preço por Unidade (R$)", min_value=0.0, value=15.0)
            pago = c3.number_input("Valor Pago Agora (R$)", min_value=0.0, value=preco*qtd)
            
            if st.form_submit_button("FINALIZAR VENDA"):
                total = preco * qtd
                cli_id = int(df_cli[df_cli['nome'] == cliente]['id'].values[0])
                data_hoje = date.today().strftime("%Y-%m-%d")
                
                conn.execute("INSERT INTO vendas (cli_id, data, prod, valor, qtd, total, pago, pendente) VALUES (?,?,?,?,?,?,?,?)",
                            (cli_id, data_hoje, produto, preco, qtd, total, pago, total-pago))
                conn.execute("UPDATE estoque SET qtd = qtd - ? WHERE produto = ?", (qtd, produto))
                conn.commit()
                st.success(f"Venda de {produto} realizada com sucesso!")
                st.balloons()
                st.rerun()

# --- FINANCEIRO & RELATÓRIOS DIÁRIOS ---
elif menu == "Financeiro":
    tab1, tab2, tab3 = st.tabs(["📊 Relatório Diário", "💸 Fluxo de Caixa", "📉 Despesas"])

    with tab1:
        st.markdown("### 📅 Resumo do Dia")
        hoje = date.today().strftime("%Y-%m-%d")
        df_hoje = pd.read_sql_query(f"SELECT * FROM vendas WHERE data = '{hoje}'", conn)
        
        if df_hoje.empty:
            st.info("Nenhuma venda hoje.")
        else:
            r1, r2, r3 = st.columns(3)
            r1.metric("Vendido Hoje", f"R$ {df_hoje['total'].sum():,.2f}")
            r2.metric("Recebido Hoje", f"R$ {df_hoje['pago'].sum():,.2f}")
            r3.metric("Pendente Hoje", f"R$ {df_hoje['pendente'].sum():,.2f}")
            st.dataframe(df_hoje[['prod', 'qtd', 'total', 'pago', 'pendente']], use_container_width=True)

    with tab2:
        st.markdown("### 📋 Histórico Geral de Vendas")
        df_f = pd.read_sql_query('''
            SELECT v.id, v.data, c.nome as cliente, v.prod, v.qtd, v.total, v.pago, v.pendente 
            FROM vendas v JOIN clientes c ON v.cli_id = c.id ORDER BY v.data DESC
        ''', conn)
        st.dataframe(df_f, use_container_width=True)

    with tab3:
        st.markdown("### 🧾 Gestão de Despesas")
        with st.form("add_despesa"):
            c1, c2, c3 = st.columns([2,1,1])
            desc = c1.text_input("Descrição da Despesa (Ex: Milho, Luz, Embalagem)")
            val = c2.number_input("Valor (R$)", min_value=0.0)
            if st.form_submit_button("Registrar Despesa"):
                conn.execute("INSERT INTO despesas (data, descricao, valor) VALUES (?,?,?)", 
                             (date.today().strftime("%Y-%m-%d"), desc, val))
                conn.commit()
                st.rerun()
        
        df_desp = pd.read_sql_query("SELECT * FROM despesas ORDER BY data DESC", conn)
        st.table(df_desp)

# --- ESTOQUE ---
elif menu == "Estoque":
    st.markdown("<h2 style='color:#FBBF24;'>📦 Gestão de Estoque</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 2])
    with col1:
        with st.form("add_est"):
            p_sel = st.selectbox("Produto", pd.read_sql_query("SELECT produto FROM estoque", conn)['produto'].tolist())
            q_add = st.number_input("Adicionar Quantidade", min_value=1)
            if st.form_submit_button("Abastecer"):
                conn.execute("UPDATE estoque SET qtd = qtd + ? WHERE produto = ?", (q_add, p_sel))
                conn.commit()
                st.success("Estoque atualizado!")
                st.rerun()
    with col2:
        df_e = pd.read_sql_query("SELECT produto as 'Produto', qtd as 'Saldo Atual' FROM estoque", conn)
        # Destacar estoque baixo
        st.dataframe(df_e.style.applymap(lambda x: 'color: #F87171' if isinstance(x, int) and x < 10 else '', subset=['Saldo Atual']), 
                     use_container_width=True)

# --- CLIENTES ---
elif menu == "Clientes":
    st.markdown("<h2 style='color:#FBBF24;'>👤 Cadastro de Clientes</h2>", unsafe_allow_html=True)
    with st.form("cli"):
        c1, c2 = st.columns(2)
        n = c1.text_input("Nome do Cliente / Granja")
        t = c2.text_input("WhatsApp")
        e = st.text_input("Endereço de Entrega")
        if st.form_submit_button("Cadastrar Cliente"):
            conn.execute("INSERT INTO clientes (nome, tel, endereco) VALUES (?,?,?)", (n,t,e))
            conn.commit()
            st.success("Cliente cadastrado!")
            st.rerun()
    
    st.markdown("### Lista de Clientes")
    st.dataframe(pd.read_sql_query("SELECT id, nome, tel, endereco FROM clientes", conn), use_container_width=True)
