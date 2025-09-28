document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('input[type="password"]').forEach(function(input) {
        if (input.dataset.hasToggle === 'true') return;
        input.dataset.hasToggle = 'true';

        // cria o wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'password-wrapper';
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        // cria o botão de olho
        const toggle = document.createElement('span');
        toggle.className = 'password-toggle';
        toggle.textContent = '👁️';
        toggle.title = 'Mostrar/Ocultar senha';

        toggle.addEventListener('click', function() {
            if (input.type === 'password') {
                input.type = 'text';
                toggle.textContent = '🙈';
            } else {
                input.type = 'password';
                toggle.textContent = '👁️';
            }
        });

        wrapper.appendChild(toggle);
    });
});
