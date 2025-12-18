import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, date
from streamlit_option_menu import option_menu

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="EggGestão Titanium", layout="wide", page_icon="🥚")

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('ovos_titanium.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY, nome TEXT, tel TEXT, endereco TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS estoque (produto TEXT PRIMARY KEY, qtd INTEGER, minimo INTEGER DEFAULT 5)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY, cli_id INTEGER, data TEXT, prod TEXT, 
                valor_unit REAL, qtd INTEGER, total REAL, 
                pago_pix REAL, pago_dinheiro REAL, pendente REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS despesas (id INTEGER PRIMARY KEY, data TEXT, descricao TEXT, valor REAL)''')
    
    prods = ["Branco Extra", "Vermelho Extra", "Branco Grande", "Vermelho Grande", "Branco Médio", "Vermelho Médio", "Branco Jumbo", "Vermelho Jumbo"]
    for p in prods:
        c.execute("INSERT OR IGNORE INTO estoque (produto, qtd) VALUES (?, 0)", (p,))
    conn.commit()
    return conn

conn = init_db()

# --- ESTILIZAÇÃO ---
st.markdown("""
    <style>
    .stApp { background-color: #0F172A; color: #F8FAFC; }
    .card { background-color: #1E293B; padding: 20px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 15px; }
    .metric-card { background: #1E293B; border-left: 5px solid #FBBF24; padding: 15px; border-radius: 8px; }
    .stButton>button { border-radius: 8px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES ---
def gerar_recibo_whatsapp(venda, cliente_nome):
    texto = f"*RECIBO - EGG MIDNIGHT*\n\n" \
            f"👤 *Cliente:* {cliente_nome}\n" \
            f"📦 *Produto:* {venda['prod']}\n" \
            f"🔢 *Qtd:* {venda['qtd']} bandejas\n" \
            f"💰 *Total:* R$ {venda['total']:.2f}\n" \
            f"✅ *Pago:* R$ {(venda['pago_pix'] + venda['pago_dinheiro']):.2f}\n" \
            f"🚩 *Pendente:* R$ {venda['pendente']:.2f}\n\n" \
            f"Obrigado pela preferência! 🥚"
    return texto

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2613/2613728.png", width=80)
    menu = option_menu("Menu", ["Dashboard", "PDV", "Financeiro", "Estoque", "Clientes"],
        icons=['graph-up', 'cart', 'cash-stack', 'box-seam', 'people'], 
        menu_icon="cast", default_index=0,
        styles={"nav-link-selected": {"background-color": "#FBBF24", "color": "#0F172A"}})

# --- 1. DASHBOARD ---
if menu == "Dashboard":
    st.title("🚀 Painel de Comando")
    
    df_v = pd.read_sql_query("SELECT * FROM vendas", conn)
    df_d = pd.read_sql_query("SELECT * FROM despesas", conn)
    
    # Métricas Inteligentes
    receita = df_v['total'].sum() if not df_v.empty else 0
    custos = df_d['valor'].sum() if not df_d.empty else 0
    lucro = receita - custos
    pendente = df_v['pendente'].sum() if not df_v.empty else 0

    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown(f"<div class='metric-card'>Vendas Brutas<br><h2>R$ {receita:,.2f}</h2></div>", unsafe_allow_html=True)
    with m2: st.markdown(f"<div class='metric-card'>Despesas<br><h2 style='color:#F87171'>R$ {custos:,.2f}</h2></div>", unsafe_allow_html=True)
    with m3: st.markdown(f"<div class='metric-card'>Lucro Real<br><h2 style='color:#34D399'>R$ {lucro:,.2f}</h2></div>", unsafe_allow_html=True)
    with m4: st.markdown(f"<div class='metric-card'>A Receber<br><h2 style='color:#FBBF24'>R$ {pendente:,.2f}</h2></div>", unsafe_allow_html=True)

    # Gráfico de Tendência
    if not df_v.empty:
        st.markdown("### 📈 Tendência de Vendas")
        df_v['data'] = pd.to_datetime(df_v['data'])
        fig = px.line(df_v.groupby('data')['total'].sum().reset_index(), x='data', y='total', 
                      template="plotly_dark", color_discrete_sequence=['#FBBF24'])
        st.plotly_chart(fig, use_container_width=True)

# --- 2. PDV (VENDAS) ---
elif menu == "PDV":
    st.title("🛒 Frente de Caixa")
    
    df_est = pd.read_sql_query("SELECT * FROM estoque WHERE qtd > 0", conn)
    df_cli = pd.read_sql_query("SELECT * FROM clientes", conn)

    if df_cli.empty or df_est.empty:
        st.error("Certifique-se de ter Clientes cadastrados e Estoque disponível!")
    else:
        with st.form("pdv_form"):
            c1, c2 = st.columns(2)
            cli = c1.selectbox("Cliente", df_cli['nome'].tolist())
            prod = c2.selectbox("Produto em Estoque", df_est['produto'].tolist())
            
            q_max = int(df_est[df_est['produto'] == prod]['qtd'].values[0])
            
            c3, c4, c5 = st.columns(3)
            qtd = c3.number_input(f"Qtd (Máx {q_max})", 1, q_max)
            preco = c4.number_input("Preço Unitário", 0.0, 100.0, 15.0)
            total = qtd * preco
            c5.markdown(f"<br><b>TOTAL: R$ {total:.2f}</b>", unsafe_allow_html=True)
            
            st.divider()
            st.write("💳 **Pagamento**")
            p1, p2 = st.columns(2)
            pix = p1.number_input("Pix", 0.0, total)
            din = p2.number_input("Dinheiro", 0.0, total - pix)
            
            devendo = total - (pix + din)
            if devendo > 0:
                st.warning(f"Atenção: R$ {devendo:.2f} será registrado como Pendência.")
                
            if st.form_submit_button("CONCLUIR VENDA"):
                cli_id = df_cli[df_cli['nome'] == cli]['id'].values[0]
                conn.execute("INSERT INTO vendas (cli_id, data, prod, valor_unit, qtd, total, pago_pix, pago_dinheiro, pendente) VALUES (?,?,?,?,?,?,?,?,?)",
                            (int(cli_id), date.today().isoformat(), prod, preco, qtd, total, pix, din, devendo))
                conn.execute("UPDATE estoque SET qtd = qtd - ? WHERE produto = ?", (qtd, prod))
                conn.commit()
                st.success("Venda realizada com sucesso!")
                st.rerun()

# --- 3. FINANCEIRO (DESPESAS E PENDÊNCIAS) ---
elif menu == "Financeiro":
    tab1, tab2, tab3 = st.tabs(["💰 Contas a Receber", "📉 Despesas/Custos", "📊 Histórico Geral"])
    
    with tab1:
        st.subheader("Clientes que devem")
        df_p = pd.read_sql_query("""
            SELECT v.id, c.nome, v.prod, v.pendente 
            FROM vendas v JOIN clientes c ON v.cli_id = c.id WHERE v.pendente > 0
        """, conn)
        
        for _, row in df_p.iterrows():
            with st.expander(f"🔴 {row['nome']} - Dívida: R$ {row['pendente']:.2f}"):
                valor_pago = st.number_input("Quanto o cliente está pagando?", 0.0, row['pendente'], key=f"paga_{row['id']}")
                if st.button("Confirmar Recebimento", key=f"btn_{row['id']}"):
                    novo_pendente = row['pendente'] - valor_pago
                    conn.execute("UPDATE vendas SET pendente = ?, pago_pix = pago_pix + ? WHERE id = ?", (novo_pendente, valor_pago, row['id']))
                    conn.commit()
                    st.rerun()

    with tab2:
        st.subheader("Registrar Gasto (Milho, Luz, Diesel, etc)")
        with st.form("gasto"):
            d1, d2 = st.columns(2)
            desc = d1.text_input("Descrição")
            val = d2.number_input("Valor R$", 0.0)
            if st.form_submit_button("Salvar Despesa"):
                conn.execute("INSERT INTO despesas (data, descricao, valor) VALUES (?,?,?)", (date.today().isoformat(), desc, val))
                conn.commit()
                st.rerun()
        st.table(pd.read_sql_query("SELECT * FROM despesas ORDER BY id DESC", conn))

    with tab3:
        # Histórico com opção de gerar recibo
        df_h = pd.read_sql_query("SELECT v.*, c.nome FROM vendas v JOIN clientes c ON v.cli_id = c.id ORDER BY v.id DESC", conn)
        for _, row in df_h.iterrows():
            with st.container():
                st.markdown(f"<div class='card'>{row['data']} | {row['nome']} | {row['prod']} | Total: R${row['total']:.2f}</div>", unsafe_allow_html=True)
                recibo = gerar_recibo_whatsapp(row, row['nome'])
                st.download_button("Gerar Recibo (TXT)", recibo, file_name="recibo.txt", key=f"rec_{row['id']}")

# --- 4. ESTOQUE ---
elif menu == "Estoque":
    st.title("📦 Controle de Ovos")
    
    # Alerta de estoque baixo
    df_est = pd.read_sql_query("SELECT * FROM estoque", conn)
    baixo = df_est[df_est['qtd'] <= df_est['minimo']]
    if not baixo.empty:
        for p in baixo['produto']:
            st.error(f"⚠️ ESTOQUE CRÍTICO: {p}")

    with st.form("add_est"):
        c1, c2, c3 = st.columns(3)
        p = c1.selectbox("Produto", df_est['produto'].tolist())
        q = c2.number_input("Quantidade Adicionada", 1)
        m = c3.number_input("Alerta Mínimo", 1, 20, 5)
        if st.form_submit_button("Atualizar Estoque"):
            conn.execute("UPDATE estoque SET qtd = qtd + ?, minimo = ? WHERE produto = ?", (q, m, p))
            conn.commit()
            st.rerun()
    
    st.dataframe(df_est, use_container_width=True)

# --- 5. CLIENTES ---
elif menu == "Clientes":
    st.title("👤 Clientes")
    with st.expander("Cadastrar Novo"):
        with st.form("cli"):
            n = st.text_input("Nome")
            t = st.text_input("WhatsApp")
            e = st.text_input("Endereço")
            if st.form_submit_button("Salvar"):
                conn.execute("INSERT INTO clientes (nome, tel, endereco) VALUES (?,?,?)", (n, t, e))
                conn.commit()
                st.rerun()
    
    df_c = pd.read_sql_query("SELECT * FROM clientes", conn)
    for _, r in df_c.iterrows():
        col1, col2 = st.columns([4, 1])
        col1.info(f"**{r['nome']}** - {r['tel']} - {r['endereco']}")
        if col2.button("Excluir", key=f"del_{r['id']}"):
            conn.execute("DELETE FROM clientes WHERE id=?", (r['id'],))
            conn.commit()
            st.rerun()
