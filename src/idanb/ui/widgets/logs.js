import { AnsiUp } from 'https://esm.sh/ansi_up@6';
const ansi_up = new AnsiUp();

function render({ model, el }) {
    el.classList.add('widget-logs');
    el.innerHTML = `
        <details class="widget-logs__expandable">
            <summary>
                Logs
                <div class="widget-logs__controls">
                    <select class="widget-logs__levels"></select>
                    <button class="widget-logs__clear">clear</button>
                </div>
            </Summary>
            <pre class="widget-logs__logs"></pre>
        </details>
        <pre class="widget-logs__status"></pre>
    `;

    const logsElement = el.querySelector('.widget-logs__logs');
    const statusElement = el.querySelector('.widget-logs__status');
    const levelsSelect = el.querySelector('select.widget-logs__levels');
    const clearButton = el.querySelector('button.widget-logs__clear');

    clearButton.addEventListener('click', () => {
        logsElement.replaceChildren();
        log('Output has been cleared.\n');
    });

    function log(html) {
        statusElement.innerHTML = html;
        const child = document.createElement('span');
        child.innerHTML = html;
        logsElement.appendChild(child);
    }

    model.on("msg:custom", (msg) => {
        log(ansi_up.ansi_to_html(msg));
    });

    function updateAllLevels() {
        const allLevels = model.get('all_levels');
        const options = Object.entries(allLevels).map(([name, level]) => {
            const option = document.createElement('option');
            option.textContent = name;
            option.value = level;
            return option;
        });
        levelsSelect.replaceChildren(...options);
    }

    function updateLevel() {
        levelsSelect.value = model.get('level').toString();
    }

    updateAllLevels();
    model.on('change:all_levels', updateAllLevels);
    updateLevel();
    model.on('change:all_levels', updateLevel);

    levelsSelect.addEventListener('change', () => {
        const value = Number.parseInt(levelsSelect.value, 10);
        model.set('level', value);
        model.save_changes();
    });
}

export default { render };
