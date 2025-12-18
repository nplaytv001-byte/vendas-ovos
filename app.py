import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, date

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="EggGestão Midnight The Boss", layout="wide", page_icon="🥚")

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('ovos_boss.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY, nome TEXT, tel TEXT, endereco TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS estoque (produto TEXT PRIMARY KEY, qtd INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT, cli_id INTEGER, data TEXT, prod TEXT, 
                valor_unit REAL, qtd INTEGER, total REAL, 
                pago_pix REAL, pago_din REAL, pendente REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS despesas (id INTEGER PRIMARY KEY, data TEXT, desc TEXT, valor REAL)''')
    
    prods = ["Branco Extra", "Vermelho Extra", "Branco Grande", "Vermelho Grande", "Branco Médio", "Vermelho Médio", "Branco Jumbo", "Vermelho Jumbo"]
    for p in prods:
        c.execute("INSERT OR IGNORE INTO estoque (produto, qtd) VALUES (?, 0)", (p,))
    conn.commit()
    return conn

conn = init_db()

# --- CSS DARK ---
st.markdown("""
    <style>
    .stApp { background-color: #0F172A; color: #F8FAFC; }
    div[data-testid="stMetric"] { background-color: #1E293B; border: 1px solid #334155; border-radius: 12px; }
    .stButton>button { border-radius: 8px; font-weight: bold; width: 100%; }
    .status-pendente { color: #F87171; font-weight: bold; }
    .status-pago { color: #34D399; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE APOIO ---
def excluir_venda(venda_id, produto, qtd_estorno):
    conn.execute("UPDATE estoque SET qtd = qtd + ? WHERE produto = ?", (qtd_estorno, produto))
    conn.execute("DELETE FROM vendas WHERE id = ?", (venda_id,))
    conn.commit()
    st.toast(f"Venda #{venda_id} excluída e estoque devolvido!", icon="🗑️")

# --- MODAIS (DIALOGS) ---
@st.dialog("Editar Venda")
def editar_venda_modal(venda):
    st.write(f"### Ajustar Venda #{venda['id']}")
    v_unit = st.number_input("Preço Unitário (R$)", value=float(venda['valor_unit']))
    p_pix = st.number_input("Pagamento PIX (R$)", value=float(venda['pago_pix']))
    p_din = st.number_input("Pagamento Dinheiro (R$)", value=float(venda['pago_din']))
    
    novo_total = v_unit * venda['qtd']
    nova_pendencia = novo_total - (p_pix + p_din)
    
    st.info(f"Novo Total: R$ {novo_total:.2f} | Pendência: R$ {nova_pendencia:.2f}")
    
    if st.button("Salvar Alterações"):
        conn.execute("""UPDATE vendas SET valor_unit=?, total=?, pago_pix=?, pago_din=?, pendente=? 
                     WHERE id=?""", (v_unit, novo_total, p_pix, p_din, nova_pendencia, venda['id']))
        conn.commit()
        st.success("Venda atualizada!")
        st.rerun()

@st.dialog("Editar Cliente")
def editar_cliente_modal(cliente):
    nome = st.text_input("Nome", value=cliente['nome'])
    tel = st.text_input("WhatsApp", value=cliente['tel'])
    end = st.text_input("Endereço", value=cliente['endereco'])
    if st.button("Salvar"):
        conn.execute("UPDATE clientes SET nome=?, tel=?, endereco=? WHERE id=?", (nome, tel, end, cliente['id']))
        conn.commit()
        st.rerun()

# --- SIDEBAR ---
with st.sidebar:
    st.title("🥚 EggBoss Pro")
    menu = st.radio("Menu", ["Dashboard", "PDV (Vendas)", "Financeiro", "Estoque", "Clientes"])

# --- 1. DASHBOARD ---
if menu == "Dashboard":
    st.header("📊 Painel de Receita")
    df_v = pd.read_sql_query("SELECT * FROM vendas", conn)
    
    c1, c2, c3 = st.columns(3)
    if not df_v.empty:
        c1.metric("Faturamento Total", f"R$ {df_v['total'].sum():,.2f}")
        c2.metric("Total em Caixa", f"R$ {(df_v['pago_pix'].sum() + df_v['pago_din'].sum()):,.2f}")
        c3.metric("Pendências", f"R$ {df_v['pendente'].sum():,.2f}", delta_color="inverse")
        
        st.subheader("📅 Receita por Calendário")
        df_v['data'] = pd.to_datetime(df_v['data'])
        df_chart = df_v.groupby('data')['total'].sum().reset_index()
        fig = px.bar(df_chart, x='data', y='total', color_discrete_sequence=['#FBBF24'], template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

# --- 2. PDV (VENDAS INTELIGENTES) ---
elif menu == "PDV (Vendas)":
    st.header("🛒 Frente de Caixa")
    df_est = pd.read_sql_query("SELECT * FROM estoque WHERE qtd > 0", conn)
    df_cli = pd.read_sql_query("SELECT * FROM clientes", conn)

    if df_cli.empty: st.error("Cadastre um cliente primeiro!")
    elif df_est.empty: st.warning("Sem ovos no estoque!")
    else:
        with st.container(border=True):
            col1, col2 = st.columns(2)
            cli_sel = col1.selectbox("Cliente", df_cli['nome'].tolist())
            prod_sel = col2.selectbox("Ovo Disponível", df_est['produto'].tolist())
            
            q_max = int(df_est[df_est['produto'] == prod_sel]['qtd'].values[0])
            st.caption(f"Saldo em estoque: {q_max} bandejas")

            st.divider()
            c_a, c_b, c_c = st.columns(3)
            qtd = c_a.number_input("Quantidade", 1, q_max, 1)
            preco = c_b.number_input("Preço Un. (R$)", 0.0, 200.0, 15.0)
            
            # REATIVIDADE: ATUALIZA ENQUANTO DIGITA
            v_total = qtd * preco
            c_c.markdown(f"### Total: <br><span style='color:#FBBF24'>R$ {v_total:.2f}</span>", unsafe_allow_html=True)
            
            p_a, p_b, p_c = st.columns(3)
            pix = p_a.number_input("Pago no PIX", 0.0, v_total, v_total)
            din = p_b.number_input("Pago no Dinheiro", 0.0, v_total - pix, 0.0)
            
            pend = v_total - (pix + din)
            cor = "#34D399" if pend == 0 else "#F87171"
            p_c.markdown(f"### Pendente: <br><span style='color:{cor}'>R$ {pend:.2f}</span>", unsafe_allow_html=True)

            if st.button("Finalizar Venda"):
                id_cli = int(df_cli[df_cli['nome'] == cli_sel]['id'].values[0])
                conn.execute("""INSERT INTO vendas (cli_id, data, prod, valor_unit, qtd, total, pago_pix, pago_din, pendente) 
                             VALUES (?,?,?,?,?,?,?,?,?)""", 
                             (id_cli, date.today().isoformat(), prod_sel, preco, qtd, v_total, pix, din, pend))
                conn.execute("UPDATE estoque SET qtd = qtd - ? WHERE produto = ?", (qtd, prod_sel))
                conn.commit()
                st.success("Venda Concluída!")
                st.rerun()

# --- 3. FINANCEIRO (RELATÓRIOS + EDITAR/EXCLUIR) ---
elif menu == "Financeiro":
    st.header("💰 Controle Financeiro")
    
    # Filtro de Data (Calendário)
    data_filtro = st.date_input("Filtrar Relatório Diário", date.today())
    
    df_f = pd.read_sql_query(f"""
        SELECT v.*, c.nome as cliente 
        FROM vendas v JOIN clientes c ON v.cli_id = c.id 
        WHERE v.data = '{
