// ---------- Função debounce ----------
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// ---------- Localização do usuário ----------
let userLat = null;
let userLon = null;
if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
        (position) => {
            userLat = position.coords.latitude;
            userLon = position.coords.longitude;
        },
        (err) => console.warn('Geolocalização não disponível:', err)
    );
}

// ---------- Buscar sugestões Nominatim ----------
async function buscarSugestoes(query) {
    if (!query) return [];
    let url = `https://nominatim.openstreetmap.org/search?format=json&addressdetails=1&q=${encodeURIComponent(query)}&limit=5&countrycodes=BR`;
    if (userLat && userLon) {
        const delta = 0.05;
        url += `&viewbox=${userLon-delta},${userLat-delta},${userLon+delta},${userLat+delta}&bounded=1`;
    }
    try {
        const resp = await fetch(url, { headers: { 'Accept-Language': 'pt-BR' } });
        if (!resp.ok) return [];
        return await resp.json();
    } catch { return []; }
}

// ---------- Criar dropdown ----------
function criarDropdown(input, resultados) {
    let old = input.parentNode.querySelector('.autocomplete-dropdown');
    if (old) old.remove();
    if (!resultados.length) return;

    const dropdown = document.createElement('div');
    dropdown.classList.add('autocomplete-dropdown');

    resultados.forEach(item => {
        const endereco = [
            item.address.road || '',
            item.address.suburb || item.address.neighbourhood || '',
            item.address.city || item.address.town || item.address.village || '',
            item.address.state || '',
            item.address.postcode || ''
        ].filter(Boolean).join(', ');

        const option = document.createElement('div');
        option.classList.add('autocomplete-option');
        option.textContent = endereco;

        option.addEventListener('click', () => {
            input.value = endereco;

            if (input.id === 'origem') {
                document.getElementById('id_bairro_origem').value = item.address.suburb || item.address.neighbourhood || '';
                document.getElementById('id_cidade_origem').value = item.address.city || item.address.town || item.address.village || '';
                document.getElementById('id_estado_origem').value = item.address.state || '';
                document.getElementById('id_cep_origem').value = item.address.postcode || '';
            } else if (input.id === 'destino') {
                document.getElementById('id_bairro_destino').value = item.address.suburb || item.address.neighbourhood || '';
                document.getElementById('id_cidade_destino').value = item.address.city || item.address.town || item.address.village || '';
                document.getElementById('id_estado_destino').value = item.address.state || '';
                document.getElementById('id_cep_destino').value = item.address.postcode || '';
            }
            dropdown.remove();
        });

        dropdown.addEventListener('mouseenter', () => option.style.backgroundColor = '#f0f0f0');
        dropdown.addEventListener('mouseleave', () => option.style.backgroundColor = '#fff');

        dropdown.appendChild(option);
    });

    input.parentNode.appendChild(dropdown);
}

// ---------- Inicializar autocomplete ----------
function inicializarAutocomplete(inputId) {
    const input = document.getElementById(inputId);

    const handleInput = debounce(async () => {
        const query = input.value;
        if (query.length < 3) {
            criarDropdown(input, []);
            return;
        }
        const resultados = await buscarSugestoes(query);
        criarDropdown(input, resultados);
    }, 300);

    input.addEventListener('input', handleInput);

    document.addEventListener('click', (e) => {
        if (!input.parentNode.contains(e.target)) {
            const dropdown = input.parentNode.querySelector('.autocomplete-dropdown');
            if (dropdown) dropdown.remove();
        }
    });
}

// ---------- DOMContentLoaded ----------
document.addEventListener('DOMContentLoaded', () => {
    inicializarAutocomplete('origem');
    inicializarAutocomplete('destino');
});