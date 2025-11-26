const { createApp } = Vue

// Debounce utility
function debounce(fn, delay) {
    let timeoutId = null;
    return function(...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => fn.apply(this, args), delay);
    };
}

createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            products: [],
            loading: true,

            // Filters
            searchQuery: '',
            filterLocations: [], // Multi-select array
            filterDateFrom: '',
            filterDateTo: '',
            groupBy: null, // 'location', 'expiry', or null

            // UI State
            showAddModal: false,
            isEditing: false,
            showScanner: false,
            showFilters: false,
            showDuplicateModal: false,
            showStatistics: false,
            selectMode: false,
            showMobileSearch: false,
            showCamera: false,
            toasts: [], // Array of { id, message, type }

            // Duplicate handling
            duplicateProducts: [],
            duplicateAction: null,

            // Statistics
            statistics: null,
            advancedStats: null,

            // Shopping List
            showShoppingList: false,
            shoppingList: [],
            newShoppingItem: '',

            // Barcode History
            showBarcodeHistory: false,
            barcodeHistory: [],

            // Batch operations
            selectedProducts: [],

            // Notifications
            notificationsEnabled: false,
            notificationPermission: 'default',

            // Scanner
            html5QrcodeScanner: null,

            // Camera
            cameraStream: null,
            videoElement: null,

            // Form
            form: {
                id: null,
                ean: '',
                name: '',
                expiry_date: '',
                purchase_date: new Date().toISOString().split('T')[0],
                location: 'Vorratskammer',
                quantity: 1,
                weight_volume: '',
                notes: '',
                is_vegetarian: false,
                is_vegan: false,
                price: 0,
                image_url: '',
                category: '',
                tags: ''
            },

            // Constants
            locations: ['Kühlschrank', 'Vorratskammer', 'Tiefkühler', 'Schrank', 'Sonstiges'],
            
            // Cache for expensive computations
            _expiryCache: new Map()
        }
    },
    computed: {
        uniqueLocations() {
            // Get all unique locations from products + default locations
            const locs = new Set(this.locations);
            this.products.forEach(p => {
                if (p.location) locs.add(p.location);
            });
            return Array.from(locs).sort();
        },
        filteredProducts() {
            const searchLower = this.searchQuery.toLowerCase();
            const hasSearch = searchLower.length > 0;
            const hasLocationFilter = this.filterLocations.length > 0;
            const hasDateFilter = this.filterDateFrom || this.filterDateTo;
            
            return this.products.filter(p => {
                // 1. Search Query - early exit for better performance
                if (hasSearch) {
                    const matchesSearch = p.name.toLowerCase().includes(searchLower) ||
                        (p.notes && p.notes.toLowerCase().includes(searchLower)) ||
                        (p.ean && p.ean.includes(searchLower));
                    if (!matchesSearch) return false;
                }

                // 2. Location Filter
                if (hasLocationFilter && !this.filterLocations.includes(p.location)) {
                    return false;
                }

                // 3. Date Range Filter (Expiry)
                if (hasDateFilter) {
                    if (!p.expiry_date) return false;
                    const expiry = new Date(p.expiry_date);
                    if (this.filterDateFrom && expiry < new Date(this.filterDateFrom)) return false;
                    if (this.filterDateTo && expiry > new Date(this.filterDateTo)) return false;
                }

                return true;
            });
        },
        groupedProducts() {
            let products = [...this.filteredProducts];

            // Default Sort: Expiry Date ASC
            products.sort((a, b) => {
                let dateA = new Date(a.expiry_date || '9999-12-31');
                let dateB = new Date(b.expiry_date || '9999-12-31');
                return dateA - dateB;
            });

            if (!this.groupBy) {
                return { 'Alle Produkte': products };
            }

            if (this.groupBy === 'location') {
                return products.reduce((groups, product) => {
                    const loc = product.location || 'Sonstiges';
                    if (!groups[loc]) groups[loc] = [];
                    groups[loc].push(product);
                    return groups;
                }, {});
            }

            if (this.groupBy === 'expiry') {
                return products.reduce((groups, product) => {
                    const days = this.getDaysUntilExpiry(product.expiry_date);
                    let key = 'Später';
                    if (days < 0) key = 'Abgelaufen';
                    else if (days <= 7) key = 'Diese Woche';
                    else if (days <= 30) key = 'Diesen Monat';

                    if (!groups[key]) groups[key] = [];
                    groups[key].push(product);
                    return groups;
                }, {});
            }

            return { 'Alle Produkte': products };
        }
    },
    watch: {
        products() {
            // Clear expiry cache when products change
            this._expiryCache.clear();
        }
    },
    beforeUnmount() {
        // Cleanup scanner if still running
        if (this.html5QrcodeScanner) {
            this.stopScanner();
        }
        // Cleanup camera if still running
        if (this.cameraStream) {
            this.stopCamera();
        }
    },
    mounted() {
        this.fetchProducts();
        this.checkNotificationPermission();
        this.startExpiryAlerts();
    },
    methods: {
        // --- Toast Notification System ---
        showToast(message, type = 'info') {
            const id = Date.now();
            this.toasts.push({ id, message, type });
            setTimeout(() => {
                this.removeToast(id);
            }, 3000);
        },
        removeToast(id) {
            this.toasts = this.toasts.filter(t => t.id !== id);
        },

        // --- API Operations ---
        async fetchProducts() {
            this.loading = true;
            try {
                const response = await fetch('/api/products');
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                this.products = await response.json();
            } catch (error) {
                console.error('Fetch error:', error);
                this.showToast('Fehler beim Laden der Produkte', 'error');
            } finally {
                this.loading = false;
            }
        },
        async saveProduct() {
            // Check for duplicates first
            if (!this.isEditing && (this.form.ean || this.form.name)) {
                const isDuplicate = await this.checkDuplicate();
                if (isDuplicate) {
                    return; // Duplicate modal will handle next steps
                }
            }

            const url = this.isEditing ? `/api/products/${this.form.id}` : '/api/products';
            const method = this.isEditing ? 'PUT' : 'POST';

            try {
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.form)
                });

                if (response.ok) {
                    this.closeModal();
                    this.fetchProducts();
                    this.showToast(this.isEditing ? 'Produkt aktualisiert' : 'Produkt hinzugefügt', 'success');
                } else {
                    const err = await response.json();
                    throw new Error(err.message || 'Server Error');
                }
            } catch (error) {
                console.error('Save error:', error);
                this.showToast(`Fehler: ${error.message}`, 'error');
            }
        },
        async deleteProduct(id) {
            // Native confirm is still best for critical destructive actions
            if (!confirm('Möchtest du dieses Produkt wirklich löschen?')) return;

            try {
                const response = await fetch(`/api/products/${id}`, { method: 'DELETE' });
                if (response.ok) {
                    this.fetchProducts();
                    this.showToast('Produkt gelöscht', 'success');
                } else {
                    throw new Error('Delete failed');
                }
            } catch (error) {
                console.error('Delete error:', error);
                this.showToast('Fehler beim Löschen', 'error');
            }
        },

        // --- Form & Modal ---
        editProduct(product) {
            this.form = { ...product };
            // Ensure boolean conversion for checkboxes
            this.form.is_vegetarian = !!this.form.is_vegetarian;
            this.form.is_vegan = !!this.form.is_vegan;
            // Ensure price is number
            this.form.price = parseFloat(this.form.price) || 0;
            this.isEditing = true;
            this.showAddModal = true;
        },
        resetForm() {
            this.form = {
                id: null,
                ean: '',
                name: '',
                expiry_date: '',
                purchase_date: new Date().toISOString().split('T')[0],
                location: 'Vorratskammer',
                quantity: 1,
                weight_volume: '',
                notes: '',
                is_vegetarian: false,
                is_vegan: false,
                price: 0,
                image_url: '',
                category: '',
                tags: ''
            };
            this.isEditing = false;
        },
        closeModal() {
            this.showAddModal = false;
            this.stopScanner();
            this.stopCamera();
            setTimeout(() => this.resetForm(), 300);
        },
        toggleLocationFilter(loc) {
            if (this.filterLocations.includes(loc)) {
                this.filterLocations = this.filterLocations.filter(l => l !== loc);
            } else {
                this.filterLocations.push(loc);
            }
        },

        // --- Helpers ---
        formatDate(dateStr) {
            if (!dateStr) return 'Kein Datum';
            return new Date(dateStr).toLocaleDateString('de-DE');
        },
        getExpiryColor(dateStr) {
            if (!dateStr) return 'border-l-4 border-slate-300'; // Neutral
            const days = this.getDaysUntilExpiry(dateStr);
            if (days < 0) return 'border-l-4 border-red-500'; // Expired
            if (days <= 7) return 'border-l-4 border-amber-400'; // Warning
            return 'border-l-4 border-emerald-400'; // Good
        },
        getExpiryBadgeClass(dateStr) {
            if (!dateStr) return 'bg-slate-100 text-slate-600';
            const days = this.getDaysUntilExpiry(dateStr);
            if (days < 0) return 'bg-red-50 text-red-600 font-medium';
            if (days <= 7) return 'bg-amber-50 text-amber-600 font-medium';
            return 'bg-emerald-50 text-emerald-600 font-medium';
        },
        getDaysUntilExpiry(dateStr) {
            if (!dateStr) return 9999;
            
            // Check cache
            const cached = this._expiryCache.get(dateStr);
            if (cached !== undefined) return cached;
            
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            const expiry = new Date(dateStr);
            const diffTime = expiry - today;
            const days = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            
            // Cache result
            this._expiryCache.set(dateStr, days);
            return days;
        },

        // --- Scanner & External API ---
        fetchProductInfo: debounce(async function() {
            if (!this.form.ean || this.form.ean.length < 8) return;

            try {
                const response = await fetch(`/api/scan/${this.form.ean}`);
                const data = await response.json();

                if (data.found) {
                    this.form.name = data.name;
                    if (data.quantity) this.form.weight_volume = data.quantity;
                    if (data.category) this.form.category = data.category;
                    if (data.image_url && !this.form.image_url) this.form.image_url = data.image_url;
                    this.showToast('Produktinformationen gefunden', 'success');
                } else {
                    this.showToast('Produkt nicht in Datenbank gefunden', 'info');
                }
            } catch (error) {
                console.error('Scan API error:', error);
                // Silent fail or subtle toast
            }
        }, 500),
        startScanner() {
            this.showScanner = true;
            this.$nextTick(() => {
                this.html5QrcodeScanner = new Html5Qrcode("reader");
                const config = { fps: 10, qrbox: { width: 250, height: 250 } };
                this.html5QrcodeScanner.start(
                    { facingMode: "environment" },
                    config,
                    this.onScanSuccess,
                    this.onScanFailure
                ).catch(err => {
                    console.error("Scanner error", err);
                    this.showToast("Kamerazugriff fehlgeschlagen", "error");
                    this.showScanner = false;
                });
            });
        },
        stopScanner() {
            if (this.html5QrcodeScanner) {
                this.html5QrcodeScanner.stop()
                    .then(() => {
                        this.html5QrcodeScanner.clear();
                        this.html5QrcodeScanner = null;
                        this.showScanner = false;
                    })
                    .catch(err => {
                        console.error("Stop scanner error", err);
                        this.html5QrcodeScanner = null;
                        this.showScanner = false;
                    });
            } else {
                this.showScanner = false;
            }
        },
        onScanSuccess(decodedText, decodedResult) {
            this.form.ean = decodedText;
            this.stopScanner();
            this.fetchProductInfo();
            // Optional: Beep sound
        },
        onScanFailure(error) {
            // No-op to avoid console spam
        },

        // --- Image Upload ---
        async handleImageUpload(event) {
            const file = event.target.files[0];
            if (!file) return;

            // Check file type
            if (!file.type.startsWith('image/')) {
                this.showToast('Bitte nur Bilddateien hochladen', 'error');
                return;
            }

            // Check file size (max 2MB before compression)
            if (file.size > 2 * 1024 * 1024) {
                this.showToast('Bild zu groß (max 2MB)', 'error');
                return;
            }

            try {
                // Compress and convert to base64
                const compressedBase64 = await this.compressImage(file);
                
                // Check compressed size (max 200KB for Raspberry Pi)
                const sizeKB = (compressedBase64.length * 3) / 4 / 1024;
                if (sizeKB > 200) {
                    this.showToast('Komprimiertes Bild zu groß. Bitte kleineres Bild wählen.', 'error');
                    return;
                }

                this.form.image_url = compressedBase64;
                this.showToast('Bild hochgeladen', 'success');
            } catch (error) {
                console.error('Image upload error:', error);
                this.showToast('Fehler beim Hochladen', 'error');
            }
        },
        compressImage(file) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.readAsDataURL(file);
                reader.onload = (e) => {
                    const img = new Image();
                    img.src = e.target.result;
                    img.onload = () => {
                        // Calculate new dimensions (max 400px)
                        let width = img.width;
                        let height = img.height;
                        const maxSize = 400;

                        if (width > height && width > maxSize) {
                            height = (height * maxSize) / width;
                            width = maxSize;
                        } else if (height > maxSize) {
                            width = (width * maxSize) / height;
                            height = maxSize;
                        }

                        // Create canvas and compress
                        const canvas = document.createElement('canvas');
                        canvas.width = width;
                        canvas.height = height;
                        const ctx = canvas.getContext('2d');
                        ctx.drawImage(img, 0, 0, width, height);
                        
                        // Convert to base64 with quality 0.7
                        resolve(canvas.toDataURL('image/jpeg', 0.7));
                    };
                    img.onerror = reject;
                };
                reader.onerror = reject;
            });
        },
        removeImage() {
            this.form.image_url = '';
        },

        // --- Camera Capture ---
        async startCamera() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { 
                        facingMode: 'environment',
                        width: { ideal: 1280 },
                        height: { ideal: 720 }
                    } 
                });
                
                this.cameraStream = stream;
                this.showCamera = true;
                
                this.$nextTick(() => {
                    this.videoElement = document.getElementById('cameraVideo');
                    if (this.videoElement) {
                        this.videoElement.srcObject = stream;
                    }
                });
            } catch (error) {
                console.error('Camera access error:', error);
                this.showToast('Kamerazugriff fehlgeschlagen', 'error');
            }
        },
        stopCamera() {
            if (this.cameraStream) {
                this.cameraStream.getTracks().forEach(track => track.stop());
                this.cameraStream = null;
            }
            if (this.videoElement) {
                this.videoElement.srcObject = null;
                this.videoElement = null;
            }
            this.showCamera = false;
        },
        async capturePhoto() {
            if (!this.videoElement) return;
            
            try {
                // Create canvas and capture frame
                const canvas = document.createElement('canvas');
                canvas.width = this.videoElement.videoWidth;
                canvas.height = this.videoElement.videoHeight;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(this.videoElement, 0, 0);
                
                // Get blob
                const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.9));
                
                // Convert to file for compression
                const file = new File([blob], 'camera-capture.jpg', { type: 'image/jpeg' });
                
                // Use existing compression method
                const compressedBase64 = await this.compressImage(file);
                
                // Check compressed size
                const sizeKB = (compressedBase64.length * 3) / 4 / 1024;
                if (sizeKB > 200) {
                    this.showToast('Foto zu groß. Bitte erneut versuchen.', 'error');
                    return;
                }
                
                this.form.image_url = compressedBase64;
                this.stopCamera();
                this.showToast('Foto aufgenommen', 'success');
            } catch (error) {
                console.error('Capture error:', error);
                this.showToast('Fehler beim Aufnehmen', 'error');
            }
        },

        // --- Duplicate Detection ---
        async checkDuplicate() {
            try {
                const response = await fetch('/api/products/check-duplicate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ean: this.form.ean, name: this.form.name })
                });
                
                const data = await response.json();
                if (data.found && data.duplicates.length > 0) {
                    this.duplicateProducts = data.duplicates;
                    this.showDuplicateModal = true;
                    return true;
                }
                return false;
            } catch (error) {
                console.error('Duplicate check error:', error);
                return false;
            }
        },
        async handleDuplicateAction(action) {
            if (action === 'update') {
                // Update quantity of first duplicate
                const duplicate = this.duplicateProducts[0];
                duplicate.quantity += this.form.quantity;
                
                try {
                    const response = await fetch(`/api/products/${duplicate.id}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(duplicate)
                    });
                    
                    if (response.ok) {
                        this.showDuplicateModal = false;
                        this.closeModal();
                        this.fetchProducts();
                        this.showToast(`Menge aktualisiert: ${duplicate.quantity}x`, 'success');
                    }
                } catch (error) {
                    console.error('Update error:', error);
                    this.showToast('Fehler beim Aktualisieren', 'error');
                }
            } else if (action === 'new') {
                // Add as new product with different expiry
                this.showDuplicateModal = false;
                // Continue with save (duplicate check already passed)
                const url = '/api/products';
                try {
                    const response = await fetch(url, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(this.form)
                    });
                    
                    if (response.ok) {
                        this.closeModal();
                        this.fetchProducts();
                        this.showToast('Neues Produkt hinzugefügt', 'success');
                    }
                } catch (error) {
                    console.error('Save error:', error);
                    this.showToast('Fehler beim Speichern', 'error');
                }
            }
        },
        cancelDuplicate() {
            this.showDuplicateModal = false;
            this.duplicateProducts = [];
        },

        // --- Statistics ---
        async fetchStatistics() {
            try {
                const response = await fetch('/api/statistics');
                this.statistics = await response.json();
                this.showStatistics = true;
            } catch (error) {
                console.error('Statistics error:', error);
                this.showToast('Fehler beim Laden der Statistiken', 'error');
            }
        },
        closeStatistics() {
            this.showStatistics = false;
        },

        // --- Batch Operations ---
        toggleSelectMode() {
            this.selectMode = !this.selectMode;
            if (!this.selectMode) {
                this.selectedProducts = [];
            }
        },
        toggleProductSelection(productId) {
            const index = this.selectedProducts.indexOf(productId);
            if (index > -1) {
                this.selectedProducts.splice(index, 1);
            } else {
                this.selectedProducts.push(productId);
            }
        },
        isSelected(productId) {
            return this.selectedProducts.includes(productId);
        },
        async batchDelete() {
            if (this.selectedProducts.length === 0) return;
            if (!confirm(`${this.selectedProducts.length} Produkte löschen?`)) return;
            
            try {
                const response = await fetch('/api/products/batch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        operation: 'delete',
                        product_ids: this.selectedProducts
                    })
                });
                
                if (response.ok) {
                    this.fetchProducts();
                    this.showToast(`${this.selectedProducts.length} Produkte gelöscht`, 'success');
                    this.selectedProducts = [];
                    this.selectMode = false;
                }
            } catch (error) {
                console.error('Batch delete error:', error);
                this.showToast('Fehler beim Löschen', 'error');
            }
        },
        async batchMoveLocation() {
            if (this.selectedProducts.length === 0) return;
            const location = prompt('Neuer Standort:');
            if (!location) return;
            
            try {
                const response = await fetch('/api/products/batch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        operation: 'update_location',
                        product_ids: this.selectedProducts,
                        location: location
                    })
                });
                
                if (response.ok) {
                    this.fetchProducts();
                    this.showToast(`${this.selectedProducts.length} Produkte verschoben`, 'success');
                    this.selectedProducts = [];
                    this.selectMode = false;
                }
            } catch (error) {
                console.error('Batch move error:', error);
                this.showToast('Fehler beim Verschieben', 'error');
            }
        },

        // --- Quick Actions ---
        async quickIncrement(product) {
            product.quantity += 1;
            try {
                await fetch(`/api/products/${product.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(product)
                });
                this.fetchProducts();
            } catch (error) {
                console.error('Quick increment error:', error);
            }
        },

        // --- Notifications ---
        checkNotificationPermission() {
            if ('Notification' in window) {
                this.notificationPermission = Notification.permission;
                this.notificationsEnabled = Notification.permission === 'granted';
            }
        },
        async requestNotificationPermission() {
            if ('Notification' in window) {
                const permission = await Notification.requestPermission();
                this.notificationPermission = permission;
                this.notificationsEnabled = permission === 'granted';
                
                if (permission === 'granted') {
                    this.showToast('Benachrichtigungen aktiviert', 'success');
                }
            }
        },
        startExpiryAlerts() {
            // Check every hour for expiring products
            setInterval(() => {
                if (!this.notificationsEnabled) return;
                
                const expiringProducts = this.products.filter(p => {
                    const days = this.getDaysUntilExpiry(p.expiry_date);
                    return days >= 0 && days <= 3; // Within 3 days
                });
                
                if (expiringProducts.length > 0) {
                    new Notification('NexoSync - Produkte laufen ab!', {
                        body: `${expiringProducts.length} Produkt(e) laufen in den nächsten 3 Tagen ab`,
                        icon: '/static/icon.png',
                        badge: '/static/badge.png'
                    });
                }
            }, 3600000); // Check every hour
        },

        // --- Shopping List ---
        async fetchShoppingList() {
            try {
                const response = await fetch('/api/shopping-list');
                this.shoppingList = await response.json();
                this.showShoppingList = true;
            } catch (error) {
                console.error('Shopping list error:', error);
                this.showToast('Fehler beim Laden der Einkaufsliste', 'error');
            }
        },
        async addToShoppingList(productName = null) {
            const name = productName || this.newShoppingItem;
            if (!name) return;
            
            try {
                await fetch('/api/shopping-list', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: name, quantity: 1 })
                });
                this.newShoppingItem = '';
                this.fetchShoppingList();
                this.showToast('Zur Einkaufsliste hinzugefügt', 'success');
            } catch (error) {
                console.error('Add to shopping list error:', error);
                this.showToast('Fehler', 'error');
            }
        },
        async toggleShoppingItem(item) {
            try {
                await fetch(`/api/shopping-list/${item.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ...item, checked: !item.checked })
                });
                this.fetchShoppingList();
            } catch (error) {
                console.error('Toggle item error:', error);
            }
        },
        async deleteShoppingItem(id) {
            try {
                await fetch(`/api/shopping-list/${id}`, { method: 'DELETE' });
                this.fetchShoppingList();
                this.showToast('Artikel entfernt', 'success');
            } catch (error) {
                console.error('Delete shopping item error:', error);
            }
        },
        async clearCheckedItems() {
            try {
                await fetch('/api/shopping-list/clear-checked', { method: 'DELETE' });
                this.fetchShoppingList();
                this.showToast('Erledigte Artikel entfernt', 'success');
            } catch (error) {
                console.error('Clear items error:', error);
            }
        },
        async generateShoppingList() {
            try {
                const response = await fetch('/api/shopping-list/generate', { method: 'POST' });
                const data = await response.json();
                this.fetchShoppingList();
                this.showToast(data.message, 'success');
            } catch (error) {
                console.error('Generate list error:', error);
                this.showToast('Fehler beim Generieren', 'error');
            }
        },
        closeShoppingList() {
            this.showShoppingList = false;
        },

        // --- Barcode History ---
        async fetchBarcodeHistory() {
            try {
                const response = await fetch('/api/barcode-history?limit=20');
                this.barcodeHistory = await response.json();
                this.showBarcodeHistory = true;
            } catch (error) {
                console.error('History error:', error);
                this.showToast('Fehler beim Laden des Verlaufs', 'error');
            }
        },
        async quickAddFromHistory(item) {
            this.form.ean = item.ean;
            this.form.name = item.name;
            this.showBarcodeHistory = false;
            this.showAddModal = true;
            this.isEditing = false;
            await this.fetchProductInfo();
        },
        closeBarcodeHistory() {
            this.showBarcodeHistory = false;
        },

        // --- Advanced Statistics ---
        async fetchAdvancedStatistics() {
            try {
                const response = await fetch('/api/statistics/advanced');
                this.advancedStats = await response.json();
                await this.fetchStatistics(); // Also load basic stats
            } catch (error) {
                console.error('Advanced stats error:', error);
                this.showToast('Fehler beim Laden der Statistiken', 'error');
            }
        }
    }
}).mount('#app')
