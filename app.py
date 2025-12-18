import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date, timedelta
import urllib.parse
from streamlit_option_menu import option_menu

# --- CONFIGURAÇÃO DE ALTO NÍVEL ---
st.set_page_config(page_title="EggGestão Pro Enterprise", layout="wide", page_icon="🥚")

# --- CSS PROPRIETÁRIO (Visual Profissional SaaS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #F1F5F9; }

    /* Estilização da Sidebar */
    [data-testid="stSidebar"] { background-color: #0F172A !important; border-right: 1px solid #1E293B; }
    
    /* Cards Profissionais */
    .stMetric {
        background-color: white !important;
        padding: 20px !important;
        border-radius: 12px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
        border: 1px solid #E2E8F0 !important;
    }
    
    .card-pro {
        background: white;
        padding: 25px;
        border-radius: 16px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }

    /* Botão de Ação Principal */
    .stButton>button {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        color: #FBBF24 !important;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
        width: 100%;
        transition: all 0.3s;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }

    /* Tabelas e Dataframes */
    .stDataFrame { border-radius: 12px; overflow: hidden; border: 1px solid #E2E8F0; }
    
    /* Tags de Status */
    .status-pago { background-color: #DCFCE7; color: #166534; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
    .status-pendente { background-color: #FEE2E2; color: #991B1B; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO DO BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('ovos_elite.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY, nome TEXT, tel TEXT, endereco TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS estoque (produto TEXT PRIMARY KEY, qtd INTEGER, validade TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vendas (id INTEGER PRIMARY KEY, cli_id INTEGER, data TEXT, prod TEXT, valor REAL, qtd INTEGER, total REAL, pago REAL, pendente REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS despesas (id INTEGER PRIMARY KEY, data TEXT, cat TEXT, valor REAL)''')
    
    prods = ["Branco Extra", "Vermelho Extra", "Branco Grande", "Vermelho Grande", "Branco Médio", "Vermelho Médio", "Branco Jumbo", "Vermelho Jumbo"]
    for p in prods:
        c.execute("INSERT OR IGNORE INTO estoque (produto, qtd, validade) VALUES (?, 0, ?)", (p, str(date.today() + timedelta(days=21))))
    conn.commit()
    return conn

conn = init_db()

# --- SIDEBAR COM MENU MODERNO ---
with st.sidebar:
    st.markdown("<h1 style='color:#FBBF24; text-align:center;'>🥚 EGG PRO</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#94A3B8; text-align:center; font-size:12px;'>SISTEMA DE GESTÃO ELITE</p>", unsafe_allow_html=True)
    st.write("---")
    
    menu = option_menu(
        None, ["Dashboard", "Vendas (PDV)", "Estoque & Lotes", "Financeiro", "CRM Clientes"],
        icons=['speedometer2', 'cart3', 'box-seam', 'bank', 'people'],
        menu_icon="cast", default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "nav-link": {"font-size": "14px", "color": "#94A3B8", "text-align": "left", "margin":"5px"},
            "nav-link-selected": {"background-color": "#1E293B", "color": "#FBBF24"},
        }
    )

# ================= 📊 DASHBOARD ESTRATÉGICO =================
if menu == "Dashboard":
    st.markdown("### 📈 Performance Executiva")
    
    # Métricas de Topo
    c1, c2, c3, c4 = st.columns(4)
    df_v = pd.read_sql_query("SELECT * FROM vendas", conn)
    total_receita = df_v['total'].sum()
    total_pendente = df_v['pendente'].sum()
    
    with c1: st.metric("Faturamento Total", f"R$ {total_receita:,.2f}")
    with c2: st.metric("Inadimplência", f"R$ {total_pendente:,.2f}", delta=f"{-(total_pendente/total_receita*100 if total_receita>0 else 0):.1f}%", delta_color="inverse")
    with c3:
        qtd_extra = pd.read_sql_query("SELECT SUM(qtd) FROM vendas WHERE prod LIKE '%Extra%'", conn).iloc[0,0] or 0
        st.metric("Saída Ovo Extra", f"{int(qtd_extra)} bds")
    with c4:
        df_est = pd.read_sql_query("SELECT SUM(qtd) FROM estoque", conn)
        st.metric("Estoque Global", f"{int(df_est.iloc[0,0])} bds")

    st.markdown("---")
    
    # Gráficos Pro
    col_l, col_r = st.columns([2,1])
    
    with col_l:
        st.markdown("<div class='card-pro'><b>Tendência de Vendas (7 Dias)</b>", unsafe_allow_html=True)
        df_v['data'] = pd.to_datetime(df_v['data'])
        vendas_diarias = df_v.groupby('data')['total'].sum().reset_index()
        fig = px.area(vendas_diarias, x='data', y='total', line_shape='spline', color_discrete_sequence=['#0F172A'])
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=20,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r:
        st.markdown("<div class='card-pro'><b>Mix de Produtos</b>", unsafe_allow_html=True)
        mix = df_v.groupby('prod')['qtd'].sum().reset_index()
        fig_mix = px.pie(mix, values='qtd', names='prod', hole=.6, color_discrete_sequence=px.colors.qualitative.Prism)
        fig_mix.update_layout(height=300, margin=dict(l=0,r=0,t=20,b=0), showlegend=False)
        st.plotly_chart(fig_mix, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ================= 🛒 VENDAS (PDV INTELIGENTE) =================
elif menu == "Vendas (PDV)":
    st.markdown("### 🛒 Ponto de Venda Profissional")
    
    df_cli = pd.read_sql_query("SELECT * FROM clientes", conn)
    if df_cli.empty:
        st.warning("⚠️ Cadastre um cliente no menu CRM para começar.")
    else:
        with st.container():
            col_form, col_resumo = st.columns([2, 1])
            
            with col_form:
                st.markdown("<div class='card-pro'>", unsafe_allow_html=True)
                with st.form("pdv_v5"):
                    cli_sel = st.selectbox("Cliente", df_cli['nome'].tolist())
                    
                    c1, c2, c3 = st.columns(3)
                    # OVO EXTRA SEMPRE NO TOPO DA LISTA
                    tam = c1.selectbox("Tamanho", ["Extra", "Jumbo", "Grande", "Médio"])
                    cor = c2.selectbox("Cor", ["Branco", "Vermelho"])
                    qtd = c3.number_input("Qtd Bandejas", min_value=1, step=1)
                    
                    # Preço Sugerido (Busca última venda)
                    prod_name = f"{cor} {tam}"
                    last_p = pd.read_sql_query(f"SELECT valor FROM vendas WHERE prod = '{prod_name}' ORDER BY id DESC LIMIT 1", conn)
                    price_sug = last_p.iloc[0,0] if not last_p.empty else 15.0
                    
                    val_unit = st.number_input("Preço Unitário (R$)", value=float(price_sug))
                    pago = st.number_input("Valor Recebido (R$)", value=float(val_unit * qtd))
                    
                    if st.form_submit_button("CONSOLIDAR VENDA"):
                        total = val_unit * qtd
                        pend = total - pago
                        cli_id = df_cli[df_cli['nome'] == cli_sel]['id'].values[0]
                        
                        # Check Estoque
                        est_atual = conn.execute(f"SELECT qtd FROM estoque WHERE produto = '{prod_name}'").fetchone()[0]
                        if est_atual >= qtd:
                            conn.execute("INSERT INTO vendas (cli_id, data, prod, valor, qtd, total, pago, pendente) VALUES (?,?,?,?,?,?,?,?)",
                                        (int(cli_id), str(date.today()), prod_name, val_unit, qtd, total, pago, pend))
                            conn.execute(f"UPDATE estoque SET qtd = qtd - {qtd} WHERE produto = '{prod_name}'")
                            conn.commit()
                            st.balloons()
                            st.success("Venda realizada!")
                        else:
                            st.error(f"Estoque insuficiente! Disponível: {est_atual}")
                st.markdown("</div>", unsafe_allow_html=True)

            with col_resumo:
                st.markdown(f"""
                <div style="background:#0F172A; color:white; padding:30px; border-radius:16px; text-align:center;">
                    <p style="color:#94A3B8; margin-bottom:5px;">VALOR TOTAL</p>
                    <h1 style="color:#FBBF24; margin:0;">R$ {val_unit * qtd:,.2f}</h1>
                    <hr style="opacity:0.1">
                    <p style="font-size:12px; color:#94A3B8;">Produto Selecionado: <b>{cor} {tam}</b></p>
                </div>
                """, unsafe_allow_html=True)

# ================= 📦 ESTOQUE & LOTES =================
elif menu == "Estoque & Lotes":
    st.markdown("### 📦 Gestão de Inventário e Validade")
    
    # Alerta de Validade
    df_est = pd.read_sql_query("SELECT * FROM estoque", conn)
    df_est['validade'] = pd.to_datetime(df_est['validade'])
    vencendo = df_est[df_est['validade'] <= pd.to_datetime(date.today() + timedelta(days=3))]
    
    if not vencendo.empty:
        st.error(f"⚠️ Atenção: {len(vencendo)} lotes vencem em menos de 3 dias!")

    col_e1, col_e2 = st.columns([1, 2])
    with col_e1:
        st.markdown("<div class='card-pro'><b>Entrada de Lote</b>", unsafe_allow_html=True)
        with st.form("entrada"):
            p_ent = st.selectbox("Produto", df_est['produto'].tolist())
            q_ent = st.number_input("Quantidade", min_value=1)
            v_ent = st.date_input("Validade do Lote", value=date.today() + timedelta(days=21))
            if st.form_submit_button("Registrar Entrada"):
                conn.execute(f"UPDATE estoque SET qtd = qtd + ?, validade = ? WHERE produto = ?", (q_ent, str(v_ent), p_ent))
                conn.commit()
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_e2:
        # Estilização da tabela de estoque
        st.markdown("<b>Status Geral de Prateleira</b>", unsafe_allow_html=True)
        st.dataframe(df_est.sort_values(by='qtd', ascending=False), use_container_width=True, hide_index=True)

# ================= 💰 FINANCEIRO ELITE =================
elif menu == "Financeiro":
    st.markdown("### 💰 Controladoria e Fluxo de Caixa")
    
    df_v = pd.read_sql_query('''SELECT v.data, c.nome as cliente, v.prod, v.total, v.pendente FROM vendas v 
                                JOIN clientes c ON v.cli_id = c.id ORDER BY v.id DESC''', conn)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='card-pro'><b>Últimas Transações</b>", unsafe_allow_html=True)
        st.dataframe(df_v, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with c2:
        st.markdown("<div class='card-pro'><b>Contas a Receber</b>", unsafe_allow_html=True)
        devedores = df_v[df_v['pendente'] > 0]
        st.dataframe(devedores, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ================= 👤 CRM CLIENTES =================
elif menu == "CRM Clientes":
    st.markdown("### 👤 Inteligência de Clientes")
    
    with st.expander("➕ Cadastrar Novo Cliente"):
        with st.form("crm_add"):
            n = st.text_input("Nome/Razão Social")
            t = st.text_input("WhatsApp")
            e = st.text_input("Endereço de Entrega")
            if st.form_submit_button("Salvar"):
                conn.execute("INSERT INTO clientes (nome, tel, endereco) VALUES (?,?,?)", (n,t,e))
                conn.commit()
                st.success("Cliente cadastrado!")
                st.rerun()

    df_cli_list = pd.read_sql_query("SELECT * FROM clientes", conn)
    st.dataframe(df_cli_list, use_container_width=True, hide_index=True)
