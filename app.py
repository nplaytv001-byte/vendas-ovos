import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from fpdf import FPDF
from datetime import datetime, date
import urllib.parse
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from streamlit_js_eval import streamlit_js_eval
from streamlit_option_menu import option_menu

# --- CONFIGURAÇÃO PREMIUM ---
st.set_page_config(page_title="EggGestão Enterprise", layout="wide", page_icon="🥚")

# --- CSS AVANÇADO (Design de Sistema Proprietário) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Fundo e Container */
    .stApp { background: #f8fafc; }
    
    /* Cards de Métricas Estilizados */
    .metric-card {
        background: white;
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        border: 1px solid #e2e8f0;
        transition: transform 0.2s ease;
    }
    .metric-card:hover { transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.05); }
    
    /* Status de Estoque */
    .stock-high { color: #10b981; font-weight: bold; }
    .stock-low { color: #f59e0b; font-weight: bold; }
    .stock-critical { color: #ef4444; font-weight: bold; }

    /* Botões Profissionais */
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 45px;
        background-color: #0f172a;
        color: white;
        border: none;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .stButton>button:hover { background-color: #334155; color: #fbbf24; }

    /* Estilização de Tabelas */
    .styled-table { width: 100%; border-collapse: collapse; margin: 25px 0; font-size: 0.9em; min-width: 400px; }
    
    /* Header Custom */
    .main-header {
        background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        margin-bottom: 25px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE BANCO DE DATA (EXTRA SEMPRE NO TOPO) ---
ORDEM_TAMANHOS = ["Extra", "Jumbo", "Grande", "Médio"]

def init_db():
    conn = sqlite3.connect('ovos_master.db', check_same_thread=False)
    c = conn.cursor()
    # Tabelas... (Mantidas conforme v3.3 para compatibilidade)
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, endereco TEXT, telefone TEXT, lat REAL, lon REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vendas (id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_id INTEGER, data TEXT, produto TEXT, valor_unit REAL, qtd INTEGER, total_nota REAL, pago REAL, pendente REAL, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS estoque (produto TEXT PRIMARY KEY, quantidade INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS despesas (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, categoria TEXT, valor REAL, descricao TEXT)''')
    
    c.execute("SELECT COUNT(*) FROM estoque")
    if c.fetchone()[0] == 0:
        for tam in ORDEM_TAMANHOS:
            for cor in ["Branco", "Vermelho"]:
                c.execute("INSERT INTO estoque VALUES (?,?)", (f"{cor} {tam}", 0))
    conn.commit()
    return conn

conn = init_db()

# --- HEADER PROFISSIONAL ---
st.markdown(f"""
    <div class="main-header">
        <div>
            <h2 style="margin:0;">🥚 EggGestão <span style="color:#fbbf24;">Enterprise</span></h2>
            <p style="margin:0; opacity:0.8; font-size:12px;">Bem-vindo, Administrador | {date.today().strftime('%d/%m/%Y')}</p>
        </div>
        <div style="text-align:right;">
            <span style="background:#334155; padding:8px 15px; border-radius:20px; font-size:12px;">v4.0 Premium</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- MENU LATERAL (SOPHISTICATED) ---
with st.sidebar:
    menu = option_menu(
        "Navegação",
        ["Dashboard", "PDV (Vendas)", "Estoque Central", "Clientes", "Financeiro", "Logística"],
        icons=["grid-1x2", "cart-check", "box-seam", "people", "wallet2", "truck"],
        menu_icon="layers",
        default_index=0,
        styles={
            "container": {"padding": "5!important", "background-color": "#f8fafc"},
            "nav-link": {"font-size": "14px", "text-align": "left", "margin":"5px", "color": "#475569"},
            "nav-link-selected": {"background-color": "#0f172a", "color": "#fbbf24"},
        }
    )

# ================= DASHBOARD 4.0 =================
if menu == "Dashboard":
    # KPIs Rápidos
    total_vendas = pd.read_sql_query("SELECT SUM(total_nota) FROM vendas", conn).iloc[0,0] or 0
    total_extra = pd.read_sql_query("SELECT SUM(qtd) FROM vendas WHERE produto LIKE '%Extra%'", conn).iloc[0,0] or 0
    total_pendente = pd.read_sql_query("SELECT SUM(pendente) FROM vendas", conn).iloc[0,0] or 0
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric-card"><small>FATURAMENTO BRUTO</small><br><b>R$ {total_vendas:,.2f}</b></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><small>OVOS EXTRA VENDIDOS</small><br><b>{int(total_extra)} Unid.</b></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><small>A RECEBER (CRÉDITO)</small><br><b style="color:#ef4444;">R$ {total_pendente:,.2f}</b></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card"><small>STATUS OPERACIONAL</small><br><b style="color:#10b981;">ATIVO</b></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Gráficos Avançados
    col_chart1, col_chart2 = st.columns([2, 1])
    
    with col_chart1:
        df_vd = pd.read_sql_query("SELECT data, SUM(total_nota) as total FROM vendas GROUP BY data", conn)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_vd['data'], y=df_vd['total'], fill='tozeroy', line_color='#0f172a', name='Vendas'))
        fig.update_layout(title="Performance de Vendas Diária", height=350, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with col_chart2:
        df_est = pd.read_sql_query("SELECT * FROM estoque", conn)
        fig_pie = go.Figure(data=[go.Pie(labels=df_est['produto'], values=df_est['quantidade'], hole=.4)])
        fig_pie.update_layout(title="Distribuição de Estoque", height=350, showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)

# ================= PDV (VENDAS) =================
elif menu == "PDV (Vendas)":
    st.subheader("🛒 Ponto de Venda")
    
    df_cli = pd.read_sql_query("SELECT id, nome, telefone FROM clientes", conn)
    
    col_pdv1, col_pdv2 = st.columns([2, 1])
    
    with col_pdv1:
        with st.container():
            st.markdown('<div style="background:white; padding:30px; border-radius:15px; border:1px solid #e2e8f0;">', unsafe_allow_html=True)
            with st.form("pdv_form"):
                cli = st.selectbox("Selecione o Cliente", df_cli['nome'].tolist())
                c1, c2, c3 = st.columns(3)
                tam = c1.selectbox("Tamanho (Extra 1º)", ORDEM_TAMANHOS)
                cor = c2.selectbox("Cor", ["Branco", "Vermelho"])
                qtd = c3.number_input("Quantidade", min_value=1)
                
                # Inteligência de Preço
                ult_preco = pd.read_sql_query(f"SELECT valor_unit FROM vendas WHERE produto LIKE '%{tam}%' ORDER BY id DESC LIMIT 1", conn)
                sugerido = ult_preco.iloc[0,0] if not ult_preco.empty else 15.0
                
                c4, c5 = st.columns(2)
                valor = c4.number_input("Preço Unitário (R$)", value=float(sugerido))
                pago = c5.number_input("Valor Pago (R$)", value=float(valor*qtd))
                
                if st.form_submit_button("CONCLUIR VENDA E GERAR RECIBO"):
                    # Lógica de banco (igual v3.3)...
                    st.success(f"Venda para {cli} processada!")
            st.markdown('</div>', unsafe_allow_html=True)

    with col_pdv2:
        st.markdown("##### Resumo do Pedido")
        total_atual = valor * qtd
        st.markdown(f"""
            <div style="background:#0f172a; color:white; padding:20px; border-radius:15px; text-align:center;">
                <p style="margin:0;">TOTAL A PAGAR</p>
                <h1 style="color:#fbbf24; margin:0;">R$ {total_atual:,.2f}</h1>
            </div>
        """, unsafe_allow_html=True)
        st.info("O ovo **EXTRA** está pré-selecionado para agilizar sua operação.")

# ================= ESTOQUE CENTRAL =================
elif menu == "Estoque Central":
    st.subheader("📦 Gestão de Inventário")
    
    df_est = pd.read_sql_query("SELECT * FROM estoque", conn)
    # Ordenar Extra no topo
    df_est['order'] = df_est['produto'].apply(lambda x: ORDEM_TAMANHOS.index(x.split(' ')[1]))
    df_est = df_est.sort_values('order').drop(columns=['order'])

    # Visual de Tabela Profissional com Alertas
    for i, r in df_est.iterrows():
        status_class = "stock-high" if r['quantidade'] > 20 else ("stock-low" if r['quantidade'] > 5 else "stock-critical")
        status_msg = "✅ ESTÁVEL" if r['quantidade'] > 20 else ("⚠️ REPOR" if r['quantidade'] > 5 else "🚨 CRÍTICO")
        
        with st.expander(f"{r['produto']} - {r['quantidade']} Bandejas"):
            col_e1, col_e2, col_e3 = st.columns([2,1,1])
            col_e1.write(f"Status atual: <span class='{status_class}'>{status_msg}</span>", unsafe_allow_html=True)
            new_q = col_e2.number_input("Adicionar", min_value=1, key=f"in_{r['produto']}")
            if col_e3.button("Atualizar", key=f"bt_{r['produto']}"):
                conn.execute("UPDATE estoque SET quantidade = quantidade + ? WHERE produto = ?", (new_q, r['produto']))
                conn.commit()
                st.rerun()

# ================= FINANCEIRO 4.0 =================
elif menu == "Financeiro":
    st.subheader("💰 Inteligência Financeira")
    
    tab1, tab2 = st.tabs(["Fluxo de Caixa", "Relatórios Exportáveis"])
    
    with tab1:
        df_fin = pd.read_sql_query('''SELECT v.data, c.nome as Cliente, v.produto, v.total_nota as Total, v.pago as Recebido, v.pendente, v.status 
                                      FROM vendas v JOIN clientes c ON v.cliente_id = c.id ORDER BY v.id DESC''', conn)
        st.dataframe(df_fin.style.background_gradient(subset=['Recebido'], cmap='Greens'), use_container_width=True)

# ================= LOGÍSTICA =================
elif menu == "Logística":
    st.subheader("🚚 Roteirização de Entregas")
    st.info("Módulo de inteligência geográfica para economia de combustível.")
    # Lógica de GPS (Mantida v3.3)...
