function curationTool() {
    return {
        // --- STATE (The App's Memory) ---
        apiTarget: 'local', // 'local' or 'render'
        username: '',
        password: '',
        heroSearch: { key: '', keyword: '' },
        langSearch: { id_contains: '', en_contains: '', ja_contains: '' },
        loading: false,
        error: null,
        results: null,
        viewMode: 'table', // 'table' or 'json'

        // --- COMPUTED (Derived Data) ---
        getApiBase() {
            if (this.apiTarget === 'render') {
                return 'https://herodb-project.onrender.com';
            }
            return 'http://127.0.0.1:8000';
        },
        getAuthHeaders() {
            // btoa is a browser function to create Base64 strings
            return new Headers({
                'Authorization': 'Basic ' + btoa(this.username + ':' + this.password)
            });
        },

        // --- METHODS (The App's Actions) ---
        async performHeroSearch() {
            if (!this.heroSearch.key || !this.heroSearch.keyword) {
                this.error = "Both Key and Keyword are required for Hero Block Search.";
                return;
            }
            const url = `${this.getApiBase()}/api/query?key=${encodeURIComponent(this.heroSearch.key)}&keyword=${encodeURIComponent(this.heroSearch.keyword)}`;
            await this.fetchData(url);
        },
        async performLangSearch() {
            const params = new URLSearchParams();
            if (this.langSearch.id_contains) params.append('id_contains', this.langSearch.id_contains);
            if (this.langSearch.en_contains) params.append('en_contains', this.langSearch.en_contains);
            if (this.langSearch.ja_contains) params.append('ja_contains', this.langSearch.ja_contains);
            if (params.toString() === '') {
                this.error = "At least one search field is required for Language DB Search.";
                return;
            }
            const url = `${this.getApiBase()}/api/lang/super_search?${params.toString()}`;
            await this.fetchData(url);
        },
        async fetchData(url) {
            this.loading = true;
            this.error = null;
            this.results = null;
            try {
                const response = await fetch(url, { headers: this.getAuthHeaders() });
                if (!response.ok) {
                    const errData = await response.json();
                    throw new Error(`API Error (${response.status}): ${errData.detail || 'Unknown error'}`);
                }
                this.results = await response.json();
            } catch (e) {
                this.error = e.message;
            } finally {
                this.loading = false;
            }
        },
        
        // --- INITIALIZATION ---
        init() {
            // Load credentials from browser's local storage if they exist
            this.username = localStorage.getItem('herodb_username') || '';
            this.password = localStorage.getItem('herodb_password') || '';

            // Save credentials whenever they change
            this.$watch('username', value => localStorage.setItem('herodb_username', value));
            this.$watch('password', value => localStorage.setItem('herodb_password', value));
        }
    }
}