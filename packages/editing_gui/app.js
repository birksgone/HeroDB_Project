// packages/editing_gui/app.js (The True Final Version)

function curationTool() {
    return {
        // --- STATE (The App's Memory) ---
        apiTarget: 'local', // 'local' or 'render'
        username: '',
        password: '',
        heroSearch: { key: '', keyword: '' },
        langSearch: { 
            ids: ['', '', '', ''],
            texts: ['', '', '', '']
        },
        loading: false,
        error: null,
        results: null,
        viewMode: 'table', // 'table' or 'json'
        tableHeaders: '',
        tableRows: [],

        // --- COMPUTED (Derived Data) ---
        getApiBase() {
            if (this.apiTarget === 'render') {
                return 'https://herodb-project.onrender.com';
            }
            return 'http://127.0.0.1:8000';
        },
        getAuthHeaders() {
            // btoa is a browser function to create Base64 strings for Basic Auth
            return new Headers({
                'Authorization': 'Basic ' + btoa(this.username + ':' + this.password)
            });
        },

        // --- METHODS (The App's Actions) ---
        clearHeroSearch() {
            this.heroSearch = { key: '', keyword: '' };
        },
        clearLangSearch() {
            this.langSearch = { ids: ['', '', '', ''], texts: ['', '', '', ''] };
        },
        
        async performHeroSearch() {
            if (!this.heroSearch.key || !this.heroSearch.keyword) {
                this.error = "Both Key and Keyword are required for Hero Block Search.";
                this.results = null;
                return;
            }
            const url = `${this.getApiBase()}/api/query?key=${encodeURIComponent(this.heroSearch.key)}&keyword=${encodeURIComponent(this.heroSearch.keyword)}`;
            await this.fetchData(url, 'hero');
        },

        async performLangSearch() {
            const params = new URLSearchParams();
            const idKeywords = this.langSearch.ids.filter(val => val.trim() !== '').join(',');
            const textKeywords = this.langSearch.texts.filter(val => val.trim() !== '').join(',');

            if (idKeywords) params.append('id_contains', idKeywords);
            if (textKeywords) params.append('text_contains', textKeywords);
            
            if (params.toString() === '') {
                this.error = "At least one search field is required for Language DB Search.";
                this.results = null;
                return;
            }
            const url = `${this.getApiBase()}/api/lang/super_search?${params.toString()}`;
            await this.fetchData(url, 'lang');
        },

        async fetchData(url, type) {
            this.loading = true;
            this.error = null;
            this.results = null;
            this.tableRows = [];
            this.tableHeaders = '';
            
            try {
                const response = await fetch(url, { headers: this.getAuthHeaders() });
                const data = await response.json(); // Always try to get JSON for error details
                if (!response.ok) {
                    throw new Error(`API Error (${response.status}): ${data.detail || response.statusText}`);
                }
                this.results = data;
                this.generateTable(type);
            } catch (e) {
                this.error = e.message;
            } finally {
                this.loading = false;
            }
        },
        
        generateTable(type) {
            if (!this.results || !this.results.results) {
                this.tableRows = []; this.tableHeaders = ''; return;
            }

            if (type === 'hero') {
                this.tableHeaders = `<tr><th>Hero ID</th><th>Property Block</th></tr>`;
                this.tableRows = this.results.results.map((item, index) => ({
                    key: item.hero_id + index, // Use index for a unique key
                    cells: [
                        item.hero_id, 
                        `<pre>${JSON.stringify(item.property_block, null, 2)}</pre>`
                    ]
                }));
            } else if (type === 'lang') {
                this.tableHeaders = `<tr><th>Lang ID</th><th>English</th><th>Japanese</th></tr>`;
                this.tableRows = Object.entries(this.results.results).map(([key, value]) => ({
                    key: key,
                    cells: [key, value.en, value.ja]
                }));
            }
        },

        // --- INITIALIZATION ---
        init() {
            // Load credentials from browser's local storage if they exist
            this.username = localStorage.getItem('herodb_username') || '';
            this.password = localStorage.getItem('herodb_password') || '';

            // Save credentials to local storage whenever they change
            this.$watch('username', value => localStorage.setItem('herodb_username', value));
            this.$watch('password', value => localStorage.setItem('herodb_password', value));
        }
    }
}