import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
from streamlit_option_menu import option_menu

# --- CONFIGURAÇÃO DE ALTO NÍVEL ---
st.set_page_config(page_title="EggGestão Pro Enterprise", layout="wide", page_icon="🥚")

# --- CSS BLINDADO (Garante que as cores não sumam) ---
st.markdown("""
    <style>
    /* 1. FUNDO GERAL E TEXTO BASE */
    .main { background-color: #F8FAFC !important; }
    
    /* Força cor de texto em títulos e labels */
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown {
        color: #1E293B !important; 
    }

    /* 2. SIDEBAR (MENU LATERAL) - SEMPRE ESCURO */
    [data-testid="stSidebar"] {
        background-color: #0F172A !important;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }

    /* 3. CARDS DE MÉTRICAS (RESOLVE O TEXTO SUMINDO) */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        padding: 15px !important;
        border-radius: 12px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
    }
    div[data-testid="stMetricValue"] > div {
        color: #0F172A !important; /* Valor da métrica sempre escuro */
    }
    div[data-testid="stMetricLabel"] > div > p {
        color: #64748B !important; /* Label sempre cinza escuro */
    }

    /* 4. CAIXAS DE ENTRADA (INPUTS) */
    input, select, textarea {
        color: #1E293B !important; /* Texto digitado sempre escuro */
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
    }

    /* 5. CARDS CUSTOMIZADOS */
    .card-pro {
        background-color: white !important;
        padding: 25px;
        border-radius: 16px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        color: #1E293B !important;
    }

    /* 6. BOTÕES */
    .stButton>button {
        background: #0F172A !important;
        color: #FBBF24 !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        border: none !important;
    }
    
    /* 7. AJUSTE DE DATAFRAMES */
    .stDataFrame {
        background-color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO DO BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('ovos_elite.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY, nome TEXT, tel TEXT, endereco TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS estoque (produto TEXT PRIMARY KEY, qtd INTEGER, validade TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vendas (id INTEGER PRIMARY KEY, cli_id INTEGER, data TEXT, prod TEXT, valor REAL, qtd INTEGER, total REAL, pago REAL, pendente REAL)''')
    
    # Ordem de prioridade (Ovo Extra em primeiro)
    prods = ["Branco Extra", "Vermelho Extra", "Branco Grande", "Vermelho Grande", "Branco Médio", "Vermelho Médio", "Branco Jumbo", "Vermelho Jumbo"]
    for p in prods:
        c.execute("INSERT OR IGNORE INTO estoque (produto, qtd, validade) VALUES (?, 0, ?)", (p, str(date.today() + timedelta(days=21))))
    conn.commit()
    return conn

conn = init_db()

# --- SIDEBAR COM MENU ---
with st.sidebar:
    st.markdown("<h1 style='color:#FBBF24; text-align:center;'>🥚 EGG PRO</h1>", unsafe_allow_html=True)
    st.write("---")
    
    menu = option_menu(
        None, ["Dashboard", "Vendas (PDV)", "Estoque", "Financeiro", "Clientes"],
        icons=['speedometer2', 'cart3', 'box-seam', 'bank', 'people'],
        menu_icon="cast", default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "nav-link": {"font-size": "14px", "color": "#94A3B8", "text-align": "left", "margin":"5px"},
            "nav-link-selected": {"background-color": "#1E293B", "color": "#FBBF24"},
        }
    )

# ================= DASHBOARD =================
if menu == "Dashboard":
    st.markdown("<h2 style='color:#0F172A !important;'>📊 Resumo de Performance</h2>", unsafe_allow_html=True)
    
    df_v = pd.read_sql_query("SELECT * FROM vendas", conn)
    total_receita = df_v['total'].sum() if not df_v.empty else 0
    total_pendente = df_v['pendente'].sum() if not df_v.empty else 0
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Faturamento", f"R$ {total_receita:,.2f}")
    with c2: st.metric("A Receber", f"R$ {total_pendente:,.2f}")
    with c3:
        qtd_extra = pd.read_sql_query("SELECT SUM(qtd) FROM vendas WHERE prod LIKE '%Extra%'", conn).iloc[0,0] or 0
        st.metric("Vendas Extra", f"{int(qtd_extra)} bds")
    with c4:
        st.metric("Status Caixa", "ABERTO")

    st.markdown("---")
    
    col_l, col_r = st.columns([2,1])
    with col_l:
        st.markdown("<div class='card-pro'><b>Vendas Diárias</b>", unsafe_allow_html=True)
        if not df_v.empty:
            df_v['data'] = pd.to_datetime(df_v['data'])
            vendas_diarias = df_v.groupby('data')['total'].sum().reset_index()
            fig = px.line(vendas_diarias, x='data', y='total', markers=True, color_discrete_sequence=['#0F172A'])
            fig.update_layout(height=250, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhuma venda registrada ainda.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r:
        st.markdown("<div class='card-pro'><b>Estoque Crítico</b>", unsafe_allow_html=True)
        df_est = pd.read_sql_query("SELECT produto, qtd FROM estoque WHERE qtd < 10", conn)
        st.dataframe(df_est, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ================= VENDAS (PDV) =================
elif menu == "Vendas (PDV)":
    st.markdown("<h2 style='color:#0F172A !important;'>🛒 Ponto de Venda</h2>", unsafe_allow_html=True)
    
    df_cli = pd.read_sql_query("SELECT * FROM clientes", conn)
    if df_cli.empty:
        st.warning("⚠️ Cadastre um cliente primeiro.")
    else:
        col_form, col_resumo = st.columns([2, 1])
        
        with col_form:
            st.markdown("<div class='card-pro'>", unsafe_allow_html=True)
            with st.form("pdv_v5", clear_on_submit=True):
                cli_sel = st.selectbox("Cliente", df_cli['nome'].tolist())
                c1, c2, c3 = st.columns(3)
                tam = c1.selectbox("Tamanho (Prioridade: Extra)", ["Extra", "Jumbo", "Grande", "Médio"])
                cor = c2.selectbox("Cor", ["Branco", "Vermelho"])
                qtd = c3.number_input("Qtd Bandejas", min_value=1, step=1)
                
                prod_name = f"{cor} {tam}"
                last_p = pd.read_sql_query(f"SELECT valor FROM vendas WHERE prod = '{prod_name}' ORDER BY id DESC LIMIT 1", conn)
                price_sug = last_p.iloc[0,0] if not last_p.empty else 15.0
                
                c4, c5 = st.columns(2)
                val_unit = c4.number_input("Preço Unitário (R$)", value=float(price_sug))
                pago = c5.number_input("Valor Pago Agora (R$)", value=float(val_unit * qtd))
                
                if st.form_submit_button("FINALIZAR VENDA"):
                    total = val_unit * qtd
                    pend = total - pago
                    cli_id = df_cli[df_cli['nome'] == cli_sel]['id'].values[0]
                    
                    est_atual = conn.execute(f"SELECT qtd FROM estoque WHERE produto = '{prod_name}'").fetchone()[0]
                    if est_atual >= qtd:
                        conn.execute("INSERT INTO vendas (cli_id, data, prod, valor, qtd, total, pago, pendente) VALUES (?,?,?,?,?,?,?,?)",
                                    (int(cli_id), str(date.today()), prod_name, val_unit, qtd, total, pago, pend))
                        conn.execute(f"UPDATE estoque SET qtd = qtd - {qtd} WHERE produto = '{prod_name}'")
                        conn.commit()
                        st.success(f"Venda para {cli_sel} concluída!")
                        st.rerun()
                    else:
                        st.error(f"Estoque insuficiente de {prod_name}!")
            st.markdown("</div>", unsafe_allow_html=True)

        with col_resumo:
            st.markdown(f"""
            <div style="background:#0F172A; color:white; padding:30px; border-radius:16px; text-align:center;">
                <p style="color:#94A3B8; margin-bottom:5px; font-size:14px;">TOTAL DO PEDIDO</p>
                <h1 style="color:#FBBF24; margin:0; font-size:42px;">R$ {val_unit * qtd:,.2f}</h1>
                <p style="font-size:12px; margin-top:15px; opacity:0.7;">Item: {cor} {tam}</p>
            </div>
            """, unsafe_allow_html=True)

# ================= ESTOQUE =================
elif menu == "Estoque":
    st.markdown("<h2 style='color:#0F172A !important;'>📦 Controle de Inventário</h2>", unsafe_allow_html=True)
    
    col_ent, col_tab = st.columns([1, 2])
    with col_ent:
        st.markdown("<div class='card-pro'><b>Entrada de Lote</b>", unsafe_allow_html=True)
        with st.form("entrada"):
            df_est_list = pd.read_sql_query("SELECT produto FROM estoque", conn)
            p_ent = st.selectbox("Produto", df_est_list['produto'].tolist())
            q_ent = st.number_input("Qtd Entrada", min_value=1)
            if st.form_submit_button("Atualizar Estoque"):
                conn.execute(f"UPDATE estoque SET qtd = qtd + ? WHERE produto = ?", (q_ent, p_ent))
                conn.commit()
                st.success("Estoque abastecido!")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_tab:
        df_full_est = pd.read_sql_query("SELECT produto, qtd, validade FROM estoque ORDER BY qtd DESC", conn)
        st.markdown("<b>Posição Atual de Estoque</b>", unsafe_allow_html=True)
        st.dataframe(df_full_est, use_container_width=True, hide_index=True)

# ================= CLIENTES =================
elif menu == "Clientes":
    st.markdown("<h2 style='color:#0F172A !important;'>👤 Gestão de Clientes</h2>", unsafe_allow_html=True)
    
    with st.expander("➕ CADASTRAR NOVO CLIENTE"):
        with st.form("crm_add"):
            n = st.text_input("Nome / Estabelecimento")
            t = st.text_input("WhatsApp")
            e = st.text_input("Endereço Completo")
            if st.form_submit_button("Salvar"):
                conn.execute("INSERT INTO clientes (nome, tel, endereco) VALUES (?,?,?)", (n,t,e))
                conn.commit()
                st.success("Cliente salvo!")
                st.rerun()

    df_cli_list = pd.read_sql_query("SELECT id, nome, tel, endereco FROM clientes", conn)
    st.dataframe(df_cli_list, use_container_width=True, hide_index=True)

# ================= FINANCEIRO =================
elif menu == "Financeiro":
    st.markdown("<h2 style='color:#0F172A !important;'>💰 Fluxo de Caixa</h2>", unsafe_allow_html=True)
    
    df_v_fin = pd.read_sql_query('''SELECT v.data, c.nome as cliente, v.prod, v.total, v.pendente FROM vendas v 
                                    JOIN clientes c ON v.cli_id = c.id ORDER BY v.id DESC''', conn)
    
    st.markdown("<div class='card-pro'><b>Histórico de Vendas e Débitos</b>", unsafe_allow_html=True)
    st.dataframe(df_v_fin, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)
