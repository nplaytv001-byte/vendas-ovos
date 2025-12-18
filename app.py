import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date
import urllib.parse
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from streamlit_js_eval import streamlit_js_eval
from streamlit_option_menu import option_menu

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="EggGestão Pro v4.1", layout="wide", page_icon="🥚")

# --- CSS DE ALTO CONTRASTE E LEITURA ---
st.markdown("""
    <style>
    /* Forçar fundo claro na área principal */
    .stApp {
        background-color: #F8FAFC;
    }

    /* Títulos e textos gerais */
    h1, h2, h3, p, span, label {
        color: #1E293B !important; /* Azul Marinho Profundo */
    }

    /* Sidebar - Contraste Escuro */
    [data-testid="stSidebar"] {
        background-color: #0F172A !important;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }

    /* Cards de Métricas (Branco Puro com Sombra) */
    .metric-card {
        background-color: #FFFFFF !important;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin-bottom: 15px;
    }
    .metric-label {
        color: #64748B !important;
        font-size: 14px;
        font-weight: 600;
        text-transform: uppercase;
    }
    .metric-value {
        color: #0F172A !important;
        font-size: 24px;
        font-weight: 800;
    }

    /* Área de PDV (Destaque de Valor) */
    .pdv-total-box {
        background-color: #0F172A !important;
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        border: 2px solid #FBBA24;
    }
    .pdv-total-box h1, .pdv-total-box p {
        color: #FBBA24 !important; /* Amarelo Ouro para destaque */
    }

    /* Input Fields (Melhorar visibilidade das bordas) */
    .stTextInput input, .stNumberInput input, .stSelectbox div {
        border: 1px solid #CBD5E1 !important;
        color: #1E293B !important;
    }

    /* Estilo de Tabelas */
    .stDataFrame {
        background-color: white;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS (Extra sempre no topo) ---
ORDEM_TAMANHOS = ["Extra", "Jumbo", "Grande", "Médio"]

def init_db():
    conn = sqlite3.connect('ovos_master.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, endereco TEXT, telefone TEXT, lat REAL, lon REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vendas (id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_id INTEGER, data TEXT, produto TEXT, valor_unit REAL, qtd INTEGER, total_nota REAL, pago REAL, pendente REAL, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS estoque (produto TEXT PRIMARY KEY, quantidade INTEGER)''')
    c.execute("SELECT COUNT(*) FROM estoque")
    if c.fetchone()[0] == 0:
        for tam in ORDEM_TAMANHOS:
            for cor in ["Branco", "Vermelho"]:
                c.execute("INSERT INTO estoque VALUES (?,?)", (f"{cor} {tam}", 0))
    conn.commit()
    return conn

conn = init_db()

# --- HEADER SUPERIOR ---
st.markdown(f"""
    <div style="background: linear-gradient(90deg, #0F172A 0%, #1E293B 100%); padding: 15px 25px; border-radius: 12px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; border-bottom: 4px solid #FBBA24;">
        <h2 style="color: white !important; margin: 0; font-weight: 800;">🥚 EggGestão <span style="color: #FBBA24 !important;">Pro</span></h2>
        <div style="color: #CBD5E1 !important; font-size: 14px;">{date.today().strftime('%d de %B, %Y')}</div>
    </div>
    """, unsafe_allow_html=True)

# --- MENU LATERAL ---
with st.sidebar:
    menu = option_menu(
        "Navegação Principal",
        ["Dashboard", "PDV / Vendas", "Estoque", "Clientes", "Financeiro"],
        icons=["house", "cart-check", "box-seam", "people", "cash-stack"],
        menu_icon="cast", default_index=0,
        styles={
            "container": {"background-color": "#0F172A"},
            "nav-link": {"font-size": "14px", "text-align": "left", "margin":"5px", "color": "white"},
            "nav-link-selected": {"background-color": "#FBBA24", "color": "#0F172A !important"},
        }
    )

# ================= DASHBOARD =================
if menu == "Dashboard":
    # Dados para métricas
    res_vendas = pd.read_sql_query("SELECT SUM(total_nota) as total, SUM(pendente) as pend FROM vendas", conn)
    total_vendas = res_vendas.iloc[0]['total'] or 0
    total_pendente = res_vendas.iloc[0]['pend'] or 0
    total_extra = pd.read_sql_query("SELECT SUM(qtd) FROM vendas WHERE produto LIKE '%Extra%'", conn).iloc[0,0] or 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Vendas Totais</div><div class="metric-value">R$ {total_vendas:,.2f}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Ovos Extra</div><div class="metric-value">{int(total_extra)} Band.</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Dívidas Clientes</div><div class="metric-value" style="color: #EF4444 !important;">R$ {total_pendente:,.2f}</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Status Caixa</div><div class="metric-value" style="color: #10B981 !important;">ABERTO</div></div>', unsafe_allow_html=True)

    # Gráfico de Estoque (Sempre mostrando Extra primeiro)
    st.markdown("### 📈 Nível de Estoque (Prioridade Extra)")
    df_est = pd.read_sql_query("SELECT * FROM estoque", conn)
    df_est['ordem'] = df_est['produto'].apply(lambda x: ORDEM_TAMANHOS.index(x.split(' ')[1]))
    df_est = df_est.sort_values('ordem')
    
    fig = go.Figure([go.Bar(x=df_est['produto'], y=df_est['quantidade'], marker_color='#1E293B')])
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=30, b=0), height=300)
    st.plotly_chart(fig, use_container_width=True)

# ================= PDV / VENDAS =================
elif menu == "PDV / Vendas":
    st.markdown("### 🛒 Ponto de Venda")
    
    col_v1, col_v2 = st.columns([2, 1])
    
    with col_v1:
        st.markdown('<div style="background: white; padding: 25px; border-radius: 15px; border: 1px solid #E2E8F0;">', unsafe_allow_html=True)
        df_cli = pd.read_sql_query("SELECT id, nome, telefone FROM clientes", conn)
        
        with st.form("venda_form", clear_on_submit=True):
            cliente = st.selectbox("Selecione o Cliente", df_cli['nome'].tolist())
            c1, c2, c3 = st.columns(3)
            # Extra é o primeiro da lista ORDEM_TAMANHOS
            tam = c1.selectbox("Tamanho", ORDEM_TAMANHOS)
            cor = c2.selectbox("Cor", ["Branco", "Vermelho"])
            qtd = c3.number_input("Qtd Bandejas", min_value=1, value=1)
            
            # Busca automática de preço
            ult_p = pd.read_sql_query(f"SELECT valor_unit FROM vendas WHERE produto LIKE '%{tam}%' ORDER BY id DESC LIMIT 1", conn)
            v_sugerido = ult_p.iloc[0,0] if not ult_p.empty else 15.0
            
            v_unit = st.number_input("Preço Unitário (R$)", value=float(v_sugerido))
            pago = st.number_input("Valor Recebido Agora (R$)", value=float(v_unit * qtd))
            
            if st.form_submit_button("CONCLUIR VENDA"):
                prod = f"{cor} {tam}"
                total = v_unit * qtd
                pend = total - pago
                c_id = int(df_cli[df_cli['nome'] == cliente]['id'].values[0])
                
                conn.execute("INSERT INTO vendas (cliente_id, data, produto, valor_unit, qtd, total_nota, pago, pendente, status) VALUES (?,?,?,?,?,?,?,?,?)",
                            (c_id, str(date.today()), prod, v_unit, qtd, total, pago, pend, "PAGO" if pend <= 0 else "PENDENTE"))
                conn.execute("UPDATE estoque SET quantidade = quantidade - ? WHERE produto = ?", (qtd, prod))
                conn.commit()
                st.success("Venda registrada!")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col_v2:
        # Resumo visual do valor (Garante leitura)
        st.markdown(f"""
            <div class="pdv-total-box">
                <p style="margin: 0; font-size: 14px; opacity: 0.9;">TOTAL DA VENDA</p>
                <h1 style="margin: 0; font-size: 48px;">R$ {v_unit * qtd:,.2f}</h1>
            </div>
        """, unsafe_allow_html=True)
        st.warning("⚠️ Verifique o estoque do Ovo Extra antes de finalizar.")

# ================= ESTOQUE =================
elif menu == "Estoque":
    st.markdown("### 📦 Gerenciamento de Estoque Central")
    df_est = pd.read_sql_query("SELECT * FROM estoque", conn)
    df_est['ordem'] = df_est['produto'].apply(lambda x: ORDEM_TAMANHOS.index(x.split(' ')[1]))
    df_est = df_est.sort_values('ordem')

    col_e1, col_e2 = st.columns([1, 2])
    
    with col_e1:
        st.markdown("#### Repor Estoque")
        with st.form("rep_form"):
            p_rep = st.selectbox("Escolha o Produto", df_est['produto'].tolist())
            q_rep = st.number_input("Qtd para Adicionar", min_value=1)
            if st.form_submit_button("Atualizar Saldo"):
                conn.execute("UPDATE estoque SET quantidade = quantidade + ? WHERE produto = ?", (q_rep, p_rep))
                conn.commit()
                st.rerun()
                
    with col_e2:
        st.markdown("#### Saldo Atual")
        st.dataframe(df_est[['produto', 'quantidade']], use_container_width=True, hide_index=True)

# ================= FINANCEIRO =================
elif menu == "Financeiro":
    st.markdown("### 💰 Controle Financeiro e Cobrança")
    df_fin = pd.read_sql_query('''SELECT v.id, v.data, c.nome as Cliente, v.produto, v.total_nota as Total, v.pendente as Devedor, v.status 
                                  FROM vendas v JOIN clientes c ON v.cliente_id = c.id ORDER BY v.id DESC''', conn)
    
    st.dataframe(df_fin, use_container_width=True, hide_index=True)

# ================= CLIENTES =================
elif menu == "Clientes":
    st.markdown("### 👤 Cadastro de Clientes")
    with st.form("cli_form"):
        n = st.text_input("Nome do Cliente")
        e = st.text_input("Endereço Completo")
        t = st.text_input("WhatsApp (Ex: 11999999999)")
        if st.form_submit_button("Cadastrar Cliente"):
            conn.execute("INSERT INTO clientes (nome, endereco, telefone) VALUES (?,?,?)", (n, e, t))
            conn.commit()
            st.success("Cliente salvo!")
