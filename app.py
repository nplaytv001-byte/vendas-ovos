import streamlit as st
import sqlite3
import pandas as pd
from fpdf import FPDF
from datetime import datetime, date, timedelta
import urllib.parse

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('gestao_ovos.db', check_same_thread=False)
    c = conn.cursor()
    # Tabela de Clientes
    c.execute('''CREATE TABLE IF NOT EXISTS clientes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, endereco TEXT)''')
    # Tabela de Vendas
    c.execute('''CREATE TABLE IF NOT EXISTS vendas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_id INTEGER, data TEXT, 
                  produto TEXT, valor_unit REAL, qtd INTEGER, total_nota REAL, 
                  pago_dinheiro REAL, pago_pix REAL, pendente REAL,
                  FOREIGN KEY(cliente_id) REFERENCES clientes(id))''')
    conn.commit()
    return conn

conn = init_db()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="EggGestão Pro", layout="wide", page_icon="🥚")

# --- FUNÇÕES DE PDF PERSONALIZADO ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'RELATÓRIO DE ENTREGAS E COBRANÇA', 0, 1, 'C')
        self.ln(5)

def gerar_pdf(df_vendas):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 8)
    
    # Cabeçalho da tabela
    pdf.set_fill_color(200, 200, 200)
    colunas = ["Data", "Cliente", "Total (R$)", "Pago (R$)", "Pendente", "Status"]
    larguras = [25, 50, 30, 30, 30, 25]
    for col, larg in zip(colunas, larguras):
        pdf.cell(larg, 10, col, 1, 0, 'C', True)
    pdf.ln()

    pdf.set_font("Arial", "", 8)
    hoje = date.today()

    for _, row in df_vendas.iterrows():
        data_venda = datetime.strptime(row['data'], '%Y-%m-%d').date()
        pago = row['pago_dinheiro'] + row['pago_pix']
        
        # Lógica de Cores e Status
        if row['pendente'] <= 0:
            pdf.set_fill_color(144, 238, 144) # Verde (Finalizado)
            status = "PAGO"
        elif data_venda < hoje:
            pdf.set_fill_color(255, 182, 193) # Vermelho (Atrasado)
            status = "ATRASADO"
        else:
            pdf.set_fill_color(255, 255, 153) # Amarelo (Pendente Hoje)
            status = "PENDENTE"

        pdf.cell(25, 10, data_venda.strftime('%d/%m/%y'), 1)
        pdf.cell(50, 10, row['nome'][:25], 1)
        pdf.cell(30, 10, f"{row['total_nota']:.2f}", 1)
        pdf.cell(30, 10, f"{pago:.2f}", 1)
        pdf.cell(30, 10, f"{row['pendente']:.2f}", 1)
        pdf.cell(25, 10, status, 1, 1, 'C', True)

    return pdf.output(dest='S')

# --- INTERFACE ---
st.sidebar.title("🥚 EggGestão Pro")
aba = st.sidebar.radio("Navegar:", ["Início", "Clientes", "Lançar Venda", "Rotas e Mapas", "Relatórios Financeiros"])

# --- ABA INÍCIO ---
if aba == "Início":
    st.title("Bem-vindo ao Painel de Controle")
    st.write("Gerencie suas vendas, clientes e rotas de entrega de forma profissional.")
    
    # Resumo Rápido
    col1, col2, col3 = st.columns(3)
    c = conn.cursor()
    col1.metric("Clientes", pd.read_sql_query("SELECT COUNT(*) FROM clientes", conn).values[0][0])
    col2.metric("Vendas Hoje", pd.read_sql_query(f"SELECT COUNT(*) FROM vendas WHERE data='{date.today()}'", conn).values[0][0])
    pendente_total = pd.read_sql_query("SELECT SUM(pendente) FROM vendas", conn).values[0][0] or 0
    col3.metric("Total a Receber", f"R$ {pendente_total:.2f}")

# --- ABA CLIENTES ---
elif aba == "Clientes":
    st.header("👤 Gestão de Clientes")
    tab1, tab2 = st.tabs(["Cadastro Individual", "Importação em Lote (Excel)"])
    
    with tab1:
        with st.form("cad_un") :
            n = st.text_input("Nome do Cliente")
            e = st.text_input("Endereço (Rua, Número, Bairro, Cidade)")
            if st.form_submit_button("Cadastrar"):
                try:
                    conn.execute("INSERT INTO clientes (nome, endereco) VALUES (?,?)", (n,e))
                    conn.commit()
                    st.success("Cliente salvo!")
                except: st.error("Erro: Cliente já existe.")

    with tab2:
        file = st.file_uploader("Suba um Excel/CSV com colunas 'Nome' e 'Endereco'", type=['xlsx', 'csv'])
        if file and st.button("Importar Todos"):
            df_imp = pd.read_excel(file) if file.name.endswith('xlsx') else pd.read_csv(file)
            for _, r in df_imp.iterrows():
                try: conn.execute("INSERT INTO clientes (nome, endereco) VALUES (?,?)", (r['Nome'], r['Endereco']))
                except: pass
            conn.commit()
            st.success("Importação concluída!")

# --- ABA LANÇAR VENDA ---
elif aba == "Lançar Venda":
    st.header("📝 Nova Entrega")
    clientes = pd.read_sql_query("SELECT id, nome FROM clientes ORDER BY nome", conn)
    
    with st.form("venda"):
        c_nome = st.selectbox("Cliente", clientes['nome'].tolist())
        col1, col2 = st.columns(2)
        tipo = col1.selectbox("Tamanho", ["Pequeno", "Médio", "Grande", "Extra", "Jumbo"])
        cor = col1.selectbox("Cor", ["Vermelho", "Branco"])
        v_unit = col2.number_input("Preço Bandeja", min_value=0.0)
        qtd = col2.number_input("Quantidade", min_value=1, step=1)
        
        st.write("---")
        p_din = st.number_input("Pago em Dinheiro", min_value=0.0)
        p_pix = st.number_input("Pago em Pix", min_value=0.0)
        
        if st.form_submit_button("Finalizar Venda"):
            c_id = int(clientes[clientes['nome'] == c_nome]['id'].values[0])
            total = v_unit * qtd
            pend = total - (p_din + p_pix)
            conn.execute('''INSERT INTO vendas (cliente_id, data, produto, valor_unit, qtd, total_nota, pago_dinheiro, pago_pix, pendente)
                            VALUES (?,?,?,?,?,?,?,?,?)''', (c_id, date.today(), f"{tipo} {cor}", v_unit, qtd, total, p_din, p_pix, pend))
            conn.commit()
            st.success("Venda registrada!")

# --- ABA ROTAS ---
elif aba == "Rotas e Mapas":
    st.header("🗺️ Planejador de Rota (Google Maps)")
    clientes_rota = pd.read_sql_query("SELECT nome, endereco FROM clientes", conn)
    selecionados = st.multiselect("Selecione os clientes para visitar hoje:", clientes_rota['nome'].tolist())
    
    if selecionados:
        df_f = clientes_rota[clientes_rota['nome'].isin(selecionados)]
        base_url = "https://www.google.com/maps/dir/"
        rota_str = "/".join([urllib.parse.quote(a) for a in df_f['endereco'].tolist()])
        
        st.link_button("🚀 ABRIR GPS COM ROTA OTIMIZADA", base_url + rota_str)
        st.write("Lista na ordem:")
        for i, r in enumerate(selecionados, 1): st.write(f"{i}º: {r}")

# --- ABA RELATÓRIOS ---
elif aba == "Relatórios Financeiros":
    st.header("📊 Financeiro e PDF")
    df_vendas = pd.read_sql_query('''SELECT v.*, c.nome FROM vendas v JOIN clientes c ON v.cliente_id = c.id ORDER BY v.data DESC''', conn)
    
    if not df_vendas.empty:
        st.dataframe(df_vendas.drop(columns=['id', 'cliente_id']))
        
        if st.button("Gerar Relatório Colorido (PDF)"):
            pdf_out = gerar_pdf(df_vendas)
            st.download_button("📥 Baixar PDF", pdf_out, "Relatorio_Vendas.pdf", "application/pdf")
    else:
        st.info("Nenhuma venda registrada.")