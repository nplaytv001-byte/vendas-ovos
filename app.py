from flask import Flask, render_template_string, request, redirect, url_for, flash, Response, session
import sqlite3
from datetime import datetime, timedelta
import csv
import io
from werkzeug.security import generate_password_hash, check_password_hash

# --- INICIALIZAÇÃO DO SISTEMA ---
app = Flask(__name__)
app.secret_key = "eggpro_v10_titanium_ultra_key"

# --- BANCO DE DADOS ---
def get_db():
    conn = sqlite3.connect('eggpro_v10.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        username TEXT UNIQUE, password TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS clientes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        nome TEXT, tel TEXT, cep TEXT, rua TEXT, bairro TEXT, cidade TEXT, estado TEXT, numero TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS estoque (
                        produto TEXT PRIMARY KEY, qtd INTEGER, preco_custo REAL, preco_sugerido REAL)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS vendas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        cli_id INTEGER, cli_nome TEXT, data TEXT, timestamp DATETIME,
                        prod TEXT, qtd INTEGER, valor_unit REAL, total REAL, 
                        pago_pix REAL, pago_dinheiro REAL, pendente REAL)''')
        
        hash_pw = generate_password_hash('123')
        conn.execute("INSERT OR IGNORE INTO usuarios (username, password) VALUES (?, ?)", ('admin', hash_pw))
        
        prods = [("Branco Extra", 100, 12.0, 16.0), ("Vermelho Extra", 100, 14.0, 19.0), ("Jumbo", 50, 18.0, 24.0)]
        for p in prods:
            conn.execute("INSERT OR IGNORE INTO estoque (produto, qtd, preco_custo, preco_sugerido) VALUES (?, ?, ?, ?)", p)
        conn.commit()

init_db()

# --- TEMPLATE BASE ---
BASE_HTML = """
<!DOCTYPE html>
<html lang="pt-br" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EggPro Titanium v10.2</title>
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4.4.19/dist/full.min.css" rel="stylesheet" />
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
    <style>.glass-card { background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); }</style>
</head>
<body class="bg-base-300 min-h-screen font-sans">
    {% if session.get('user') %}
    <div class="drawer lg:drawer-open">
        <input id="nav-drawer" type="checkbox" class="drawer-toggle" />
        <div class="drawer-content flex flex-col">
            <div class="navbar bg-base-100 lg:hidden shadow-xl border-b border-white/5">
                <label for="nav-drawer" class="btn btn-square btn-ghost"><i data-lucide="menu"></i></label>
                <div class="flex-1 px-2 font-black text-primary italic">EGGPRO v10</div>
            </div>
            <main class="p-4 md:p-10">
                {% with messages = get_flashed_messages(with_categories=true) %}
                  {% if messages %}
                    {% for category, msg in messages %}
                        <div class="alert alert-{{ category }} mb-6 shadow-lg"><span>{{ msg }}</span></div>
                    {% endfor %}
                  {% endif %}
                {% endwith %}
                {{ content | safe }}
            </main>
        </div> 
        <div class="drawer-side z-50">
            <label for="nav-drawer" class="drawer-overlay"></label> 
            <ul class="menu p-6 w-80 min-h-full bg-base-200 text-base-content gap-2 border-r border-white/5">
                <li class="mb-8 flex flex-row items-center gap-4 px-2">
                    <div class="bg-primary p-3 rounded-2xl text-white shadow-lg"><i data-lucide="egg"></i></div>
                    <span class="text-2xl font-black italic">TITANIUM <span class="text-primary">v10</span></span>
                </li>
                <li><a href="/"><i data-lucide="layout-dashboard"></i> Dashboard</a></li>
                <li><a href="/vender" class="bg-primary/10 text-primary font-bold"><i data-lucide="shopping-cart"></i> Nova Venda</a></li>
                <li><a href="/vendas_log"><i data-lucide="history"></i> Histórico</a></li>
                <li><a href="/financeiro"><i data-lucide="dollar-sign"></i> Financeiro</a></li>
                <li><a href="/estoque"><i data-lucide="package"></i> Estoque</a></li>
                <li><a href="/clientes"><i data-lucide="users"></i> Clientes</a></li>
                <div class="divider opacity-20">SISTEMA</div>
                <li><a href="/usuarios"><i data-lucide="lock"></i> Operadores</a></li>
                <li><a href="/logout" class="text-error"><i data-lucide="log-out"></i> Sair</a></li>
            </ul>
        </div>
    </div>
    {% else %}
        {{ content | safe }}
    {% endif %}
    <script>lucide.createIcons();</script>
</body>
</html>
"""

# --- DASHBOARD ---
@app.route('/')
def dashboard():
    if not session.get('user'): return redirect(url_for('login'))
    hoje = datetime.now().strftime("%d/%m/%Y")
    with get_db() as conn:
        resumo = conn.execute("SELECT SUM(total), SUM(pago_pix + pago_dinheiro), SUM(pendente) FROM vendas WHERE data = ?", (hoje,)).fetchone()
        grafico = conn.execute("SELECT data, SUM(total) as t FROM vendas GROUP BY data ORDER BY timestamp DESC LIMIT 7").fetchall()
    
    labels = [r['data'] for r in reversed(grafico)]
    valores = [r['t'] for r in reversed(grafico)]

    page_content = render_template_string("""
    <h1 class="text-3xl font-black italic mb-8">Painel Principal</h1>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <div class="stats glass-card shadow">
            <div class="stat"><div class="stat-title text-xs font-bold uppercase">Vendido Hoje</div><div class="stat-value text-primary">R$ {{ "%.2f"|format(resumo[0] or 0) }}</div></div>
        </div>
        <div class="stats glass-card shadow">
            <div class="stat"><div class="stat-title text-xs font-bold uppercase">Recebido Hoje</div><div class="stat-value text-success">R$ {{ "%.2f"|format(resumo[1] or 0) }}</div></div>
        </div>
        <div class="stats glass-card shadow border-l-4 border-error">
            <div class="stat"><div class="stat-title text-xs font-bold uppercase">Em Aberto</div><div class="stat-value text-error">R$ {{ "%.2f"|format(resumo[2] or 0) }}</div></div>
        </div>
    </div>
    <div class="card bg-base-100 p-6 shadow-xl"><div id="chart"></div></div>
    <script>
        new ApexCharts(document.querySelector("#chart"), {
            series: [{ name: 'Vendas R$', data: {{ valores | tojson }} }],
            chart: { type: 'area', height: 350, theme: 'dark', toolbar: {show:false} },
            colors: ['#641ae6'],
            stroke: { curve: 'smooth' },
            xaxis: { categories: {{ labels | tojson }} }
        }).render();
    </script>
    """, resumo=resumo, valores=valores, labels=labels)
    return render_template_string(BASE_HTML, content=page_content)

# --- HISTÓRICO E RELATÓRIOS (NOVO) ---
@app.route('/vendas_log')
def vendas_log():
    if not session.get('user'): return redirect(url_for('login'))
    with get_db() as conn:
        vendas = conn.execute("SELECT * FROM vendas ORDER BY id DESC").fetchall()
    
    page_content = render_template_string("""
    <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <h1 class="text-3xl font-black italic">Histórico de Vendas</h1>
        
        <div class="dropdown dropdown-end">
            <label tabindex="0" class="btn btn-neutral btn-sm shadow-lg border-primary/30">
                <i data-lucide="download"></i> Baixar Relatório
            </label>
            <ul tabindex="0" class="dropdown-content z-[1] menu p-2 shadow-2xl bg-base-200 rounded-box w-52 border border-white/10">
                <li><a href="/relatorio/diario"><i data-lucide="calendar"></i> Hoje (Diário)</a></li>
                <li><a href="/relatorio/semanal"><i data-lucide="calendar-days"></i> Últimos 7 dias</a></li>
                <li><a href="/relatorio/mensal"><i data-lucide="calendar-range"></i> Últimos 30 dias</a></li>
            </ul>
        </div>
    </div>

    <div class="card bg-base-100 overflow-x-auto shadow-xl">
        <table class="table table-zebra">
            <thead><tr><th>ID</th><th>Cliente</th><th>Data</th><th>Produto</th><th>Total</th><th>Status</th><th>Ação</th></tr></thead>
            <tbody>
                {% for v in vendas %}
                <tr>
                    <td>#{{ v['id'] }}</td>
                    <td class="font-bold">{{ v['cli_nome'] }}</td>
                    <td class="text-xs">{{ v['data'] }}</td>
                    <td>{{ v['prod'] }} ({{ v['qtd'] }}x)</td>
                    <td class="font-bold text-primary">R$ {{ "%.2f"|format(v['total']) }}</td>
                    <td>{{ "Pago" if v['pendente'] <= 0 else "Pendente" }}</td>
                    <td><a href="/vendas/excluir/{{ v['id'] }}" class="btn btn-ghost btn-xs text-error" onclick="return confirm('Estornar?')">Estornar</a></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    """, vendas=vendas)
    return render_template_string(BASE_HTML, content=page_content)

@app.route('/relatorio/<periodo>')
def gerar_relatorio(periodo):
    if not session.get('user'): return redirect(url_for('login'))
    agora = datetime.now()
    query = "SELECT * FROM vendas"
    params = []

    if periodo == 'diario':
        query += " WHERE data = ?"; params.append(agora.strftime("%d/%m/%Y"))
    elif periodo == 'semanal':
        query += " WHERE timestamp >= ?"; params.append((agora - timedelta(days=7)))
    elif periodo == 'mensal':
        query += " WHERE timestamp >= ?"; params.append((agora - timedelta(days=30)))

    with get_db() as conn:
        vendas = conn.execute(query, params).fetchall()

    output = io.StringIO()
    output.write('\ufeff') # Garante acentos no Excel
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['ID', 'Cliente', 'Data', 'Produto', 'Qtd', 'Total', 'Pendente'])
    for v in vendas:
        writer.writerow([v['id'], v['cli_nome'], v['data'], v['prod'], v['qtd'], v['total'], v['pendente']])

    output.seek(0)
    return Response(output.read(), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename=relatorio_{periodo}.csv"})

# --- CLIENTES ---
@app.route('/clientes', methods=['GET', 'POST'])
def clientes():
    if not session.get('user'): return redirect(url_for('login'))
    if request.method == 'POST':
        f = request.form
        with get_db() as conn:
            conn.execute("INSERT INTO clientes (nome, tel, cep, rua, bairro, cidade, estado, numero) VALUES (?,?,?,?,?,?,?,?)", 
                        (f['nome'], f['tel'], f['cep'], f['rua'], f['bairro'], f['cidade'], f['estado'], f['numero']))
            conn.commit()
        flash("Cliente cadastrado!", "success")

    with get_db() as conn:
        clis = conn.execute("SELECT * FROM clientes ORDER BY nome").fetchall()
    
    page_content = render_template_string(r"""
    <div class="flex justify-between items-center mb-8">
        <h1 class="text-3xl font-black italic">Clientes</h1>
        <button class="btn btn-primary" onclick="m_c.showModal()">+ Novo Cliente</button>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {% for c in clis %}
        <div class="card bg-base-100 shadow-xl border border-white/5 group">
            <div class="card-body p-5">
                <div class="flex justify-between">
                    <h2 class="text-xl font-bold text-primary">{{ c['nome'] }}</h2>
                    <div class="flex gap-1">
                        <a href="/clientes/editar/{{ c['id'] }}" class="btn btn-ghost btn-xs text-info"><i data-lucide="pencil"></i></a>
                        <a href="/clientes/excluir/{{ c['id'] }}" class="btn btn-ghost btn-xs text-error" onclick="return confirm('Excluir?')"><i data-lucide="trash-2"></i></a>
                    </div>
                </div>
                <p class="text-xs opacity-60">{{ c['rua'] }}, {{ c['numero'] }}</p>
                <div class="badge badge-outline mt-2">{{ c['tel'] }}</div>
            </div>
        </div>
        {% endfor %}
    </div>
    <dialog id="m_c" class="modal">
        <div class="modal-box w-11/12 max-w-2xl">
            <h3 class="font-black text-2xl mb-6">Cadastrar Cliente</h3>
            <form method="POST" class="grid grid-cols-2 gap-4">
                <input name="nome" placeholder="Nome" class="input input-bordered col-span-2" required />
                <input name="tel" placeholder="WhatsApp" class="input input-bordered" />
                <input name="cep" id="cep" placeholder="CEP" class="input input-bordered" onblur="buscarCEP('cep', 'rua', 'bairro', 'cidade', 'estado')" />
                <input name="rua" id="rua" placeholder="Rua" class="input input-bordered col-span-2" />
                <input name="numero" placeholder="Nº" class="input input-bordered" required />
                <input name="bairro" id="bairro" placeholder="Bairro" class="input input-bordered" />
                <input name="cidade" id="cidade" placeholder="Cidade" class="input input-bordered" />
                <input name="estado" id="estado" placeholder="UF" class="input input-bordered" />
                <button class="btn btn-primary col-span-2 mt-4">SALVAR</button>
            </form>
        </div>
        <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>
    <script>
        function buscarCEP(idCep, idRua, idBairro, idCidade, idUf) {
            let cep = document.getElementById(idCep).value.replace(/\D/g, '');
            if (cep.length != 8) return;
            fetch(`https://viacep.com.br/ws/${cep}/json/`)
                .then(r => r.json()).then(d => {
                    if (!d.erro) {
                        document.getElementById(idRua).value = d.logradouro;
                        document.getElementById(idBairro).value = d.bairro;
                        document.getElementById(idCidade).value = d.localidade;
                        document.getElementById(idUf).value = d.uf;
                    }
                });
        }
    </script>
    """, clis=clis)
    return render_template_string(BASE_HTML, content=page_content)

@app.route('/clientes/editar/<int:id>', methods=['GET', 'POST'])
def clientes_editar(id):
    if not session.get('user'): return redirect(url_for('login'))
    with get_db() as conn:
        if request.method == 'POST':
            f = request.form
            conn.execute("UPDATE clientes SET nome=?, tel=?, cep=?, rua=?, bairro=?, cidade=?, estado=?, numero=? WHERE id=?", 
                        (f['nome'], f['tel'], f['cep'], f['rua'], f['bairro'], f['cidade'], f['estado'], f['numero'], id))
            conn.commit()
            flash("Cliente atualizado!", "info")
            return redirect(url_for('clientes'))
        c = conn.execute("SELECT * FROM clientes WHERE id=?", (id,)).fetchone()
    
    page_content = render_template_string(r"""
    <div class="max-w-2xl mx-auto card bg-base-100 shadow-2xl p-8 border-t-8 border-info">
        <h2 class="text-3xl font-black italic mb-8">Editar Cliente</h2>
        <form method="POST" class="grid grid-cols-2 gap-4">
            <input name="nome" value="{{ c['nome'] }}" class="input input-bordered col-span-2" required />
            <input name="tel" value="{{ c['tel'] }}" class="input input-bordered" />
            <input name="cep" id="e_cep" value="{{ c['cep'] }}" class="input input-bordered" onblur="buscarCEP('e_cep', 'e_rua', 'e_bairro', 'e_cidade', 'e_estado')" />
            <input name="rua" id="e_rua" value="{{ c['rua'] }}" class="input input-bordered col-span-2" />
            <input name="numero" value="{{ c['numero'] }}" class="input input-bordered" required />
            <input name="bairro" id="e_bairro" value="{{ c['bairro'] }}" class="input input-bordered" />
            <input name="cidade" id="e_cidade" value="{{ c['cidade'] }}" class="input input-bordered" />
            <input name="estado" id="e_estado" value="{{ c['estado'] }}" class="input input-bordered" />
            <button class="btn btn-info col-span-2 mt-4 text-white">ATUALIZAR</button>
            <a href="/clientes" class="btn btn-ghost col-span-2">Cancelar</a>
        </form>
    </div>
    <script>
        function buscarCEP(idCep, idRua, idBairro, idCidade, idUf) {
            let cep = document.getElementById(idCep).value.replace(/\D/g, '');
            if (cep.length != 8) return;
            fetch(`https://viacep.com.br/ws/${cep}/json/`).then(r => r.json()).then(d => {
                if (!d.erro) {
                    document.getElementById(idRua).value = d.logradouro;
                    document.getElementById(idBairro).value = d.bairro;
                    document.getElementById(idCidade).value = d.localidade;
                    document.getElementById(idUf).value = d.uf;
                }
            });
        }
    </script>
    """, c=c)
    return render_template_string(BASE_HTML, content=page_content)

@app.route('/clientes/excluir/<int:id>')
def clientes_excluir(id):
    with get_db() as conn:
        conn.execute("DELETE FROM clientes WHERE id=?", (id,))
        conn.commit()
    flash("Cliente removido.", "warning")
    return redirect(url_for('clientes'))

# --- VENDA ---
@app.route('/vender', methods=['GET', 'POST'])
def vender():
    if not session.get('user'): return redirect(url_for('login'))
    with get_db() as conn:
        if request.method == 'POST':
            f = request.form
            total = int(f['qtd']) * float(f['valor_unit'])
            pend = total - (float(f['pago_pix'] or 0) + float(f['pago_dinheiro'] or 0))
            cli = conn.execute("SELECT nome FROM clientes WHERE id=?", (f['cliente_id'],)).fetchone()
            conn.execute("INSERT INTO vendas (cli_id, cli_nome, data, timestamp, prod, qtd, valor_unit, total, pago_pix, pago_dinheiro, pendente) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (f['cliente_id'], cli['nome'], datetime.now().strftime("%d/%m/%Y"), datetime.now(), f['produto'], f['qtd'], f['valor_unit'], total, f['pago_pix'], f['pago_dinheiro'], pend))
            conn.execute("UPDATE estoque SET qtd = qtd - ? WHERE produto = ?", (f['qtd'], f['produto']))
            conn.commit()
            return redirect(url_for('vendas_log'))
        clis = conn.execute("SELECT * FROM clientes ORDER BY nome").fetchall()
        prods = conn.execute("SELECT * FROM estoque WHERE qtd > 0").fetchall()
    
    page_content = render_template_string("""
    <div class="max-w-xl mx-auto card bg-base-100 shadow-2xl p-8 border-t-8 border-primary">
        <h2 class="text-3xl font-black mb-6 italic">Nova Venda</h2>
        <form method="POST" class="space-y-4">
            <select name="cliente_id" class="select select-bordered w-full">
                {% for c in clis %}<option value="{{ c['id'] }}">{{ c['nome'] }}</option>{% endfor %}
            </select>
            <div class="flex gap-2">
                <select name="produto" class="select select-bordered flex-1">
                    {% for p in prods %}<option value="{{ p['produto'] }}">{{ p['produto'] }}</option>{% endfor %}
                </select>
                <input name="qtd" type="number" value="1" class="input input-bordered w-24" />
            </div>
            <input name="valor_unit" step="0.01" type="number" placeholder="Preço Unitário" class="input input-bordered w-full" required />
            <div class="grid grid-cols-2 gap-2">
                <input name="pago_pix" placeholder="Valor PIX" step="0.01" type="number" class="input input-bordered border-success" />
                <input name="pago_dinheiro" placeholder="Valor Dinheiro" step="0.01" type="number" class="input input-bordered border-success" />
            </div>
            <button class="btn btn-primary w-full">FINALIZAR</button>
        </form>
    </div>
    """, clis=clis, prods=prods)
    return render_template_string(BASE_HTML, content=page_content)

# --- ESTOQUE ---
@app.route('/estoque', methods=['GET', 'POST'])
def estoque():
    if not session.get('user'): return redirect(url_for('login'))
    with get_db() as conn:
        if request.method == 'POST':
            conn.execute("UPDATE estoque SET qtd = qtd + ? WHERE produto = ?", (request.form['qtd'], request.form['produto']))
            conn.commit()
            flash("Estoque atualizado!", "success")
        dados = conn.execute("SELECT * FROM estoque").fetchall()
    page_content = render_template_string("""
    <h1 class="text-3xl font-black mb-8 italic text-secondary">Estoque</h1>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div class="card bg-base-100 p-8 shadow-xl border-t-4 border-secondary">
            <form method="POST" class="space-y-4">
                <select name="produto" class="select select-bordered w-full">
                    {% for d in dados %}<option>{{ d['produto'] }}</option>{% endfor %}
                </select>
                <input name="qtd" type="number" class="input input-bordered w-full" placeholder="Qtd entrada" required />
                <button class="btn btn-secondary w-full">ADICIONAR</button>
            </form>
        </div>
        <div class="space-y-4">
            {% for d in dados %}
            <div class="card bg-base-100 p-4 shadow-xl flex flex-row justify-between items-center">
                <span class="font-bold">{{ d['produto'] }}</span>
                <span class="badge badge-lg {{ 'badge-error' if d['qtd'] < 15 else 'badge-primary' }}">{{ d['qtd'] }} bjs</span>
            </div>
            {% endfor %}
        </div>
    </div>
    """, dados=dados)
    return render_template_string(BASE_HTML, content=page_content)

# --- FINANCEIRO ---
@app.route('/financeiro')
def financeiro():
    if not session.get('user'): return redirect(url_for('login'))
    with get_db() as conn:
        pendentes = conn.execute("SELECT * FROM vendas WHERE pendente > 0 ORDER BY id DESC").fetchall()
    page_content = render_template_string("""
    <h1 class="text-3xl font-black mb-8 italic text-error">Pendências</h1>
    <div class="grid grid-cols-1 gap-4">
        {% for v in pendentes %}
        <div class="card bg-base-100 p-6 shadow-xl flex flex-row justify-between items-center border border-error/20">
            <div>
                <h3 class="text-xl font-bold text-primary">{{ v['cli_nome'] }}</h3>
                <p class="text-xs opacity-50">Venda #{{ v['id'] }} - {{ v['data'] }}</p>
            </div>
            <div class="flex items-center gap-6">
                <div class="text-right text-error font-black">R$ {{ "%.2f"|format(v['pendente']) }}</div>
                <button class="btn btn-success" onclick="abrirBaixa('{{ v['id'] }}', '{{ v['pendente'] }}', '{{ v['cli_nome'] }}')">Receber</button>
            </div>
        </div>
        {% endfor %}
    </div>
    <dialog id="modal_baixa" class="modal"><div class="modal-box">
        <h3 class="font-bold text-lg mb-4">Receber de <span id="b_nome" class="text-primary"></span></h3>
        <form action="/vendas/dar_baixa" method="POST" class="space-y-4">
            <input type="hidden" name="venda_id" id="b_id">
            <input type="number" step="0.01" name="valor_pago" id="b_valor" class="input input-bordered w-full" required>
            <select name="forma" class="select select-bordered w-full"><option value="pix">PIX</option><option value="dinheiro">Dinheiro</option></select>
            <button class="btn btn-success w-full">Confirmar</button>
        </form>
    </div></dialog>
    <script>function abrirBaixa(id, val, nome){ document.getElementById('b_id').value=id; document.getElementById('b_nome').innerText=nome; document.getElementById('b_valor').value=val; modal_baixa.showModal(); }</script>
    """, pendentes=pendentes)
    return render_template_string(BASE_HTML, content=page_content)

@app.route('/vendas/dar_baixa', methods=['POST'])
def dar_baixa_venda():
    v_id, valor, forma = request.form['venda_id'], float(request.form['valor_pago']), request.form['forma']
    with get_db() as conn:
        v = conn.execute("SELECT * FROM vendas WHERE id=?", (v_id,)).fetchone()
        novo_p = max(0, v['pendente'] - valor)
        if forma == 'pix': conn.execute("UPDATE vendas SET pago_pix = pago_pix + ?, pendente = ? WHERE id = ?", (valor, novo_p, v_id))
        else: conn.execute("UPDATE vendas SET pago_dinheiro = pago_dinheiro + ?, pendente = ? WHERE id = ?", (valor, novo_p, v_id))
        conn.commit()
    flash("Baixa efetuada!", "success")
    return redirect(url_for('financeiro'))

# --- USUÁRIOS E LOGIN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form['username'], request.form['password']
        with get_db() as conn:
            user = conn.execute("SELECT * FROM usuarios WHERE username = ?", (u,)).fetchone()
            if user and check_password_hash(user['password'], p):
                session['user'] = u
                return redirect(url_for('dashboard'))
        flash("Erro no login!", "error")
    return render_template_string(BASE_HTML, content="""
    <div class="flex items-center justify-center min-h-screen">
        <div class="card w-96 bg-base-100 shadow-2xl border-t-8 border-primary p-8 text-center">
            <h2 class="text-3xl font-black italic mb-6">EGGPRO v10</h2>
            <form method="POST" class="space-y-4">
                <input name="username" placeholder="Usuário" class="input input-bordered w-full" required />
                <input name="password" type="password" placeholder="Senha" class="input input-bordered w-full" required />
                <button class="btn btn-primary w-full shadow-lg">ENTRAR</button>
            </form>
        </div>
    </div>
    """)

@app.route('/usuarios', methods=['GET', 'POST'])
def usuarios():
    if not session.get('user'): return redirect(url_for('login'))
    with get_db() as conn:
        if request.method == 'POST':
            u, p = request.form['username'], generate_password_hash(request.form['password'])
            conn.execute("INSERT OR IGNORE INTO usuarios (username, password) VALUES (?,?)", (u, p))
            conn.commit()
        users = conn.execute("SELECT id, username FROM usuarios").fetchall()
    page_content = render_template_string("""
    <h1 class="text-3xl font-black italic mb-8">Operadores</h1>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        {% for u in users %}
        <div class="card bg-base-100 p-6 shadow-xl flex justify-between items-center flex-row">
            <span class="font-bold">{{ u['username'] }}</span>
            <a href="/usuarios/excluir/{{ u['id'] }}" class="btn btn-ghost btn-xs text-error">Excluir</a>
        </div>
        {% endfor %}
        <div class="card bg-base-100 p-6 shadow-xl"><button class="btn btn-primary" onclick="m_u.showModal()">+ Novo</button></div>
    </div>
    <dialog id="m_u" class="modal"><div class="modal-box"><form method="POST" class="space-y-4"><input name="username" placeholder="Usuário" class="input input-bordered w-full" required /><input name="password" type="password" placeholder="Senha" class="input input-bordered w-full" required /><button class="btn btn-primary w-full">Criar</button></form></div></dialog>
    """, users=users)
    return render_template_string(BASE_HTML, content=page_content)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/usuarios/excluir/<int:id>')
def usuarios_excluir(id):
    with get_db() as conn:
        conn.execute("DELETE FROM usuarios WHERE id=?", (id,))
        conn.commit()
    return redirect(url_for('usuarios'))

@app.route('/vendas/excluir/<int:id>')
def vendas_excluir(id):
    with get_db() as conn:
        v = conn.execute("SELECT * FROM vendas WHERE id=?", (id,)).fetchone()
        conn.execute("UPDATE estoque SET qtd = qtd + ? WHERE produto = ?", (v['qtd'], v['prod']))
        conn.execute("DELETE FROM vendas WHERE id=?", (id,))
        conn.commit()
    flash("Estornado!", "warning")
    return redirect(url_for('vendas_log'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
