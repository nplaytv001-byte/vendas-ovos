import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, date

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="EggGestão Midnight Ultimate", layout="wide", page_icon="🥚")

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('ovos_ultimate.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY, nome TEXT, tel TEXT, endereco TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS estoque (produto TEXT PRIMARY KEY, qtd INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY, cli_id INTEGER, data TEXT, prod TEXT, 
                valor_unit REAL, qtd INTEGER, total REAL, 
                pago_pix REAL, pago_din REAL, pendente REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS despesas (id INTEGER PRIMARY KEY, data TEXT, desc TEXT, valor REAL)''')
    
    # Inicializa estoque se vazio
    prods = ["Branco Extra", "Vermelho Extra", "Branco Grande", "Vermelho Grande", "Branco Médio", "Vermelho Médio", "Branco Jumbo", "Vermelho Jumbo"]
    for p in prods:
        c.execute("INSERT OR IGNORE INTO estoque (produto, qtd) VALUES (?, 0)", (p,))
    conn.commit()
    return conn

conn = init_db()

# --- CSS PERSONALIZADO (DARK) ---
st.markdown("""
    <style>
    .stApp { background-color: #0F172A; color: #F8FAFC; }
    div[data-testid="stMetric"] { background-color: #1E293B; border: 1px solid #334155; padding: 15px; border-radius: 10px; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .card { background-color: #1E293B; padding: 20px; border-radius: 10px; border: 1px solid #334155; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- COMPONENTES DE DIÁLOGO (MODAIS) ---
@st.dialog("Editar Cliente")
def editar_cliente(id, nome_atual, tel_atual, end_atual):
    novo_nome = st.text_input("Nome", value=nome_atual)
    novo_tel = st.text_input("Telefone", value=tel_atual)
    novo_end = st.text_input("Endereço", value=end_atual)
    if st.button("Salvar Alterações"):
        conn.execute("UPDATE clientes SET nome=?, tel=?, endereco=? WHERE id=?", (novo_nome, novo_tel, novo_end, id))
        conn.commit()
        st.success("Cliente atualizado!")
        st.rerun()

# --- SIDEBAR NAV ---
with st.sidebar:
    st.title("🥚 EggMidnight")
    menu = st.radio("Navegação", ["Painel Geral", "Vender (PDV)", "Financeiro", "Estoque", "Clientes"])

# --- 1. PAINEL GERAL (DASHBOARD + CALENDÁRIO) ---
if menu == "Painel Geral":
    st.header("📊 Resumo do Negócio")
    
    df_v = pd.read_sql_query("SELECT * FROM vendas", conn)
    df_d = pd.read_sql_query("SELECT * FROM despesas", conn)
    
    total_receita = df_v['total'].sum() if not df_v.empty else 0
    total_pago = (df_v['pago_pix'].sum() + df_v['pago_din'].sum()) if not df_v.empty else 0
    total_pendente = df_v['pendente'].sum() if not df_v.empty else 0
    total_despesas = df_d['valor'].sum() if not df_d.empty else 0
    lucro = total_pago - total_despesas

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Receita Bruta", f"R$ {total_receita:,.2f}")
    m2.metric("A Receber (Dívidas)", f"R$ {total_pendente:,.2f}", delta_color="inverse")
    m3.metric("Despesas", f"R$ {total_despesas:,.2f}")
    m4.metric("Lucro em Caixa", f"R$ {lucro:,.2f}")

    if not df_v.empty:
        st.subheader("📅 Calendário de Receita (Vendas por Dia)")
        df_v['data'] = pd.to_datetime(df_v['data'])
        daily_revenue = df_v.groupby('data')['total'].sum().reset_index()
        fig = px.bar(daily_revenue, x='data', y='total', color_discrete_sequence=['#FBBF24'], template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

# --- 2. VENDER (PDV INTELIGENTE) ---
elif menu == "Vender (PDV)":
    st.header("🛒 Nova Venda")
    
    # Busca apenas produtos com estoque > 0
    df_est = pd.read_sql_query("SELECT * FROM estoque WHERE qtd > 0", conn)
    df_cli = pd.read_sql_query("SELECT * FROM clientes", conn)

    if df_cli.empty:
        st.error("Cadastre um cliente primeiro!")
    elif df_est.empty:
        st.warning("Estoque zerado! Abasteça na aba Estoque.")
    else:
        with st.container(border=True):
            c1, c2 = st.columns(2)
            cliente_sel = c1.selectbox("Selecione o Cliente", df_cli['nome'].tolist())
            produto_sel = c2.selectbox("Produto (Apenas em estoque)", df_est['produto'].tolist())
            
            # Pegar estoque maximo do produto selecionado
            qtd_max = int(df_est[df_est['produto'] == produto_sel]['qtd'].values[0])
            st.caption(f"Estoque disponível: {qtd_max} bandejas")

            st.divider()
            
            col_a, col_b, col_c = st.columns(3)
            qtd = col_a.number_input("Quantidade", min_value=1, max_value=qtd_max, step=1)
            preco_un = col_b.number_input("Preço Unitário (R$)", min_value=0.0, value=15.0)
            
            # CÁLCULO AUTOMÁTICO ENQUANTO DIGITA
            total_venda = qtd * preco_un
            col_c.markdown(f"### Total: <br> <span style='color:#FBBF24'>R$ {total_venda:.2f}</span>", unsafe_allow_html=True)
            
            st.write("💰 **Formas de Pagamento (Pode ser parcial)**")
            p1, p2, p3 = st.columns(3)
            pix = p1.number_input("Valor em PIX", min_value=0.0, max_value=total_venda, value=total_venda)
            din = p2.number_input("Valor em Dinheiro", min_value=0.0, max_value=(total_venda - pix), value=0.0)
            
            pendente = total_venda - (pix + din)
            cor_p = "#34D399" if pendente == 0 else "#F87171"
            p3.markdown(f"### Pendente: <br> <span style='color:{cor_p}'>R$ {pendente:.2f}</span>", unsafe_allow_html=True)

            if st.button("Finalizar e abater do estoque"):
                id_cli = int(df_cli[df_cli['nome'] == cliente_sel]['id'].values[0])
                conn.execute("""INSERT INTO vendas (cli_id, data, prod, valor_unit, qtd, total, pago_pix, pago_din, pendente) 
                             VALUES (?,?,?,?,?,?,?,?,?)""", 
                             (id_cli, date.today().isoformat(), produto_sel, preco_un, qtd, total_venda, pix, din, pendente))
                conn.execute("UPDATE estoque SET qtd = qtd - ? WHERE produto = ?", (qtd, produto_sel))
                conn.commit()
                st.balloons()
                st.success("Venda registrada!")
                st.rerun()

# --- 3. FINANCEIRO (RELATÓRIOS DIÁRIOS) ---
elif menu == "Financeiro":
    st.header("💸 Financeiro")
    tab1, tab2 = st.tabs(["📋 Relatório Diário", "📉 Despesas"])
    
    with tab1:
        data_busca = st.date_input("Filtrar Data", date.today())
        df_dia = pd.read_sql_query(f"""
            SELECT v.id, c.nome as cliente, v.prod, v.qtd, v.total, v.pago_pix, v.pago_din, v.pendente 
            FROM vendas v JOIN clientes c ON v.cli_id = c.id 
            WHERE v.data = '{data_busca.isoformat()}'
        """, conn)
        
        if df_dia.empty:
            st.info("Nenhuma movimentação nesta data.")
        else:
            st.dataframe(df_dia, use_container_width=True, hide_index=True)
            st.write(f"**Total Vendido no Dia:** R$ {df_dia['total'].sum():.2f}")

    with tab2:
        with st.form("nova_despesa"):
            desc = st.text_input("Descrição da Despesa (Ex: Milho, Frete)")
            valor_d = st.number_input("Valor (R$)", min_value=0.0)
            if st.form_submit_button("Lançar Despesa"):
                conn.execute("INSERT INTO despesas (data, desc, valor) VALUES (?,?,?)", (date.today().isoformat(), desc, valor_d))
                conn.commit()
                st.rerun()
        st.table(pd.read_sql_query("SELECT data, desc, valor FROM despesas ORDER BY id DESC", conn))

# --- 4. ESTOQUE ---
elif menu == "Estoque":
    st.header("📦 Controle de Estoque")
    df_e = pd.read_sql_query("SELECT * FROM estoque", conn)
    
    with st.container(border=True):
        st.write("### Abastecer Estoque")
        c1, c2 = st.columns(2)
        p_add = c1.selectbox("Escolha o Produto", df_e['produto'].tolist())
        q_add = c2.number_input("Quantidade de Bandejas", min_value=1)
        if st.button("Confirmar Entrada"):
            conn.execute("UPDATE estoque SET qtd = qtd + ? WHERE produto = ?", (q_add, p_add))
            conn.commit()
            st.rerun()
    
    st.subheader("Saldo Atual")
    st.dataframe(df_e, use_container_width=True, hide_index=True)

# --- 5. CLIENTES (EDITAR E EXCLUIR) ---
elif menu == "Clientes":
    st.header("👤 Gestão de Clientes")
    
    with st.expander("➕ Adicionar Novo Cliente"):
        with st.form("cad_cli"):
            nome = st.text_input("Nome Comercial")
            tel = st.text_input("WhatsApp")
            end = st.text_input("Endereço")
            if st.form_submit_button("Cadastrar"):
                conn.execute("INSERT INTO clientes (nome, tel, endereco) VALUES (?,?,?)", (nome, tel, end))
                conn.commit()
                st.rerun()

    st.subheader("Lista de Clientes")
    df_c = pd.read_sql_query("SELECT * FROM clientes", conn)
    
    for idx, row in df_c.iterrows():
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            col1.write(f"**{row['nome']}**")
            col2.write(f"📞 {row['tel']}")
            
            if col3.button("✏️ Editar", key=f"edit_{row['id']}"):
                editar_cliente(row['id'], row['nome'], row['tel'], row['endereco'])
                
            if col4.button("🗑️ Excluir", key=f"del_{row['id']}"):
                conn.execute("DELETE FROM clientes WHERE id=?", (row['id'],))
                conn.commit()
                st.rerun()
