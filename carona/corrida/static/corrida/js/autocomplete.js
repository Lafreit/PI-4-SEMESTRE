// ===============================
// AUTOCOMPLETE + COORDENADAS
// ===============================

// Debounce para reduzir chamadas à API
function debounce(fn, delay = 300) {
    let timeout;
    return (...args) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn(...args), delay);
    };
}

// Busca sugestões na API
async function buscarSugestoes(q) {
    if (!q || q.length < 3) return [];

    try {
        const resp = await fetch(`/corrida/api/geocode/?q=${encodeURIComponent(q)}`);
        if (!resp.ok) {
            console.error("Erro ao buscar autocomplete:", resp.status);
            return [];
        }
        const data = await resp.json();
        return data.results || [];
    } catch (err) {
        console.error("Erro ao buscar autocomplete:", err);
        return [];
    }
}

// Cria o dropdown com as sugestões
function criarDropdown(input, resultados) {
    removerDropdown();
    if (!resultados.length) return;

    const wrapper = input.parentElement;
    const box = document.createElement("div");
    box.className = "autocomplete-dropdown";
    box.style.display = "block";
    wrapper.appendChild(box);

    resultados.forEach((item, index) => {
        const op = document.createElement("div");
        op.className = "autocomplete-option";
        op.innerText = item.label;
        op.dataset.index = index;

        op.onclick = () => selecionarItem(input, item);

        box.appendChild(op);
    });
}

// Remove todos os dropdowns
function removerDropdown() {
    document.querySelectorAll(".autocomplete-dropdown").forEach(el => el.remove());
}

// Seleciona uma sugestão e preenche hidden inputs
function selecionarItem(input, item) {
    input.value = item.label;
    input.dataset.lat = item.lat;
    input.dataset.lon = item.lon;

    if(input.id === "origem") {
        document.getElementById("id_origem_lat").value = item.lat;
        document.getElementById("id_origem_lon").value = item.lon;
        document.getElementById("id_bairro_origem").value = item.bairro || '';
        document.getElementById("id_cidade_origem").value = item.city || '';
        document.getElementById("id_estado_origem").value = item.state || '';
        document.getElementById("id_cep_origem").value = item.postcode || '';
    }

    if(input.id === "destino") {
        document.getElementById("id_destino_lat").value = item.lat;
        document.getElementById("id_destino_lon").value = item.lon;
        document.getElementById("id_bairro_destino").value = item.bairro || '';
        document.getElementById("id_cidade_destino").value = item.city || '';
        document.getElementById("id_estado_destino").value = item.state || '';
        document.getElementById("id_cep_destino").value = item.postcode || '';
    }

    removerDropdown();
}

// Atualiza seleção no teclado
function atualizarSelecao(items, index) {
    items.forEach((el, i) => el.classList.toggle("selected", i === index));
}

// Ativa autocomplete em um input
function ativarAutocomplete(idInput) {
    const input = document.getElementById(idInput);
    if (!input) return;

    let selecionadoIndex = -1;
    let resultados = [];

    const inputHandler = debounce(async () => {
        const q = input.value.trim();
        resultados = await buscarSugestoes(q);
        criarDropdown(input, resultados);
        selecionadoIndex = -1;
    }, 300);

    input.addEventListener("input", inputHandler);

    // Navegação por teclado
    input.addEventListener("keydown", (e) => {
        const box = input.parentElement.querySelector(".autocomplete-dropdown");
        if (!box) return;
        const items = Array.from(box.querySelectorAll(".autocomplete-option"));

        if (e.key === "ArrowDown") {
            e.preventDefault();
            selecionadoIndex = (selecionadoIndex + 1) % items.length;
            atualizarSelecao(items, selecionadoIndex);
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            selecionadoIndex = (selecionadoIndex - 1 + items.length) % items.length;
            atualizarSelecao(items, selecionadoIndex);
        } else if (e.key === "Enter") {
            e.preventDefault();
            if (selecionadoIndex >= 0 && resultados[selecionadoIndex]) {
                selecionarItem(input, resultados[selecionadoIndex]);
            }
        }
    });
}

// ===============================
// VALIDAÇÃO DO FORM
// ===============================
document.addEventListener("DOMContentLoaded", () => {
    ativarAutocomplete("origem");
    ativarAutocomplete("destino");

    // Impede submit se coordenadas estiverem vazias
    const form = document.querySelector(".form-corrida");
    if (form) {
        form.addEventListener("submit", (e) => {
            const latO = document.getElementById("id_lat_origem").value;
            const lonO = document.getElementById("id_lon_origem").value;
            const latD = document.getElementById("id_lat_destino").value;
            const lonD = document.getElementById("id_lon_destino").value;

            if (!latO || !lonO || !latD || !lonD) {
                e.preventDefault();
                alert("Você deve selecionar origem e destino válidos a partir das sugestões.");
            }
        });
    }

    // Fecha dropdown ao clicar fora
    document.addEventListener("click", removerDropdown);
});
