import streamlit as st
import sqlite3
import pandas as pd
from fpdf import FPDF
from datetime import datetime, date
import urllib.parse
import io  # ESSENCIAL PARA CORRIGIR O ERRO

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('gestao_ovos.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clientes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, endereco TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vendas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_id INTEGER, data TEXT, 
                  produto TEXT, valor_unit REAL, qtd INTEGER, total_nota REAL, 
                  pago_dinheiro REAL, pago_pix REAL, pendente REAL,
                  FOREIGN KEY(cliente_id) REFERENCES clientes(id))''')
    conn.commit()
    return conn

conn = init_db()

# --- CLASSE PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 16)
        self.cell(0, 10, 'RELATORIO DE ENTREGAS E COBRANCA', 0, 1, 'C')
        self.ln(5)

def gerar_pdf(df_vendas):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 8)
    
    # Cabeçalho da tabela
    pdf.set_fill_color(200, 200, 200)
    colunas = ["Data", "Cliente", "Total (R$)", "Pago (R$)", "Pendente", "Status"]
    larguras = [25, 55, 25, 25, 25, 35]
    for col, larg in zip(colunas, larguras):
        pdf.cell(larg, 10, col, 1, 0, 'C', True)
    pdf.ln()

    pdf.set_font("helvetica", "", 8)
    hoje = date.today()

    for _, row in df_vendas.iterrows():
        # Tratamento de dados nulos para evitar erros no PDF
        data_str = row['data'] if row['data'] else str(date.today())
        data_venda = datetime.strptime(data_str, '%Y-%m-%d').date()
        pago = (row['pago_dinheiro'] or 0.0) + (row['pago_pix'] or 0.0)
        total_nota = row['total_nota'] or 0.0
        pendente = row['pendente'] or 0.0
        nome_cliente = str(row['nome']) if row['nome'] else "Nao identificado"
        
        if pendente <= 0:
            pdf.set_fill_color(144, 238, 144) 
            status = "PAGO"
        elif data_venda < hoje:
            pdf.set_fill_color(255, 182, 193)
            status = "ATRASADO"
        else:
            pdf.set_fill_color(255, 255, 153)
            status = "PENDENTE"

        pdf.cell(25, 10, data_venda.strftime('%d/%m/%y'), 1)
        pdf.cell(55, 10, nome_cliente[:28], 1)
        pdf.cell(25, 10, f"{total_nota:.2f}", 1)
        pdf.cell(25, 10, f"{pago:.2f}", 1)
        pdf.cell(25, 10, f"{pendente:.2f}", 1)
        pdf.cell(35, 10, status, 1, 1, 'C', True)

    # CORREÇÃO AQUI: Converter bytearray da fpdf2 para bytes puro
    pdf_output = pdf.output()
    if isinstance(pdf_output, bytearray):
        return bytes(pdf_output)
    return pdf_output

# --- INTERFACE ---
st.set_page_config(page_title="EggGestão Pro", layout="wide", page_icon="🥚")

st.sidebar.title("🥚 EggGestão Pro")
aba = st.sidebar.radio("Navegar:", ["Início", "Clientes", "Lançar Venda", "Quitar Dívidas", "Rotas e Mapas", "Relatórios"])

if aba == "Início":
    st.title("🚀 Painel de Controle")
    col1, col2, col3 = st.columns(3)
    
    qtd_clientes = pd.read_sql_query("SELECT COUNT(*) FROM clientes", conn).values[0][0]
    vendas_hoje = pd.read_sql_query(f"SELECT COUNT(*) FROM vendas WHERE data='{date.today()}'", conn).values[0][0]
    pendente_total = pd.read_sql_query("SELECT SUM(pendente) FROM vendas", conn).values[0][0] or 0
    
    col1.metric("Total Clientes", qtd_clientes)
    col2.metric("Vendas Hoje", vendas_hoje)
    col3.metric("Total a Receber", f"R$ {pendente_total:.2f}")

elif aba == "Clientes":
    st.header("👤 Gestão de Clientes")
    with st.form("cad_cliente"):
        n = st.text_input("Nome do Cliente")
        e = st.text_input("Endereço (Rua, Nº, Bairro)")
        if st.form_submit_button("Cadastrar"):
            try:
                conn.execute("INSERT INTO clientes (nome, endereco) VALUES (?,?)", (n,e))
                conn.commit()
                st.success("Cadastrado!")
            except: st.error("Erro ou cliente já existe.")

elif aba == "Lançar Venda":
    st.header("📝 Nova Entrega")
    clientes_df = pd.read_sql_query("SELECT id, nome FROM clientes ORDER BY nome", conn)
    
    if not clientes_df.empty:
        with st.form("venda"):
            c_nome = st.selectbox("Cliente", clientes_df['nome'].tolist())
            col1, col2 = st.columns(2)
            
            # Ovo Branco na frente do Vermelho
            cor = col1.selectbox("Cor do Ovo", ["Branco", "Vermelho"])
            tipo = col1.selectbox("Tamanho", ["Médio", "Grande", "Extra", "Jumbo"])
            
            v_unit = col2.number_input("Preço Bandeja (R$)", min_value=0.0, value=15.0)
            qtd = col2.number_input("Quantidade", min_value=1, step=1)
            
            total_calc = v_unit * qtd
            st.info(f"**Total da Nota: R$ {total_calc:.2f}**")
            
            p_din = st.number_input("Pago Dinheiro", min_value=0.0)
            p_pix = st.number_input("Pago Pix", min_value=0.0)
            
            if st.form_submit_button("Finalizar Venda"):
                c_id = int(clientes_df[clientes_df['nome'] == c_nome]['id'].values[0])
                pend = total_calc - (p_din + p_pix)
                conn.execute('''INSERT INTO vendas (cliente_id, data, produto, valor_unit, qtd, total_nota, pago_dinheiro, pago_pix, pendente)
                                VALUES (?,?,?,?,?,?,?,?,?)''', (c_id, date.today(), f"{cor} {tipo}", v_unit, qtd, total_calc, p_din, p_pix, pend))
                conn.commit()
                st.success("Venda registrada!")
    else:
        st.warning("Cadastre um cliente antes.")

elif aba == "Quitar Dívidas":
    st.header("💰 Baixa de Pagamento")
    df_pendentes = pd.read_sql_query('''SELECT v.id, c.nome, v.pendente FROM vendas v 
                                      JOIN clientes c ON v.cliente_id = c.id WHERE v.pendente > 0''', conn)
    if not df_pendentes.empty:
        sel = st.selectbox("Dívida de:", df_pendentes.apply(lambda r: f"ID:{r['id']} - {r['nome']} (Falta R${r['pendente']:.2f})", axis=1))
        v_id = int(sel.split("ID:")[1].split(" -")[0])
        valor = st.number_input("Valor Pago Agora", min_value=0.0)
        meio = st.radio("Meio:", ["Pix", "Dinheiro"])
        if st.button("Confirmar Pagamento"):
            col = "pago_pix" if meio == "Pix" else "pago_dinheiro"
            conn.execute(f"UPDATE vendas SET {col} = {col} + ?, pendente = pendente - ? WHERE id = ?", (valor, valor, v_id))
            conn.commit()
            st.success("Atualizado!")
            st.rerun()
    else: st.info("Sem dívidas pendentes.")

elif aba == "Rotas e Mapas":
    st.header("🗺️ Planejador de Rota")
    clientes_rota = pd.read_sql_query("SELECT nome, endereco FROM clientes", conn)
    selecionados = st.multiselect("Clientes hoje:", clientes_rota['nome'].tolist())
    if selecionados:
        ends = clientes_rota[clientes_rota['nome'].isin(selecionados)]['endereco'].tolist()
        url = "https://www.google.com/maps/dir/" + "/".join([urllib.parse.quote(e) for e in ends])
        st.link_button("🚀 ABRIR GPS", url)

elif aba == "Relatórios":
    st.header("📊 Financeiro")
    df_vendas = pd.read_sql_query('''SELECT v.*, c.nome FROM vendas v JOIN clientes c ON v.cliente_id = c.id ORDER BY v.data DESC''', conn)
    
    if not df_vendas.empty:
        st.dataframe(df_vendas.drop(columns=['id', 'cliente_id']), use_container_width=True)
        
        # Gerar os dados binários do PDF
        try:
            pdf_data = gerar_pdf(df_vendas)
            
            st.download_button(
                label="📥 Baixar Relatório em PDF",
                data=pdf_data,
                file_name=f"Relatorio_{date.today()}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")
    else:
        st.info("Nenhuma venda registrada para gerar relatório.")
