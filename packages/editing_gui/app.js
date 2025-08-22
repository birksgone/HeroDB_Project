// Plain, reliable JavaScript.

document.addEventListener('DOMContentLoaded', () => {

    // --- Element References ---
    const apiUsernameInput = document.getElementById('api_username');
    const apiPasswordInput = document.getElementById('api_password');
    
    const heroSearchKeyInput = document.getElementById('hero_search_key');
    const heroSearchKeywordInput = document.getElementById('hero_search_keyword');
    const heroSearchBtn = document.getElementById('hero_search_btn');
    const heroClearBtn = document.getElementById('hero_clear_btn');

    const langIdInputs = document.querySelectorAll('.lang-id-input');
    const langTextInputs = document.querySelectorAll('.lang-text-input');
    const langSearchBtn = document.getElementById('lang_search_btn');
    const langClearBtn = document.getElementById('lang_clear_btn');

    const statusArea = document.getElementById('status_area');
    const resultsContainer = document.getElementById('results_container');
    const resultsCount = document.getElementById('results_count');
    
    const viewTableBtn = document.getElementById('view_table_btn');
    const viewJsonBtn = document.getElementById('view_json_btn');
    const tableView = document.getElementById('table_view');
    const jsonView = document.getElementById('json_view');
    const jsonOutput = document.getElementById('json_output');
    const resultsTableBody = document.querySelector('#results_table tbody');
    const resultsTableHeader = document.querySelector('#results_table thead');

    // --- Helper Functions ---
    function getApiBase() {
        return document.getElementById('api_target_render').checked 
            ? 'https://herodb-project.onrender.com' 
            : 'http://127.0.0.1:8000';
    }

    function getAuthHeaders() {
        return new Headers({
            'Authorization': 'Basic ' + btoa(apiUsernameInput.value + ':' + apiPasswordInput.value)
        });
    }

    function showStatus(message, isError = false) {
        statusArea.textContent = message;
        statusArea.className = isError ? 'status error' : 'status';
        resultsContainer.style.display = 'none';
    }

    // --- Main Fetch Logic ---
    async function fetchData(url, type) {
        showStatus('Loading...', false);
        try {
            const response = await fetch(url, { headers: getAuthHeaders() });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(`API Error (${response.status}): ${data.detail || 'Unknown error'}`);
            }
            statusArea.textContent = '';
            displayResults(data, type);
        } catch (e) {
            showStatus(e.message, true);
        }
    }
    
    // --- Result Display Logic ---
    function displayResults(data, type) {
        resultsContainer.style.display = 'block';
        resultsCount.textContent = data.count;
        jsonOutput.value = JSON.stringify(data, null, 2);
        resultsTableHeader.innerHTML = '';
        resultsTableBody.innerHTML = '';

        if (data.results) {
            if (type === 'hero') {
                resultsTableHeader.innerHTML = `<tr><th>Hero ID</th><th>Property Block</th></tr>`;
                data.results.forEach(item => {
                    const row = resultsTableBody.insertRow();
                    row.insertCell().textContent = item.hero_id;
                    const pre = document.createElement('pre');
                    pre.textContent = JSON.stringify(item.property_block, null, 2);
                    row.insertCell().appendChild(pre);
                });
            } else if (type === 'lang') {
                resultsTableHeader.innerHTML = `<tr><th>Lang ID</th><th>English</th><th>Japanese</th></tr>`;
                 Object.entries(data.results).forEach(([key, value]) => {
                    const row = resultsTableBody.insertRow();
                    row.insertCell().textContent = key;
                    row.insertCell().textContent = value.en;
                    row.insertCell().textContent = value.ja;
                });
            }
        }
    }

    // --- Event Listeners ---
    heroSearchBtn.addEventListener('click', () => {
        const key = heroSearchKeyInput.value;
        const keyword = heroSearchKeywordInput.value;
        if (!key || !keyword) {
            showStatus("Both Key and Keyword are required.", true); return;
        }
        const url = `${getApiBase()}/api/query?key=${encodeURIComponent(key)}&keyword=${encodeURIComponent(keyword)}`;
        fetchData(url, 'hero');
    });

    // --- THIS IS THE MISSING PIECE ---
    heroClearBtn.addEventListener('click', () => {
        heroSearchKeyInput.value = '';
        heroSearchKeywordInput.value = '';
    });

    langSearchBtn.addEventListener('click', () => {
        const params = new URLSearchParams();
        const idKeywords = Array.from(langIdInputs).map(input => input.value.trim()).filter(Boolean).join(',');
        const textKeywords = Array.from(langTextInputs).map(input => input.value.trim()).filter(Boolean).join(',');
        
        if (idKeywords) params.append('id_contains', idKeywords);
        if (textKeywords) params.append('text_contains', textKeywords);
        
        if (params.toString() === '') {
            showStatus("At least one search field is required.", true); return;
        }
        const url = `${getApiBase()}/api/lang/super_search?${params.toString()}`;
        fetchData(url, 'lang');
    });
    
    // --- AND THIS IS THE OTHER MISSING PIECE ---
    langClearBtn.addEventListener('click', () => {
        langIdInputs.forEach(input => input.value = '');
        langTextInputs.forEach(input => input.value = '');
    });

    viewTableBtn.addEventListener('click', () => {
        tableView.style.display = 'block';
        jsonView.style.display = 'none';
        viewTableBtn.classList.add('active');
        viewJsonBtn.classList.remove('active');
    });

    viewJsonBtn.addEventListener('click', () => {
        tableView.style.display = 'none';
        jsonView.style.display = 'block';
        viewTableBtn.classList.remove('active');
        viewJsonBtn.classList.add('active');
    });
    
    // --- Initialization & Local Storage ---
    apiUsernameInput.value = localStorage.getItem('herodb_username') || '';
    apiPasswordInput.value = localStorage.getItem('herodb_password') || '';
    apiUsernameInput.addEventListener('input', (e) => localStorage.setItem('herodb_username', e.target.value));
    apiPasswordInput.addEventListener('input', (e) => localStorage.setItem('herodb_password', e.target.value));
});