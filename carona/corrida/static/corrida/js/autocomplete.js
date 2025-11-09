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


// ---------- Buscar sugestões via Photon (versão final, inclui lat/lon) ----------
async function buscarSugestoes(query) {
    if (!query) return [];

    const params = new URLSearchParams({
        q: query,
        limit: 5,
        lang: 'pt'
    });

    if (userLat && userLon) {
        params.append('lat', userLat);
        params.append('lon', userLon);
    }

    const url = `https://photon.komoot.io/api/?${params.toString()}`;

    try {
        const resp = await fetch(url);
        if (!resp.ok) return [];
        const data = await resp.json();

        return data.features.map(f => {
            const props = f.properties || {};
            const coords = (f.geometry && f.geometry.coordinates) || [null, null];
            const endereco = [
                props.name || '',
                props.street || '',
                props.city || props.town || props.village || '',
                props.state || '',
                props.postcode || ''
            ].filter(Boolean).join(', ');

            return {
                display_name: endereco || props.label || props.osm_value || props.name || '',
                address: {
                    suburb: props.suburb || '',
                    neighbourhood: props.neighbourhood || '',
                    city: props.city || props.town || props.village || '',
                    state: props.state || '',
                    postcode: props.postcode || ''
                },
                lat: coords[1],
                lon: coords[0],
                properties: props
            };
        });

    } catch (err) {
        console.warn('Erro ao buscar sugestões:', err);
        return [];
    }
}


// ---------- Criar dropdown (com keyboard navigation e preenchimento de lat/lon) ----------
function criarDropdown(input, resultados) {
    // remove dropdown anterior
    let old = input.parentNode.querySelector('.autocomplete-dropdown');
    if (old) old.remove();
    if (!resultados || !resultados.length) return;

    const dropdown = document.createElement('div');
    dropdown.classList.add('autocomplete-dropdown');
    dropdown.setAttribute('role', 'listbox');
    dropdown.style.zIndex = 9999;

    let selectedIndex = -1;

    // helper para atualizar destaque visual
    function atualizarSelecao(newIndex) {
        const items = dropdown.querySelectorAll('.autocomplete-option');
        if (selectedIndex >= 0 && items[selectedIndex]) items[selectedIndex].classList.remove('selected');
        selectedIndex = newIndex;
        if (selectedIndex >= 0 && items[selectedIndex]) {
            items[selectedIndex].classList.add('selected');
            // rolagem suave se necessário
            const el = items[selectedIndex];
            const rect = el.getBoundingClientRect();
            const parentRect = dropdown.getBoundingClientRect();
            if (rect.bottom > parentRect.bottom) el.scrollIntoView(false);
            if (rect.top < parentRect.top) el.scrollIntoView();
        }
    }

    resultados.forEach((item, idx) => {
        const endereco = item.display_name || (
            [
                item.address && item.address.suburb,
                item.address && (item.address.neighbourhood || ''),
                item.address && item.address.city,
                item.address && item.address.state,
                item.address && item.address.postcode
            ].filter(Boolean).join(', ')
        ) || 'Endereço desconhecido';

        const option = document.createElement('div');
        option.classList.add('autocomplete-option');
        option.setAttribute('role', 'option');
        option.setAttribute('data-idx', idx);
        option.setAttribute('data-lat', item.lat || '');
        option.setAttribute('data-lon', item.lon || '');
        option.textContent = endereco;

        // mouse interactions (por opção)
        option.addEventListener('mouseenter', () => {
            const i = Number(option.dataset.idx);
            atualizarSelecao(i);
        });
        option.addEventListener('mouseleave', () => {
            // remove highlight quando sair do item
            option.classList.remove('selected');
            selectedIndex = -1;
        });

        option.addEventListener('click', () => {
            aplicarSelecao(input, item, endereco);
            dropdown.remove();
        });

        dropdown.appendChild(option);
    });

    input.parentNode.appendChild(dropdown);

    // teclado: navegação e seleção
    input.addEventListener('keydown', onKeyDown);

    function onKeyDown(e) {
        const items = dropdown.querySelectorAll('.autocomplete-option');
        if (!items.length) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            const next = Math.min(selectedIndex + 1, items.length - 1);
            atualizarSelecao(next);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            const prev = Math.max(selectedIndex - 1, 0);
            atualizarSelecao(prev);
        } else if (e.key === 'Enter') {
            if (selectedIndex >= 0 && items[selectedIndex]) {
                e.preventDefault();
                const el = items[selectedIndex];
                const lat = el.dataset.lat;
                const lon = el.dataset.lon;
                const endereco = el.textContent;
                const chosen = {
                    display_name: endereco,
                    address: {
                        suburb: el.dataset.suburb || '',
                        city: el.dataset.city || '',
                        state: el.dataset.state || '',
                        postcode: el.dataset.postcode || ''
                    },
                    lat: lat,
                    lon: lon
                };
                aplicarSelecao(input, chosen, endereco);
                dropdown.remove();
            }
        } else if (e.key === 'Escape') {
            dropdown.remove();
        }
    }

    // quando clicar fora, remove dropdown (já existe global, mas mantemos aqui)
    const onClickOutside = (ev) => {
        if (!input.parentNode.contains(ev.target)) {
            dropdown.remove();
        }
    };
    document.addEventListener('click', onClickOutside, { once: false });

    // limpa listeners quando dropdown é removido
    const observer = new MutationObserver(() => {
        if (!document.body.contains(dropdown)) {
            input.removeEventListener('keydown', onKeyDown);
            document.removeEventListener('click', onClickOutside);
            observer.disconnect();
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });

    // função para aplicar seleção (preenche campos visíveis e hidden)
    function aplicarSelecao(inputEl, itemObj, enderecoTexto) {
        inputEl.value = enderecoTexto;

        // campos de bairro/cidade/estado/cep
        const isOrigem = inputEl.id === 'origem';
        const prefix = isOrigem ? 'origem' : 'destino';

        const getEl = (name) => document.getElementById(`id_${name}_${prefix}`);

        // tenta preencher com propriedades retornadas (itemObj.address)
        try {
            const addr = itemObj.address || {};
            const bairro = addr.suburb || addr.neighbourhood || '';
            const cidade = addr.city || addr.town || addr.village || '';
            const estado = addr.state || '';
            const cep = addr.postcode || '';

            const elBairro = getEl('bairro');
            const elCidade = getEl('cidade');
            const elEstado = getEl('estado');
            const elCep = getEl('cep');

            if (elBairro) elBairro.value = bairro;
            if (elCidade) elCidade.value = cidade;
            if (elEstado) elEstado.value = estado;
            if (elCep) elCep.value = cep;

            // lat/lon hidden fields (IDs: id_lat_origem, id_lon_origem, id_lat_destino, id_lon_destino)
            const latEl = document.getElementById(`id_lat_${prefix}`);
            const lonEl = document.getElementById(`id_lon_${prefix}`);
            if (latEl && lonEl) {
                latEl.value = (itemObj.lat !== undefined && itemObj.lat !== null) ? itemObj.lat : '';
                lonEl.value = (itemObj.lon !== undefined && itemObj.lon !== null) ? itemObj.lon : '';
            }
        } catch (err) {
            console.warn('Erro ao aplicar seleção do autocomplete:', err);
        }
    }
}
