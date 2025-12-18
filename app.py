import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from fpdf import FPDF
from datetime import datetime, date
import urllib.parse
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from streamlit_js_eval import streamlit_js_eval
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="EggGestão Pro v3.0", layout="wide", page_icon="🥚")

# --- ESTILO CSS ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .stMetric { background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('ovos_master.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clientes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, 
                  endereco TEXT, telefone TEXT, lat REAL, lon REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vendas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_id INTEGER, data TEXT, 
                  produto TEXT, valor_unit REAL, qtd INTEGER, total_nota REAL, 
                  pago REAL, pendente REAL, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS estoque (produto TEXT PRIMARY KEY, quantidade INTEGER)''')
    
    # Inicializar estoque se vazio
    c.execute("SELECT COUNT(*) FROM estoque")
    if c.fetchone()[0] == 0:
        prods = [("Branco Médio", 0), ("Branco Grande", 0), ("Branco Extra", 0), ("Branco Jumbo", 0),
                 ("Vermelho Médio", 0), ("Vermelho Grande", 0), ("Vermelho Extra", 0), ("Vermelho Jumbo", 0)]
        c.executemany("INSERT INTO estoque VALUES (?,?)", prods)
    conn.commit()
    return conn

conn = init_db()
geolocator = Nominatim(user_agent="egg_gestao_pro_v3")

# --- FUNÇÕES AUXILIARES ---
def normalizar(t):
    import unicodedata
    return "".join(c for c in unicodedata.normalize('NFD', str(t)) if unicodedata.category(c) != 'Mn')

def buscar_coords(end):
    try:
        loc = geolocator.geocode(end, timeout=10)
        return (loc.latitude, loc.longitude) if loc else (None, None)
    except: return None, None

# --- CLASSE PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'RELATORIO DE ENTREGAS - EGGGESTAO PRO', 0, 1, 'C')
        self.ln(5)

# --- NAVEGAÇÃO SIDEBAR ---
st.sidebar.title("🥚 EggGestão Pro")
st.sidebar.markdown("---")
menu = st.sidebar.selectbox("Ir para:", ["📊 Dashboard", "👤 Clientes", "📦 Estoque", "📝 Lançar Venda", "🗺️ Rota Inteligente", "💰 Financeiro"])

# ================= DASHBOARD =================
if menu == "📊 Dashboard":
    st.title("Painel Geral")
    
    # Métricas
    c1, c2, c3 = st.columns(3)
    total_pendente = pd.read_sql_query("SELECT SUM(pendente) FROM vendas", conn).iloc[0,0] or 0
    total_mes = pd.read_sql_query("SELECT SUM(total_nota) FROM vendas WHERE strftime('%m', data) = strftime('%m', 'now')", conn).iloc[0,0] or 0
    cli_count = pd.read_sql_query("SELECT COUNT(*) FROM clientes", conn).iloc[0,0]
    
    c1.metric("A Receber (Dívidas)", f"R$ {total_pendente:.2f}")
    c2.metric("Vendas do Mês", f"R$ {total_mes:.2f}")
    c3.metric("Clientes Ativos", cli_count)

    st.markdown("---")
    col_l, col_r = st.columns(2)
    
    # Gráfico Estoque
    df_est = pd.read_sql_query("SELECT * FROM estoque", conn)
    fig_est = px.bar(df_est, x='produto', y='quantidade', title="Estoque Atual", color='quantidade', color_continuous_scale='YlOrBr')
    col_l.plotly_chart(fig_est, use_container_width=True)
    
    # Gráfico Vendas
    df_vd = pd.read_sql_query("SELECT data, SUM(total_nota) as total FROM vendas GROUP BY data LIMIT 10", conn)
    fig_vd = px.line(df_vd, x='data', y='total', title="Tendência de Vendas", markers=True)
    col_r.plotly_chart(fig_vd, use_container_width=True)

# ================= CLIENTES =================
elif menu == "👤 Clientes":
    st.title("Gestão de Clientes")
    t1, t2 = st.tabs(["Cadastrar", "Lista de Clientes"])
    
    with t1:
        with st.form("cli_form"):
            nome = st.text_input("Nome do Cliente / Estabelecimento")
            end = st.text_input("Endereço Completo (Rua, Número, Bairro, Cidade)")
            tel = st.text_input("WhatsApp (ex: 11999999999)")
            if st.form_submit_button("Salvar Cliente"):
                lat, lon = buscar_coords(end)
                try:
                    conn.execute("INSERT INTO clientes (nome, endereco, telefone, lat, lon) VALUES (?,?,?,?,?)", (nome, end, tel, lat, lon))
                    conn.commit()
                    st.success("✅ Cliente cadastrado com sucesso!")
                except: st.error("Erro: Cliente já existe.")
                
    with t2:
        df_cli = pd.read_sql_query("SELECT * FROM clientes", conn)
        for i, r in df_cli.iterrows():
            with st.expander(f"{r['nome']} - {r['endereco']}"):
                c1, c2 = st.columns(2)
                if c1.button("Excluir", key=f"delcli_{r['id']}"):
                    conn.execute("DELETE FROM clientes WHERE id=?", (r['id'],))
                    conn.commit()
                    st.rerun()
                c2.write(f"📍 Lat: {r['lat']} | Lon: {r['lon']}")

# ================= ESTOQUE =================
elif menu == "📦 Estoque":
    st.title("Controle de Estoque")
    df_est = pd.read_sql_query("SELECT * FROM estoque", conn)
    
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.subheader("Repor Mercadoria")
        p_sel = st.selectbox("Produto", df_est['produto'].tolist())
        q_add = st.number_input("Qtd para Adicionar", min_value=1)
        if st.button("Confirmar Entrada"):
            conn.execute("UPDATE estoque SET quantidade = quantidade + ? WHERE produto = ?", (q_add, p_sel))
            conn.commit()
            st.success("Estoque atualizado!")
            st.rerun()
    with col_b:
        st.dataframe(df_est, use_container_width=True)

# ================= VENDAS =================
elif menu == "📝 Lançar Venda":
    st.title("Nova Venda")
    df_cli = pd.read_sql_query("SELECT id, nome, telefone FROM clientes", conn)
    
    if df_cli.empty:
        st.warning("Cadastre clientes primeiro!")
    else:
        with st.form("venda_form"):
            cliente_nome = st.selectbox("Selecione o Cliente", df_cli['nome'].tolist())
            c1, c2, c3 = st.columns(3)
            cor = c1.selectbox("Cor", ["Branco", "Vermelho"])
            tam = c2.selectbox("Tamanho", ["Médio", "Grande", "Extra", "Jumbo"])
            qtd = c3.number_input("Qtd de Bandejas", min_value=1)
            
            val = st.number_input("Preço Unitário (R$)", min_value=0.0, value=15.0)
            pago = st.number_input("Valor Pago Agora (R$)", min_value=0.0)
            
            if st.form_submit_button("Finalizar Venda"):
                prod = f"{cor} {tam}"
                est_atual = conn.execute("SELECT quantidade FROM estoque WHERE produto=?", (prod,)).fetchone()[0]
                
                if est_atual < qtd:
                    st.error(f"Estoque insuficiente ({est_atual} disp.)")
                else:
                    c_id = int(df_cli[df_cli['nome'] == cliente_nome]['id'].values[0])
                    total = val * qtd
                    pend = total - pago
                    status = "PAGO" if pend <= 0 else "PENDENTE"
                    
                    conn.execute("INSERT INTO vendas (cliente_id, data, produto, valor_unit, qtd, total_nota, pago, pendente, status) VALUES (?,?,?,?,?,?,?,?,?)",
                                (c_id, str(date.today()), prod, val, qtd, total, pago, pend, status))
                    conn.execute("UPDATE estoque SET quantidade = quantidade - ? WHERE produto = ?", (qtd, prod))
                    conn.commit()
                    st.success("Venda realizada!")
                    st.balloons()

# ================= ROTA INTELIGENTE =================
elif menu == "🗺️ Rota Inteligente":
    st.title("Otimizador de Entregas")
    
    st.write("📍 Obtendo sua localização...")
    loc = streamlit_js_eval(data_key='pos', function_name='getCurrentPosition', component_ready=True)
    
    if loc:
        lat_carro = loc['coords']['latitude']
        lon_carro = loc['coords']['longitude']
        st.success("Localização do GPS encontrada!")
        
        df_rota = pd.read_sql_query("SELECT nome, endereco, lat, lon FROM clientes WHERE lat IS NOT NULL", conn)
        selecionados = st.multiselect("Selecione os clientes para entrega hoje:", df_rota['nome'].tolist())
        
        if selecionados:
            pontos = df_rota[df_rota['nome'].isin(selecionados)].to_dict('records')
            rota_final = []
            atual = (lat_carro, lon_carro)
            
            while pontos:
                proximo = min(pontos, key=lambda p: geodesic(atual, (p['lat'], p['lon'])).km)
                rota_final.append(proximo)
                atual = (proximo['lat'], proximo['lon'])
                pontos.remove(proximo)
            
            st.subheader("Caminho Otimizado:")
            for i, p in enumerate(rota_final):
                st.write(f"{i+1}º: **{p['nome']}** - {p['endereco']}")
            
            # Gerar link Google Maps
            link = "https://www.google.com/maps/dir/" + f"{lat_carro},{lon_carro}/" + "/".join([urllib.parse.quote(p['endereco']) for p in rota_final])
            st.link_button("🚀 INICIAR GPS (GOOGLE MAPS)", link)
            st.map(pd.DataFrame(rota_final))
    else:
        st.info("Aguardando permissão de GPS do navegador...")

# ================= FINANCEIRO =================
elif menu == "💰 Financeiro":
    st.title("Gestão Financeira")
    df_fin = pd.read_sql_query('''SELECT v.id, v.data, c.nome, v.produto, v.total_nota, v.pago, v.pendente, v.status 
                                  FROM vendas v JOIN clientes c ON v.cliente_id = c.id ORDER BY v.id DESC''', conn)
    
    st.dataframe(df_fin, use_container_width=True)
    
    # Baixar PDF
    if not df_fin.empty:
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", "", 8)
        for _, row in df_fin.iterrows():
            txt = f"{row['data']} | {row['nome']} | {row['produto']} | Total: {row['total_nota']} | Pend: {row['pendente']}"
            pdf.cell(0, 8, normalizar(txt), 1, 1)
        
        pdf_out = pdf.output(dest='S').encode('latin-1')
        st.download_button("📥 Baixar PDF de Vendas", pdf_out, "financeiro.pdf", "application/pdf")

    st.markdown("---")
    st.subheader("Quitar Dívida")
    dividas = df_fin[df_fin['pendente'] > 0]
    if not dividas.empty:
        sel = st.selectbox("Escolha a conta:", dividas.apply(lambda r: f"ID:{r['id']} | {r['nome']} | R${r['pendente']}", axis=1))
        v_id = int(sel.split(" |")[0].split(":")[1])
        v_pago = st.number_input("Valor Recebido", min_value=0.0)
        if st.button("Confirmar Recebimento"):
            conn.execute("UPDATE vendas SET pago = pago + ?, pendente = pendente - ? WHERE id = ?", (v_pago, v_pago, v_id))
            conn.execute("UPDATE vendas SET status = 'PAGO' WHERE pendente <= 0 AND id = ?", (v_id,))
            conn.commit()
            st.success("Dívida atualizada!")
            st.rerun()
