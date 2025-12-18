import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, date
from streamlit_option_menu import option_menu

# --- CONFIGURAÇÃO DE ALTO NÍVEL ---
st.set_page_config(page_title="EggGestão Midnight Pro", layout="wide", page_icon="🥚")

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
    .card-dark { background-color: #1E293B; padding: 25px; border-radius: 15px; border: 1px solid #334155; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('ovos_midnight.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY, nome TEXT, tel TEXT, endereco TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS estoque (produto TEXT PRIMARY KEY, qtd INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vendas (id INTEGER PRIMARY KEY, cli_id INTEGER, data TEXT, prod TEXT, valor REAL, qtd INTEGER, total REAL, pago REAL, pendente REAL)''')
    prods = ["Branco Extra", "Vermelho Extra", "Branco Grande", "Vermelho Grande", "Branco Médio", "Vermelho Médio", "Branco Jumbo", "Vermelho Jumbo"]
    for p in prods:
        c.execute("INSERT OR IGNORE INTO estoque (produto, qtd) VALUES (?, 0)", (p,))
    conn.commit()
    return conn

conn = init_db()

# --- FUNÇÕES DE MANIPULAÇÃO ---
def excluir_venda(venda_id, produto, qtd_retorno):
    # Deleta a venda
    conn.execute("DELETE FROM vendas WHERE id = ?", (venda_id,))
    # Devolve a quantidade ao estoque
    conn.execute("UPDATE estoque SET qtd = qtd + ? WHERE produto = ?", (qtd_retorno, produto))
    conn.commit()
    st.toast(f"Venda #{venda_id} removida e estoque devolvido!", icon="🗑️")
    st.rerun()

@st.dialog("Editar Venda")
def editar_venda_modal(venda):
    st.write(f"Editando Venda #{venda['id']}")
    novo_valor = st.number_input("Preço Unitário (R$)", value=float(venda['valor']))
    novo_pago = st.number_input("Valor Pago (R$)", value=float(venda['pago']))
    
    if st.button("Salvar Alterações"):
        novo_total = novo_valor * venda['qtd']
        novo_pendente = novo_total - novo_pago
        conn.execute("""UPDATE vendas SET valor=?, total=?, pago=?, pendente=? WHERE id=?""", 
                     (novo_valor, novo_total, novo_pago, novo_pendente, venda['id']))
        conn.commit()
        st.success("Venda atualizada!")
        st.rerun()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h1 style='color:#FBBF24; text-align:center;'>🥚 EGG Midnight</h1>", unsafe_allow_html=True)
    menu = option_menu(None, ["Home", "Vendas", "Estoque", "Financeiro", "Clientes"],
        icons=['house', 'cart3', 'box', 'currency-dollar', 'person-badge'],
        styles={"nav-link-selected": {"background-color": "#FBBF24", "color": "#0F172A"}})

# --- HOME ---
if menu == "Home":
    st.markdown("<h2 style='color:#FBBF24;'>📊 Visão de Comando</h2>", unsafe_allow_html=True)
    df_v = pd.read_sql_query("SELECT * FROM vendas", conn)
    total_receita = df_v['total'].sum() if not df_v.empty else 0
    total_pendente = df_v['pendente'].sum() if not df_v.empty else 0
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Faturamento Total", f"R$ {total_receita:,.2f}")
    c2.metric("Contas a Receber", f"R$ {total_pendente:,.2f}")
    c3.metric("Vendas Realizadas", len(df_v))
    c4.metric("Clientes", pd.read_sql_query("SELECT COUNT(*) FROM clientes", conn).iloc[0,0])

# --- VENDAS (PDV) ---
elif menu == "Vendas":
    st.markdown("<h2 style='color:#FBBF24;'>🛒 Frente de Caixa</h2>", unsafe_allow_html=True)
    df_cli = pd.read_sql_query("SELECT * FROM clientes", conn)
    if df_cli.empty:
        st.warning("Cadastre um cliente primeiro.")
    else:
        with st.form("pdv", clear_on_submit=True):
            cli_sel = st.selectbox("Cliente", df_cli['nome'].tolist())
            c1, c2, c3 = st.columns(3)
            tam = c1.selectbox("Tamanho", ["Extra", "Jumbo", "Grande", "Médio"])
            cor = c2.selectbox("Cor", ["Branco", "Vermelho"])
            qtd = c3.number_input("Bandejas", min_value=1, step=1)
            
            prod_name = f"{cor} {tam}"
            v_unit = st.number_input("Preço Unitário (R$)", value=15.0)
            pago = st.number_input("Valor Pago Agora (R$)", value=float(v_unit * qtd))
            
            if st.form_submit_button("CONCLUIR VENDA"):
                est_atual = conn.execute("SELECT qtd FROM estoque WHERE produto = ?", (prod_name,)).fetchone()[0]
                if est_atual >= qtd:
                    total = v_unit * qtd
                    cli_id = df_cli[df_cli['nome'] == cli_sel]['id'].values[0]
                    conn.execute("INSERT INTO vendas (cli_id, data, prod, valor, qtd, total, pago, pendente) VALUES (?,?,?,?,?,?,?,?)",
                                (int(cli_id), str(date.today()), prod_name, v_unit, qtd, total, pago, total-pago))
                    conn.execute("UPDATE estoque SET qtd = qtd - ? WHERE produto = ?", (qtd, prod_name))
                    conn.commit()
                    st.balloons()
                    st.rerun()
                else: st.error("Estoque insuficiente!")

# --- ESTOQUE ---
elif menu == "Estoque":
    st.markdown("<h2 style='color:#FBBF24;'>📦 Estoque</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 2])
    with col1:
        with st.form("add_est"):
            p_sel = st.selectbox("Produto", pd.read_sql_query("SELECT produto FROM estoque", conn)['produto'].tolist())
            q_add = st.number_input("Quantidade", min_value=1)
            if st.form_submit_button("Adicionar"):
                conn.execute("UPDATE estoque SET qtd = qtd + ? WHERE produto = ?", (q_add, p_sel))
                conn.commit()
                st.rerun()
    with col2:
        df_e = pd.read_sql_query("SELECT produto as 'Produto', qtd as 'Saldo' FROM estoque", conn)
        st.dataframe(df_e, use_container_width=True, hide_index=True)

# --- FINANCEIRO (COM EDITAR E REMOVER) ---
elif menu == "Financeiro":
    st.markdown("<h2 style='color:#FBBF24;'>💰 Fluxo e Histórico</h2>", unsafe_allow_html=True)
    
    # Query para pegar os dados
    df_f = pd.read_sql_query('''
        SELECT v.id, v.data, c.nome as cliente, v.prod, v.qtd, v.valor, v.total, v.pago, v.pendente 
        FROM vendas v JOIN clientes c ON v.cli_id = c.id ORDER BY v.id DESC
    ''', conn)

    if df_f.empty:
        st.info("Nenhuma venda registrada.")
    else:
        st.markdown("<div class='card-dark'>", unsafe_allow_html=True)
        # Cabeçalho da tabela customizada
        h1, h2, h3, h4, h5, h6, h7 = st.columns([1, 2, 2, 1, 1, 1, 1])
        h1.write("**Data**")
        h2.write("**Cliente**")
        h3.write("**Produto**")
        h4.write("**Total**")
        h5.write("**Débito**")
        h6.write("**Edit**")
        h7.write("**Sair**")
        st.divider()

        for index, row in df_f.iterrows():
            c1, c2, c3, c4, c5, c6, c7 = st.columns([1, 2, 2, 1, 1, 1, 1])
            c1.write(row['data'])
            c2.write(row['cliente'])
            c3.write(f"{row['qtd']}x {row['prod']}")
            c4.write(f"R${row['total']:.2f}")
            
            # Cor para o débito (vermelho se houver pendência)
            cor_debito = "#F87171" if row['pendente'] > 0 else "#34D399"
            c5.markdown(f"<span style='color:{cor_debito};'>R${row['pendente']:.2f}</span>", unsafe_allow_html=True)
            
            # Botão Editar
            if c6.button("✏️", key=f"edit_{row['id']}"):
                editar_venda_modal(row)
            
            # Botão Excluir
            if c7.button("🗑️", key=f"del_{row['id']}"):
                excluir_venda(row['id'], row['prod'], row['qtd'])
        
        st.markdown("</div>", unsafe_allow_html=True)

# --- CLIENTES ---
elif menu == "Clientes":
    st.markdown("<h2 style='color:#FBBF24;'>👤 Clientes</h2>", unsafe_allow_html=True)
    with st.form("cli"):
        n = st.text_input("Nome Comercial")
        t = st.text_input("WhatsApp")
        e = st.text_input("Endereço")
        if st.form_submit_button("Salvar"):
            conn.execute("INSERT INTO clientes (nome, tel, endereco) VALUES (?,?,?)", (n,t,e))
            conn.commit()
            st.rerun()
    st.dataframe(pd.read_sql_query("SELECT nome, tel, endereco FROM clientes", conn), use_container_width=True)
