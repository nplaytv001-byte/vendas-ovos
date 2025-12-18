import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
from streamlit_option_menu import option_menu

# --- CONFIGURAÇÃO DE ALTO NÍVEL ---
st.set_page_config(page_title="EggGestão Midnight Pro", layout="wide", page_icon="🥚")

# --- CSS DARK TOTAL (Blindagem de Cores) ---
st.markdown("""
    <style>
    /* 1. FUNDO GERAL E TEXTOS */
    .stApp {
        background-color: #0F172A !important;
        color: #F8FAFC !important;
    }
    
    /* Forçar todos os textos para branco/claro */
    h1, h2, h3, h4, h5, h6, p, label, span, div {
        color: #F8FAFC !important;
    }

    /* 2. SIDEBAR ESCURA */
    [data-testid="stSidebar"] {
        background-color: #020617 !important;
        border-right: 1px solid #1E293B;
    }

    /* 3. CARDS DE MÉTRICAS DARK */
    div[data-testid="stMetric"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        padding: 20px !important;
        border-radius: 15px !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3) !important;
    }
    div[data-testid="stMetricValue"] > div {
        color: #FBBF24 !important; /* Valores em Dourado */
        font-weight: 800 !important;
    }

    /* 4. INPUTS E CAIXAS DE SELEÇÃO */
    input, select, textarea, [data-baseweb="select"] {
        background-color: #1E293B !important;
        color: white !important;
        border: 1px solid #475569 !important;
        border-radius: 8px !important;
    }
    
    /* 5. BOTÕES PREMIUM */
    .stButton>button {
        background: linear-gradient(135deg, #FBBF24 0%, #D97706 100%) !important;
        color: #0F172A !important;
        font-weight: 700 !important;
        border: none !important;
        padding: 10px 20px !important;
        width: 100% !important;
        border-radius: 10px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* 6. TABELAS (DATAFRAMES) */
    .stDataFrame {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
    }

    /* 7. CARDS CUSTOMIZADOS */
    .card-dark {
        background-color: #1E293B;
        padding: 25px;
        border-radius: 15px;
        border: 1px solid #334155;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO DO BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('ovos_midnight.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY, nome TEXT, tel TEXT, endereco TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS estoque (produto TEXT PRIMARY KEY, qtd INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vendas (id INTEGER PRIMARY KEY, cli_id INTEGER, data TEXT, prod TEXT, valor REAL, qtd INTEGER, total REAL, pago REAL, pendente REAL)''')
    
    # Prioridade: Ovo Extra sempre em primeiro
    prods = ["Branco Extra", "Vermelho Extra", "Branco Grande", "Vermelho Grande", "Branco Médio", "Vermelho Médio", "Branco Jumbo", "Vermelho Jumbo"]
    for p in prods:
        c.execute("INSERT OR IGNORE INTO estoque (produto, qtd) VALUES (?, 0)", (p,))
    conn.commit()
    return conn

conn = init_db()

# --- SIDEBAR NAV ---
with st.sidebar:
    st.markdown("<h1 style='color:#FBBF24; text-align:center;'>🥚 EGG Midnight</h1>", unsafe_allow_html=True)
    st.write("---")
    menu = option_menu(
        None, ["Home", "Vendas", "Estoque", "Financeiro", "Clientes"],
        icons=['house', 'cart3', 'box', 'currency-dollar', 'person-badge'],
        menu_icon="cast", default_index=0,
        styles={
            "container": {"background-color": "transparent"},
            "nav-link": {"color": "white", "font-size": "14px", "text-align": "left", "margin":"5px"},
            "nav-link-selected": {"background-color": "#FBBF24", "color": "#0F172A"},
        }
    )

# ================= HOME / DASHBOARD =================
if menu == "Home":
    st.markdown("<h2 style='color:#FBBF24 !important;'>📊 Visão de Comando</h2>", unsafe_allow_html=True)
    
    df_v = pd.read_sql_query("SELECT * FROM vendas", conn)
    total_receita = df_v['total'].sum() if not df_v.empty else 0
    total_pendente = df_v['pendente'].sum() if not df_v.empty else 0
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Faturamento Mensal", f"R$ {total_receita:,.2f}")
    with c2: st.metric("Contas a Receber", f"R$ {total_pendente:,.2f}")
    with c3:
        qtd_extra = pd.read_sql_query("SELECT SUM(qtd) FROM vendas WHERE prod LIKE '%Extra%'", conn).iloc[0,0] or 0
        st.metric("Total Ovo Extra", f"{int(qtd_extra)} bds")
    with c4:
        cli_count = pd.read_sql_query("SELECT COUNT(*) FROM clientes", conn).iloc[0,0]
        st.metric("Base de Clientes", f"{cli_count} ativos")

    st.markdown("---")
    
    col_l, col_r = st.columns([2,1])
    with col_l:
        st.markdown("<div class='card-dark'><b>Desempenho Semanal</b>", unsafe_allow_html=True)
        if not df_v.empty:
            df_v['data'] = pd.to_datetime(df_v['data'])
            vendas_diarias = df_v.groupby('data')['total'].sum().reset_index()
            fig = px.area(vendas_diarias, x='data', y='total', color_discrete_sequence=['#FBBF24'])
            fig.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                              font=dict(color="white"), xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("Inicie as vendas para visualizar o gráfico.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r:
        st.markdown("<div class='card-dark'><b>Níveis de Estoque</b>", unsafe_allow_html=True)
        df_est_pie = pd.read_sql_query("SELECT * FROM estoque WHERE qtd > 0", conn)
        if not df_est_pie.empty:
            fig_pie = px.pie(df_est_pie, values='qtd', names='produto', hole=.5, color_discrete_sequence=px.colors.sequential.YlOrBr)
            fig_pie.update_layout(height=300, showlegend=False, paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_pie, use_container_width=True)
        else: st.write("Estoque zerado.")
        st.markdown("</div>", unsafe_allow_html=True)

# ================= VENDAS (PDV) =================
elif menu == "Vendas":
    st.markdown("<h2 style='color:#FBBF24 !important;'>🛒 Frente de Caixa</h2>", unsafe_allow_html=True)
    
    df_cli = pd.read_sql_query("SELECT * FROM clientes", conn)
    if df_cli.empty:
        st.warning("⚠️ Cadastre um cliente primeiro.")
    else:
        col_f, col_r = st.columns([2, 1])
        with col_f:
            st.markdown("<div class='card-dark'>", unsafe_allow_html=True)
            with st.form("pdv_midnight", clear_on_submit=True):
                cli_sel = st.selectbox("Selecione o Cliente", df_cli['nome'].tolist())
                c1, c2, c3 = st.columns(3)
                tam = c1.selectbox("Tamanho (Top: Extra)", ["Extra", "Jumbo", "Grande", "Médio"])
                cor = c2.selectbox("Cor", ["Branco", "Vermelho"])
                qtd = c3.number_input("Qtd Bandejas", min_value=1, step=1)
                
                prod_name = f"{cor} {tam}"
                # Inteligência de Preço (Histórico)
                last_p = pd.read_sql_query(f"SELECT valor FROM vendas WHERE prod = '{prod_name}' ORDER BY id DESC LIMIT 1", conn)
                price_sug = last_p.iloc[0,0] if not last_p.empty else 15.0
                
                v_unit = st.number_input("Preço Unitário (R$)", value=float(price_sug))
                pago = st.number_input("Valor Pago Agora (R$)", value=float(v_unit * qtd))
                
                if st.form_submit_button("CONCLUIR VENDA"):
                    total = v_unit * qtd
                    pend = total - pago
                    cli_id = df_cli[df_cli['nome'] == cli_sel]['id'].values[0]
                    
                    est_atual = conn.execute(f"SELECT qtd FROM estoque WHERE produto = '{prod_name}'").fetchone()[0]
                    if est_atual >= qtd:
                        conn.execute("INSERT INTO vendas (cli_id, data, prod, valor, qtd, total, pago, pendente) VALUES (?,?,?,?,?,?,?,?)",
                                    (int(cli_id), str(date.today()), prod_name, v_unit, qtd, total, pago, pend))
                        conn.execute(f"UPDATE estoque SET qtd = qtd - {qtd} WHERE produto = '{prod_name}'")
                        conn.commit()
                        st.balloons()
                        st.success(f"Venda para {cli_sel} registrada!")
                        st.rerun()
                    else: st.error("Erro: Estoque insuficiente!")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col_r:
            st.markdown(f"""
            <div style="background: linear-gradient(180deg, #1E293B 0%, #0F172A 100%); padding: 40px; border-radius: 20px; border: 2px solid #FBBF24; text-align: center;">
                <p style="color: #94A3B8; margin-bottom: 5px; font-size: 14px;">TOTAL À RECEBER</p>
                <h1 style="color: #FBBF24; margin: 0; font-size: 50px;">R$ {v_unit * qtd:,.2f}</h1>
                <p style="font-size: 12px; margin-top: 20px; color: #64748B;">Produto: {prod_name}</p>
            </div>
            """, unsafe_allow_html=True)

# ================= ESTOQUE =================
elif menu == "Estoque":
    st.markdown("<h2 style='color:#FBBF24 !important;'>📦 Controle de Inventário</h2>", unsafe_allow_html=True)
    
    col_e1, col_e2 = st.columns([1, 2])
    with col_e1:
        st.markdown("<div class='card-dark'><b>Entrada de Produto</b>", unsafe_allow_html=True)
        with st.form("entrada"):
            prod_list = pd.read_sql_query("SELECT produto FROM estoque", conn)
            p_sel = st.selectbox("Produto", prod_list['produto'].tolist())
            q_add = st.number_input("Adicionar Qtd", min_value=1)
            if st.form_submit_button("Atualizar Estoque"):
                conn.execute(f"UPDATE estoque SET qtd = qtd + ? WHERE produto = ?", (q_add, p_sel))
                conn.commit()
                st.success("Estoque atualizado!")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_e2:
        df_full = pd.read_sql_query("SELECT produto as 'Produto', qtd as 'Saldo' FROM estoque ORDER BY Saldo DESC", conn)
        st.dataframe(df_full, use_container_width=True, hide_index=True)

# ================= CLIENTES =================
elif menu == "Clientes":
    st.markdown("<h2 style='color:#FBBF24 !important;'>👤 Gestão de Carteira</h2>", unsafe_allow_html=True)
    with st.expander("➕ CADASTRAR NOVO CLIENTE"):
        with st.form("crm_midnight"):
            n = st.text_input("Nome Comercial")
            t = st.text_input("WhatsApp")
            e = st.text_input("Endereço de Entrega")
            if st.form_submit_button("Salvar"):
                conn.execute("INSERT INTO clientes (nome, tel, endereco) VALUES (?,?,?)", (n,t,e))
                conn.commit()
                st.success("Cliente cadastrado!")
                st.rerun()
    
    df_c = pd.read_sql_query("SELECT nome as 'Cliente', tel as 'WhatsApp', endereco as 'Endereço' FROM clientes", conn)
    st.dataframe(df_c, use_container_width=True, hide_index=True)

# ================= FINANCEIRO =================
elif menu == "Financeiro":
    st.markdown("<h2 style='color:#FBBF24 !important;'>💰 Fluxo Financeiro</h2>", unsafe_allow_html=True)
    df_f = pd.read_sql_query('''SELECT v.data as 'Data', c.nome as 'Cliente', v.prod as 'Produto', v.total as 'Total', v.pendente as 'Débito' 
                                FROM vendas v JOIN clientes c ON v.cli_id = c.id ORDER BY v.id DESC''', conn)
    st.markdown("<div class='card-dark'>", unsafe_allow_html=True)
    st.dataframe(df_f, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)
