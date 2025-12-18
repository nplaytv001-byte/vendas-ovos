// Dados iniciais (simulando um banco de dados)
let vendas = [
    { id: 1, cliente: "Ana Silva", produto: "Curso de Design", valor: 250.00 },
    { id: 2, cliente: "João Souza", produto: "E-book Marketing", valor: 47.90 }
];

const listaElemento = document.getElementById('vendas-lista');

// Função para Renderizar a lista na tela
function renderizarVendas() {
    listaElemento.innerHTML = ""; // Limpa a tabela

    vendas.forEach(venda => {
        const tr = document.createElement('tr');
        tr.className = "border-b hover:bg-gray-50";
        tr.innerHTML = `
            <td class="px-6 py-4">${venda.cliente}</td>
            <td class="px-6 py-4">${venda.produto}</td>
            <td class="px-6 py-4">R$ ${venda.valor.toFixed(2)}</td>
            <td class="px-6 py-4 text-center">
                <button onclick="abrirModal(${venda.id})" class="text-blue-600 hover:text-blue-800 mr-3">
                    <i class="fas fa-edit"></i> Editar
                </button>
                <button onclick="removerVenda(${venda.id})" class="text-red-600 hover:text-red-800">
                    <i class="fas fa-trash"></i> Remover
                </button>
            </td>
        `;
        listaElemento.appendChild(tr);
    });
}

// --- FUNÇÃO REMOVER ---
function removerVenda(id) {
    if (confirm("Tem certeza que deseja excluir esta venda?")) {
        vendas = vendas.filter(venda => venda.id !== id);
        renderizarVendas(); // Atualiza a tela
    }
}

// --- FUNÇÕES DE EDIÇÃO ---
const modal = document.getElementById('modal-edit');

function abrirModal(id) {
    const venda = vendas.find(v => v.id === id);
    if (venda) {
        document.getElementById('edit-id').value = venda.id;
        document.getElementById('edit-cliente').value = venda.cliente;
        document.getElementById('edit-valor').value = venda.valor;
        modal.classList.remove('hidden'); // Mostra o modal
    }
}

function fecharModal() {
    modal.classList.add('hidden');
}

function salvarEdicao() {
    const id = parseInt(document.getElementById('edit-id').value);
    const novoCliente = document.getElementById('edit-cliente').value;
    const novoValor = parseFloat(document.getElementById('edit-valor').value);

    // Atualiza o objeto no array
    vendas = vendas.map(venda => {
        if (venda.id === id) {
            return { ...venda, cliente: novoCliente, valor: novoValor };
        }
        return venda;
    });

    fecharModal();
    renderizarVendas();
}

// Inicializa a tabela ao carregar a página
renderizarVendas();
