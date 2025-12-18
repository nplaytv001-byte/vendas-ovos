import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, date
from streamlit_option_menu import option_menu

# --- CONFIGURAÇÃO DE ALTO NÍVEL ---
st.set_page_config(page_title="EggGestão Midnight Ultra", layout="wide", page_icon="🥚")

# --- CSS PERSONALIZADO ---
st.markdown("""
    <style>
    .stApp { background-color: #0F172A !important; color: #F8FAFC !important; }
    [data-testid="stSidebar"] { background-color: #020617 !important; border-right: 1px solid #1E293B; }
    .stMetric { background-color: #1E293B !important; border: 1px solid #334155 !important; border-radius: 15px !important; padding: 15px !important; }
    .stButton>button { background: linear-gradient(135deg, #FBBF24 0%, #D97706 100%) !important; color: #0F172A !important; font-weight: bold; border-radius: 8px; }
    .main-card { background-color: #1E293B; padding: 20px; border-radius: 15px; border: 1px solid #334155; }
    </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('ovos_midnight_v3.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY, nome TEXT, tel TEXT, endereco TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS estoque (produto TEXT PRIMARY KEY, qtd INTEGER)''')
    # Tabela de vendas atualizada para suportar Pix e Dinheiro
    c.execute('''CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY, cli_id INTEGER, data TEXT, prod TEXT, 
                valor_unit REAL, qtd INTEGER, total REAL, 
                pago_pix REAL, pago_dinheiro REAL, pendente REAL)''')
    
    prods = ["Branco Extra", "Vermelho Extra", "Branco Grande", "Vermelho Grande", "Branco Médio", "Vermelho Médio", "Branco Jumbo", "Vermelho Jumbo"]
    for p in prods:
        c.execute("INSERT OR IGNORE INTO estoque (produto, qtd) VALUES (?, 0)", (p,))
    conn.commit()
    return conn

conn = init_db()

# --- FUNÇÕES DE APOIO ---
def get_clientes():
    return pd.read_sql_query("SELECT * FROM clientes", conn)

def get_estoque_disponivel():
    return pd.read_sql_query("SELECT * FROM estoque WHERE qtd > 0", conn)

# --- MODAIS CLIENTES ---
@st.dialog("Editar Cliente")
def editar_cliente_modal(cliente):
    nome = st.text_input("Nome", value=cliente['nome'])
    tel = st.text_input("Telefone", value=cliente['tel'])
    end = st.text_input("Endereço", value=cliente['endereco'])
    if st.button("Salvar Alterações"):
        conn.execute("UPDATE clientes SET nome=?, tel=?, endereco=? WHERE id=?", (nome, tel, end, cliente['id']))
        conn.commit()
        st.success("Cliente atualizado!")
        st.rerun()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h1 style='color:#FBBF24; text-align:center;'>🥚 EGG Midnight</h1>", unsafe_allow_html=True)
    menu = option_menu(None, ["Dashboard", "PDV Vendas", "Estoque", "Financeiro", "Clientes"],
        icons=['house', 'cart3', 'box', 'currency-dollar', 'person-badge'],
        styles={"nav-link-selected": {"background-color": "#FBBF24", "color": "#0F172A"}})

# --- DASHBOARD ---
if menu == "Dashboard":
    st.markdown("<h2 style='color:#FBBF24;'>📊 Visão Geral</h2>", unsafe_allow_html=True)
    df_v = pd.read_sql_query("SELECT * FROM vendas", conn)
    
    c1, c2, c3, c4 = st.columns(4)
    if not df_v.empty:
        c1.metric("Receita Bruta", f"R$ {df_v['total'].sum():,.2f}")
        c2.metric("Total Recebido", f"R$ {(df_v['pago_pix'].sum() + df_v['pago_dinheiro'].sum()):,.2f}")
        c3.metric("Contas a Receber", f"R$ {df_v['pendente'].sum():,.2f}", delta_color="inverse")
        c4.metric("Vendas", len(df_v))
        
        # Calendário de Receita
        st.markdown("### 📅 Receita por Calendário")
        df_v['data'] = pd.to_datetime(df_v['data'])
        receita_diaria = df_v.groupby('data')['total'].sum().reset_index()
        fig = px.bar(receita_diaria, x='data', y='total', labels={'total':'Faturamento', 'data':'Data'},
                     color_discrete_sequence=['#FBBF24'], template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhuma venda realizada ainda.")

# --- PDV VENDAS ---
elif menu == "PDV Vendas":
    st.markdown("<h2 style='color:#FBBF24;'>🛒 Frente de Caixa</h2>", unsafe_allow_html=True)
    
    df_est = get_estoque_disponivel()
    df_cli = get_clientes()
    
    if df_cli.empty:
        st.warning("⚠️ Cadastre um cliente antes de vender.")
    elif df_est.empty:
        st.error("❌ Não há ovos disponíveis no estoque!")
    else:
        with st.container(border=True):
            col1, col2 = st.columns(2)
            cliente_nome = col1.selectbox("Cliente", df_cli['nome'].tolist())
            produto_nome = col2.selectbox("Ovos Disponíveis", df_est['produto'].tolist())
            
            # Info do estoque selecionado
            qtd_max = int(df_est[df_est['produto'] == produto_nome]['qtd'].values[0])
            st.info(f"Estoque atual de {produto_nome}: {qtd_max} bandejas")
            
            c1, c2, c3 = st.columns(3)
            qtd_venda = c1.number_input("Quantidade", min_value=1, max_value=qtd_max, step=1)
            preco_unit = c2.number_input("Preço Unitário (R$)", min_value=0.0, value=15.0, step=0.50)
            
            total_venda = qtd_venda * preco_unit
            c3.markdown(f"### Total: <span style='color:#FBBF24;'>R$ {total_venda:.2f}</span>", unsafe_allow_html=True)
            
            st.divider()
            st.markdown("#### Pagamento")
            p1, p2, p3 = st.columns(3)
            p_pix = p1.number_input("Pago no PIX (R$)", min_value=0.0, value=0.0)
            p_din = p2.number_input("Pago no Dinheiro (R$)", min_value=0.0, value=0.0)
            
            pendente = total_venda - (p_pix + p_din)
            cor_pendente = "#34D399" if pendente <= 0 else "#F87171"
            p3.markdown(f"#### Pendência: <span style='color:{cor_pendente};'>R$ {pendente:.2f}</span>", unsafe_allow_html=True)
            
            if st.button("FINALIZAR VENDA"):
                cli_id = df_cli[df_cli['nome'] == cliente_nome]['id'].values[0]
                conn.execute("""INSERT INTO vendas 
                    (cli_id, data, prod, valor_unit, qtd, total, pago_pix, pago_dinheiro, pendente) 
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (int(cli_id), date.today().strftime("%Y-%m-%d"), produto_nome, preco_unit, qtd_venda, total_venda, p_pix, p_din, pendente))
                
                conn.execute("UPDATE estoque SET qtd = qtd - ? WHERE produto = ?", (qtd_venda, produto_nome))
                conn.commit()
                st.success(f"Venda registrada para {cliente_nome}!")
                st.balloons()
                st.rerun()

# --- FINANCEIRO ---
elif menu == "Financeiro":
    st.markdown("<h2 style='color:#FBBF24;'>💰 Relatórios Financeiros</h2>", unsafe_allow_html=True)
    
    # Filtro por data
    data_relatorio = st.date_input("Filtrar por Dia", date.today())
    
    df_f = pd.read_sql_query(f"""
        SELECT v.id, v.data, c.nome as cliente, v.prod, v.qtd, v.total, v.pago_pix, v.pago_dinheiro, v.pendente 
        FROM vendas v JOIN clientes c ON v.cli_id = c.id 
        WHERE v.data = '{data_relatorio.strftime("%Y-%m-%d")}'
    """, conn)
    
    if not df_f.empty:
        st.write(f"### Relatório de {data_relatorio.strftime('%d/%m/%Y')}")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Vendas do Dia", f"R$ {df_f['total'].sum():,.2f}")
        r2.metric("Recebido PIX", f"R$ {df_f['pago_pix'].sum():,.2f}")
        r3.metric("Recebido Dinheiro", f"R$ {df_f['pago_dinheiro'].sum():,.2f}")
        r4.metric("Pendente", f"R$ {df_f['pendente'].sum():,.2f}")
        
        st.dataframe(df_f, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma venda registrada nesta data.")

# --- ESTOQUE ---
elif menu == "Estoque":
    st.markdown("<h2 style='color:#FBBF24;'>📦 Gestão de Estoque</h2>", unsafe_allow_html=True)
    with st.form("add_estoque"):
        c1, c2 = st.columns(2)
        p_sel = c1.selectbox("Produto", ["Branco Extra", "Vermelho Extra", "Branco Grande", "Vermelho Grande", "Branco Médio", "Vermelho Médio", "Branco Jumbo", "Vermelho Jumbo"])
        q_add = c2.number_input("Adicionar Qtd de Bandejas", min_value=1, step=1)
        if st.form_submit_button("Atualizar Estoque"):
            conn.execute("UPDATE estoque SET qtd = qtd + ? WHERE produto = ?", (q_add, p_sel))
            conn.commit()
            st.rerun()
            
    df_est_total = pd.read_sql_query("SELECT * FROM estoque", conn)
    st.dataframe(df_est_total, use_container_width=True, hide_index=True)

# --- CLIENTES ---
elif menu == "Clientes":
    st.markdown("<h2 style='color:#FBBF24;'>👤 Gestão de Clientes</h2>", unsafe_allow_html=True)
    
    with st.expander("➕ Novo Cliente"):
        with st.form("novo_cli"):
            nome = st.text_input("Nome Comercial")
            tel = st.text_input("WhatsApp")
            end = st.text_input("Endereço")
            if st.form_submit_button("Cadastrar"):
                conn.execute("INSERT INTO clientes (nome, tel, endereco) VALUES (?,?,?)", (nome, tel, end))
                conn.commit()
                st.rerun()
                
    df_c = get_clientes()
    if not df_c.empty:
        for idx, row in df_c.iterrows():
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                col1.write(f"**{row['nome']}**")
                col2.write(f"📞 {row['tel']}")
                
                if col3.button("✏️", key=f"ed_{row['id']}"):
                    editar_cliente_modal(row)
                    
                if col4.button("🗑️", key=f"del_{row['id']}"):
                    conn.execute("DELETE FROM clientes WHERE id=?", (row['id'],))
                    conn.commit()
                    st.toast("Cliente removido!")
                    st.rerun()
