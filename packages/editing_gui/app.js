document.addEventListener('alpine:init', () => {
    Alpine.data('curationTool', () => ({
        // --- STATE ---
        apiTarget: 'local',
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
        viewMode: 'table',
        tableHeaders: '',
        tableRows: [],
        lastSuccessfulUrl: '', // To store the URL for sharing

        // --- METHODS ---
        getApiBase() {
            return this.apiTarget === 'render' 
                ? 'https://herodb-project.onrender.com' 
                : 'http://127.0.0.1:8000';
        },
        // getAuthHeaders is no longer needed if Basic Auth is removed from the API
        // getAuthHeaders() { ... },

        clearHeroSearch() { 
            this.heroSearch = { key: '', keyword: '' }; 
        },
        clearLangSearch() { 
            this.langSearch = { ids: ['', '', '', ''], texts: ['', '', '', ''] }; 
        },
        
        async performHeroSearch() {
            if (!this.heroSearch.key || !this.heroSearch.keyword) {
                this.error = "Both Key and Keyword are required."; this.results = null; return;
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
                this.error = "At least one search field is required."; this.results = null; return;
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
            this.lastSuccessfulUrl = ''; // Reset on new fetch

            console.log(`Fetching from: ${url}`);
            try {
                // We fetch without auth headers now
                const response = await fetch(url); 
                const data = await response.json();
                console.log('API Response:', data);
                if (!response.ok) {
                    throw new Error(`API Error (${response.status}): ${data.detail || response.statusText}`);
                }
                this.results = data;
                this.lastSuccessfulUrl = url; // Save the URL on success
                this.generateTable(type);
            } catch (e) {
                this.error = e.message;
            } finally {
                this.loading = false;
            }
        },
        
        shareWithAI() {
            if (this.lastSuccessfulUrl) {
                navigator.clipboard.writeText(this.lastSuccessfulUrl)
                    .then(() => {
                        alert('API URL copied to clipboard!');
                    })
                    .catch(err => {
                        alert('Failed to copy URL. See console for error.');
                        console.error('Clipboard copy failed:', err);
                    });
            } else {
                alert('No successful search result to share yet.');
            }
        },

        generateTable(type) {
            if (!this.results || !this.results.results) {
                this.tableRows = []; 
                this.tableHeaders = ''; 
                if (!this.error) {
                    this.results = { count: 0 };
                }
                return;
            }
            if (type === 'hero') {
                this.tableHeaders = `<tr><th>Hero ID</th><th>Property Block</th></tr>`;
                this.tableRows = this.results.results.map((item, index) => ({
                    key: item.hero_id + index,
                    cells: [item.hero_id, `<pre>${JSON.stringify(item.property_block, null, 2)}</pre>`]
                }));
            } else if (type === 'lang') {
                this.tableHeaders = `<tr><th>Lang ID</th><th>English</th><th>Japanese</th></tr>`;
                this.tableRows = Object.entries(this.results.results).map(([key, value]) => ({
                    key: key,
                    cells: [key, value.en, value.ja]
                }));
            }
        },

        init() {
            // We no longer need to load credentials, but init() is kept for potential future use.
            console.log('Curation Tool Initialized.');
        }
    }));
});