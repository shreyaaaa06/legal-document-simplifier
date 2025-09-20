// main.js
const App = {
    currentUser: null,
    documents: [],
    isAuthenticated: false,
    apiBase: '/api'
};
let currentConversationId = null;

// Initialize application
function initializeApp() {
    checkAuthentication();
    initializeNavigation();
    initializeEventListeners();
    
    // Auto-refresh authentication status
    setInterval(checkAuthentication, 300000); // 5 minutes
}

// Authentication functions
async function checkAuthentication() {
    try {
        const response = await fetch(`${App.apiBase}/auth/check-auth`);
        const data = await response.json();
        
        App.isAuthenticated = data.authenticated;
        if (data.authenticated) {
            App.currentUser = data.user;
            updateUserInterface(true);
        } else {
            updateUserInterface(false);
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        updateUserInterface(false);
    }
}

function updateUserInterface(isAuthenticated) {
    const userNameElement = document.getElementById('user-name');
    const navbar = document.getElementById('navbar');
    
    if (isAuthenticated && App.currentUser) {
        if (userNameElement) {
            userNameElement.textContent = App.currentUser.name || App.currentUser.email;
        }
        navbar?.classList.remove('hidden');
        
        // Redirect to dashboard if on login/register page
        if (window.location.pathname === '/login' || window.location.pathname === '/register') {
            window.location.href = '/dashboard';
        }
    } else {
        navbar?.classList.add('hidden');
        
        // Redirect to login if on protected page
        const protectedPages = ['/dashboard', '/upload', '/document'];
        if (protectedPages.some(page => window.location.pathname.startsWith(page))) {
            window.location.href = '/login';
        }
    }
}

// API helper functions
async function apiCall(endpoint, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include'
    };
    
    const finalOptions = { ...defaultOptions, ...options };
    
    // Don't set Content-Type for FormData
    if (options.body instanceof FormData) {
        delete finalOptions.headers['Content-Type'];
    }
    
    showLoading();
    
    try {
        const response = await fetch(`${App.apiBase}${endpoint}`, finalOptions);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Request failed');
        }
        
        return data;
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    } finally {
        hideLoading();
    }
}

// Loading functions
function showLoading(text = 'Loading...') {
    const overlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-text');
    
    if (loadingText) loadingText.textContent = text;
    if (overlay) overlay.classList.remove('hidden');
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.classList.add('hidden');
}

// Toast notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <i class="fas fa-${getToastIcon(type)}"></i>
            <span>${message}</span>
        </div>
    `;
    
    container.appendChild(toast);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-out forwards';
        setTimeout(() => container.removeChild(toast), 300);
    }, 5000);
}

function getToastIcon(type) {
    const icons = {
        success: 'check-circle',
        error: 'exclamation-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    };
    return icons[type] || 'info-circle';
}

// Navigation functions
function initializeNavigation() {
    const navToggle = document.getElementById('nav-toggle');
    const navMenu = document.getElementById('nav-menu');
    const userMenuButton = document.getElementById('user-menu-button');
    const userDropdown = document.getElementById('user-dropdown');
    
    // Mobile menu toggle
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', () => {
            navMenu.classList.toggle('show');
        });
    }
    
    // User dropdown
    if (userMenuButton && userDropdown) {
        userMenuButton.addEventListener('click', (e) => {
            e.stopPropagation();
            userDropdown.classList.toggle('show');
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', () => {
            userDropdown.classList.remove('show');
        });
    }
    
    // Highlight active page
    highlightActivePage();
}

function highlightActivePage() {
    const navLinks = document.querySelectorAll('.nav-link');
    const currentPath = window.location.pathname;
    
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
}

// Authentication forms
async function handleLogin(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    
    try {
        const response = await apiCall('/auth/login', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        showToast('Login successful!', 'success');
        App.currentUser = response.user;
        App.isAuthenticated = true;
        updateUserInterface(true);
        
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function handleRegister(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    
    // Validate passwords match
    if (data.password !== data.confirmPassword) {
        showToast('Passwords do not match', 'error');
        return;
    }
    
    try {
        const response = await apiCall('/auth/register', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        showToast('Registration successful!', 'success');
        App.currentUser = response.user;
        App.isAuthenticated = true;
        updateUserInterface(true);
        
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function logout() {
    try {
        await apiCall('/auth/logout', { method: 'POST' });
        
        App.currentUser = null;
        App.isAuthenticated = false;
        App.documents = [];
        
        showToast('Logged out successfully', 'success');
        updateUserInterface(false);
        
    } catch (error) {
        console.error('Logout failed:', error);
        // Force logout on client side
        App.currentUser = null;
        App.isAuthenticated = false;
        updateUserInterface(false);
    }
}

// Profile management
function showProfile() {
    const modal = document.getElementById('profile-modal');
    const nameInput = document.getElementById('profile-name');
    const emailInput = document.getElementById('profile-email');
    
    if (App.currentUser) {
        nameInput.value = App.currentUser.name || '';
        emailInput.value = App.currentUser.email || '';
    }
    
    modal.classList.remove('hidden');
}

function hideProfile() {
    const modal = document.getElementById('profile-modal');
    modal.classList.add('hidden');
}

async function handleProfileUpdate(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    
    try {
        const response = await apiCall('/auth/profile', {
            method: 'PUT',
            body: JSON.stringify(data)
        });
        
        App.currentUser = response.user;
        updateUserInterface(true);
        hideProfile();
        showToast('Profile updated successfully', 'success');
        
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// Document functions
async function loadDocuments() {
    try {
        const response = await apiCall('/documents/');
        App.documents = response.documents || [];
        return App.documents;
    } catch (error) {
        showToast('Failed to load documents', 'error');
        return [];
    }
}

async function uploadDocument(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        showLoading('Uploading document...');
        
        const response = await fetch(`${App.apiBase}/documents/upload`, {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });
        
        console.log('Upload response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Upload failed with response:', errorText);
            throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Upload successful:', data);
        
        showToast('Document uploaded successfully!', 'success');
        return data.document;
        
    } catch (error) {
        console.error('Upload error:', error);
        showToast(`Upload failed: ${error.message}`, 'error');
        throw error;
    } finally {
        hideLoading();
    }
}

async function handleFileSelection(event) {
    const files = Array.from(event.target.files || event.dataTransfer?.files || []);
    
    if (files.length === 0) return;
    
    const file = files[0];
    
    try {
        // Validate file
        validateFile(file);
        
        console.log('Uploading file:', file.name, 'Size:', file.size);
        
        // Upload and process
        const document = await uploadDocument(file);
        
        console.log('Document uploaded:', document);
        
        // Redirect to document view after upload
        if (document && document.id) {
            window.location.href = `/document/${document.id}`;
        }
        
    } catch (error) {
        console.error('File handling failed:', error);
        showToast(error.message, 'error');
    }
    
    // Reset file input properly
    if (event.target && event.target.type === 'file') {
        event.target.value = '';
    }
}

async function processDocument(documentId) {
    try {
        showLoading('Processing document with AI...');
        
        const response = await apiCall(`/agents/process-document/${documentId}`, {
            method: 'POST',
            body: JSON.stringify({
                simplification_level: 'general'
            })
        });
        
        showToast('Document processed successfully!', 'success');
        return response;
        
    } catch (error) {
        showToast(`Processing failed: ${error.message}`, 'error');
        throw error;
    }
}

async function deleteDocument(documentId) {
    if (!confirm('Are you sure you want to delete this document?')) {
        return;
    }
    
    try {
        await apiCall(`/documents/${documentId}`, {
            method: 'DELETE'
        });
        
        showToast('Document deleted successfully', 'success');
        
        // Remove from local cache
        App.documents = App.documents.filter(doc => doc.id !== documentId);
        
        // Refresh the page if we're on the dashboard
        if (window.location.pathname === '/dashboard') {
            await loadDashboard();
        }
        
    } catch (error) {
        showToast(`Failed to delete document: ${error.message}`, 'error');
    }
}

// Q&A functions
// Update existing askQuestion function
async function askQuestion(question, documentId = null) {
    // Check if question is calendar-related first
    const calendarKeywords = ['calendar', 'deadline', 'due', 'when', 'schedule', 'payment'];
    
    if (calendarKeywords.some(keyword => question.toLowerCase().includes(keyword))) {
        try {
            return await handleCalendarQuestion(question);
        } catch (error) {
            // Fall back to regular Q&A if calendar handling fails
        }
    }
    
    // Existing askQuestion logic continues...
    try {
        showLoading('Finding answer...');
        
        const response = await apiCall('/agents/ask-question', {
            method: 'POST',
            body: JSON.stringify({
                question: question,
                document_id: documentId,
                conversation_id: currentConversationId
            })
        });
        
        if (response.conversation_id) {
            currentConversationId = response.conversation_id;
        }
        
        return response;
        
    } catch (error) {
        showToast(`Failed to get answer: ${error.message}`, 'error');
        throw error;
    }
}

async function handleCalendarQuestion(question) {
    try {
        const response = await apiCall('/agents/ask-calendar', {
            method: 'POST',
            body: JSON.stringify({ question })
        });
        
        if (response.show_calendar) {
            showCalendarModal(response.deadlines);
        }
        
        return response;
    } catch (error) {
        console.error('Calendar question failed:', error);
        throw error;
    }
}

function showCalendarModal(deadlines) {
    // Create and show calendar modal with deadlines
    const modal = createCalendarModal(deadlines);
    document.body.appendChild(modal);
}

async function getSuggestedQuestions(documentId = null) {
    try {
        const params = documentId ? `?document_id=${documentId}` : '';
        const response = await apiCall(`/agents/suggested-questions${params}`);
        return response.suggestions || [];
    } catch (error) {
        console.error('Failed to get suggestions:', error);
        return [];
    }
}

// Dashboard functions
async function loadDashboard() {
    try {
        showLoading('Loading dashboard...');
        
        const [documentsResponse, dashboardResponse] = await Promise.all([
            apiCall('/documents/'),
            apiCall('/documents/dashboard').catch(() => ({
                total_documents: 0,
                processing_documents: 0,
                completed_documents: 0,
                overall_stats: { high_risk_clauses: 0 },
                upcoming_deadlines: [],  // Add this
                high_risk_alerts: []     // Add this
            }))
        ]);
        
        App.documents = documentsResponse.documents || [];
        
        renderDashboardStats(dashboardResponse);
        renderRecentDocuments(App.documents);
        renderUpcomingDeadlines(dashboardResponse.upcoming_deadlines || []);
        renderRiskAlerts(dashboardResponse.high_risk_alerts || []);
        
        // NEW: Load deadlines from processed documents
        await loadDeadlinesFromDocuments();
        
    } catch (error) {
        console.error('Dashboard load failed:', error);
        showToast('Failed to load dashboard data', 'error');
        renderRecentDocuments([]);
    } finally {
        hideLoading();
    }
}

function renderDashboardStats(dashboardData) {
    const statsContainer = document.getElementById('dashboard-stats');
    if (!statsContainer) return;
    
    const stats = [
        {
            icon: 'file-alt',
            number: dashboardData.total_documents,
            label: 'Total Documents',
            color: 'var(--primary-color)'
        },
        {
            icon: 'clock',
            number: dashboardData.processing_documents,
            label: 'Processing',
            color: 'var(--warning-color)'
        },
        {
            icon: 'check-circle',
            number: dashboardData.completed_documents,
            label: 'Completed',
            color: 'var(--success-color)'
        },
        {
            icon: 'exclamation-triangle',
            number: dashboardData.overall_stats?.high_risk_clauses || 0,
            label: 'High Risk Clauses',
            color: 'var(--danger-color)'
        }
    ];
    
    statsContainer.innerHTML = stats.map(stat => `
        <div class="stat-card">
            <div class="stat-icon" style="background-color: ${stat.color}20; color: ${stat.color};">
                <i class="fas fa-${stat.icon}"></i>
            </div>
            <div class="stat-number">${stat.number}</div>
            <div class="stat-label">${stat.label}</div>
        </div>
    `).join('');
}

function renderRecentDocuments(documents) {
    const container = document.getElementById('recent-documents');
    if (!container) return;
    
    if (documents.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 3rem; color: var(--text-secondary);">
                <i class="fas fa-file-alt" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.5;"></i>
                <p>No documents uploaded yet</p>
                <a href="/upload" class="btn btn-primary" style="margin-top: 1rem;">Upload Your First Document</a>
            </div>
        `;
        return;
    }
    
    container.innerHTML = documents.slice(0, 5).map(doc => `
        <div class="document-item" onclick="viewDocument('${doc.id}')">
            <div class="document-header">
                <div>
                    <div class="document-title">${doc.filename}</div>
                    <div class="document-type">${doc.document_type || 'Unknown Type'}</div>
                </div>
                <div class="status-badge status-${doc.status}">
                    <i class="fas fa-${getStatusIcon(doc.status)}"></i>
                    ${doc.status}
                </div>
            </div>
            <div class="document-meta">
                <span><i class="fas fa-calendar"></i> ${formatDate(doc.created_at)}</span>
                <span><i class="fas fa-list"></i> ${doc.clause_count || 0} clauses</span>
                ${doc.risk_score ? `<span class="risk-indicator risk-${getRiskLevel(doc.risk_score)}">
                    <i class="fas fa-shield-alt"></i> Risk: ${doc.risk_score}/100
                </span>` : ''}
            </div>
            <div class="document-actions">
                <button class="btn btn-sm btn-primary" onclick="event.stopPropagation(); viewDocument('${doc.id}')">
                    <i class="fas fa-eye"></i> View
                </button>
                <button class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); downloadDocument('${doc.id}')">
                    <i class="fas fa-download"></i> Download
                </button>
                <button class="btn btn-sm btn-danger" onclick="event.stopPropagation(); deleteDocument('${doc.id}')">
                    <i class="fas fa-trash"></i> Delete
                </button>
            </div>
        </div>
    `).join('');
}

// Utility functions
function getStatusIcon(status) {
    const icons = {
        processing: 'clock',
        completed: 'check',
        failed: 'exclamation-triangle'
    };
    return icons[status] || 'question';
}

function getRiskLevel(score) {
    if (score >= 70) return 'high';
    if (score >= 40) return 'medium';
    return 'low';
}

function formatDate(dateString) {
    if (!dateString) return 'Unknown';
    
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 1) return 'Today';
    if (diffDays === 2) return 'Yesterday';
    if (diffDays <= 7) return `${diffDays} days ago`;
    
    return date.toLocaleDateString();
}

function viewDocument(documentId) {
    window.location.href = `/document/${documentId}`;
}

function downloadDocument(documentId) {
    // This would be implemented based on your download requirements
    showToast('Download functionality coming soon', 'info');
}

// File upload handling
function initializeFileUpload() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    
    if (!uploadArea || !fileInput) return;
    
    // Click to select file
    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });
    
    // File selection handling
    fileInput.addEventListener('change', handleFileSelection);
    
    // Drag and drop handling
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const files = Array.from(e.dataTransfer.files);
        if (files.length > 0) {
            handleFileSelection({ target: { files } });
        }
    });
}

// Main file selection handler
async function handleFileSelection(event) {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;

    const file = files[0];

    try {
        validateFile(file);  // Modular validation

        const document = await uploadDocument(file);

        // Redirect to document page
        setTimeout(() => {
            window.location.href = `/document/${document.id}`;
        }, 1000);  // small delay for better UX

    } catch (error) {
        console.error('File handling failed:', error);
        showToast(error.message, 'error');  // show user-friendly message
    }
}

// Validation function
function validateFile(file) {
    // Size check (16MB)
    if (file.size > 16 * 1024 * 1024) {
        throw new Error('File size must be less than 16MB');
    }

    // Allowed types (PDF, Word, images)
    const allowedTypes = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
        'image/jpeg',
        'image/png',
        'image/bmp',
        'image/tiff'
    ];

    if (!allowedTypes.includes(file.type)) {
        throw new Error('Unsupported file type. Please upload PDF, Word document, or image file.');
    }
}


// Event listeners
function initializeEventListeners() {
    // Profile form
    const profileForm = document.getElementById('profile-form');
    if (profileForm) {
        profileForm.addEventListener('submit', handleProfileUpdate);
    }
    
    // Login form
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    // Register form
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
    
    // File upload
    initializeFileUpload();
    
    // Page-specific initializations
    const path = window.location.pathname;
    
    if (path === '/dashboard') {
        loadDashboard();
    } else if (path.startsWith('/document/')) {
        const documentId = path.split('/')[2];
        loadDocumentAnalysis(documentId);
    }
}

// Document analysis page
async function loadDocumentAnalysis(documentId) {
    try {
        console.log(`Loading document analysis for ${documentId}`);
        
        showLoadingState();
        
        const response = await apiCall(`/documents/${documentId}`);
        console.log('Document response:', response);
        
        // Check if document is still processing
        if (response.status === 'processing') {
            showProcessingStatus(documentId);
            return;
        }
        
        if (response.status === 'failed') {
            showFailedStatus(documentId);
            return;
        }
        
        // Check if there are clauses
        if (!response.clauses || response.clauses.length === 0) {
            showNoClausesMessage();
            return;
        }
        
        hideLoadingState();
        renderDocumentAnalysis(response);
        
        // Load Q&A suggestions
        const suggestions = await getSuggestedQuestions(documentId);
        renderQASuggestions(suggestions, documentId);
        if (!currentConversationId) {
            try {
                const convResponse = await apiCall('/agents/conversations', {
                    method: 'POST',
                    body: JSON.stringify({ document_id: documentId })
                });
                currentConversationId = convResponse.conversation.id;
                console.log('Created conversation:', currentConversationId);
            } catch (error) {
                console.log('Could not create conversation:', error);
            }
        }
        
    } catch (error) {
        console.error('Failed to load document analysis:', error);
        hideLoadingState();
        window.showToast('Failed to load document analysis', 'error');
    }
}

function showLoadingState() {
    const loadingElement = document.getElementById('loading-state');
    const headerElement = document.getElementById('document-header');
    const summaryElement = document.getElementById('document-summary');
    
    if (loadingElement) loadingElement.classList.remove('hidden');
    if (headerElement) headerElement.classList.add('hidden');
    if (summaryElement) summaryElement.classList.add('hidden');
}

function hideLoadingState() {
    const loadingElement = document.getElementById('loading-state');
    const headerElement = document.getElementById('document-header');
    const summaryElement = document.getElementById('document-summary');
    
    if (loadingElement) loadingElement.classList.add('hidden');
    if (headerElement) headerElement.classList.remove('hidden');
    if (summaryElement) summaryElement.classList.remove('hidden');
}

function showProcessingStatus(documentId) {
    const container = document.getElementById('clauses-container');
    if (container) {
        container.innerHTML = `
            <div style="text-align: center; padding: 3rem;">
                <div style="border: 4px solid #f3f4f6; border-top: 4px solid var(--primary-color); border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 0 auto 2rem;"></div>
                <h3 style="margin: 1rem 0; color: var(--primary-color);">Processing Document...</h3>
                <p>AI is analyzing your document. This may take a few minutes.</p>
                <button onclick="location.reload()" class="btn btn-primary" style="margin-top: 1rem;">
                    <i class="fas fa-sync-alt"></i> Check Status
                </button>
            </div>
        `;
    }
    
    // Auto-refresh every 15 seconds
    setTimeout(() => {
        location.reload();
    }, 15000);
}

function showFailedStatus(documentId) {
    const container = document.getElementById('clauses-container');
    if (container) {
        container.innerHTML = `
            <div style="text-align: center; padding: 3rem;">
                <i class="fas fa-exclamation-triangle" style="font-size: 3rem; color: var(--danger-color); margin-bottom: 1rem;"></i>
                <h3 style="margin: 1rem 0; color: var(--danger-color);">Processing Failed</h3>
                <p>There was an error processing this document. Please try uploading again.</p>
                <div style="margin-top: 1rem; display: flex; gap: 1rem; justify-content: center;">
                    <button onclick="retryProcessing('${documentId}')" class="btn btn-primary">
                        <i class="fas fa-redo"></i> Retry Processing
                    </button>
                    <button onclick="deleteCurrentDocument()" class="btn btn-danger">
                        <i class="fas fa-trash"></i> Delete Document
                    </button>
                </div>
            </div>
        `;
    }
}

function showNoClausesMessage() {
    const container = document.getElementById('clauses-container');
    if (container) {
        container.innerHTML = `
            <div style="text-align: center; padding: 3rem;">
                <i class="fas fa-file-alt" style="font-size: 3rem; color: var(--text-secondary); opacity: 0.5; margin-bottom: 1rem;"></i>
                <h3 style="margin: 1rem 0;">No Content Found</h3>
                <p>The document may not contain analyzable text or there might be an issue with text extraction.</p>
                <button onclick="location.reload()" class="btn btn-primary" style="margin-top: 1rem;">
                    <i class="fas fa-sync-alt"></i> Refresh
                </button>
            </div>
        `;
    }
}
async function openCalendarView() {
    try {
        // Get dashboard data for deadlines
        const response = await apiCall('/documents/dashboard');
        const deadlines = response.upcoming_deadlines || [];
        
        // Create calendar modal with actual calendar grid
        const modal = document.createElement('div');
        modal.className = 'calendar-modal';
        modal.innerHTML = createCalendarHTML(deadlines);
        
        document.body.appendChild(modal);
        
    } catch (error) {
        showToast('Failed to load calendar data', 'error');
        console.error('Calendar error:', error);
    }
}

function createCalendarHTML(deadlines) {
    const now = new Date();
    const currentMonth = now.getMonth();
    const currentYear = now.getFullYear();
    const today = now.getDate();
    
    // Get first day of month and number of days
    const firstDay = new Date(currentYear, currentMonth, 1);
    const lastDay = new Date(currentYear, currentMonth + 1, 0);
    const startingDayOfWeek = firstDay.getDay();
    const daysInMonth = lastDay.getDate();
    
    // Month names
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'];
    
    // Create calendar grid
    let calendarHTML = `
        <div class="modal-content" style="max-width: 800px; width: 90vw;">
            <div class="calendar-header">
                <h3>${monthNames[currentMonth]} ${currentYear} - Document Deadlines</h3>
                <button class="modal-close" onclick="closeCalendarModal()">&times;</button>
            </div>
            <div class="calendar-body">
                <div class="calendar-grid">
                    <div class="calendar-day-header">Sun</div>
                    <div class="calendar-day-header">Mon</div>
                    <div class="calendar-day-header">Tue</div>
                    <div class="calendar-day-header">Wed</div>
                    <div class="calendar-day-header">Thu</div>
                    <div class="calendar-day-header">Fri</div>
                    <div class="calendar-day-header">Sat</div>
    `;
    
    // Add empty cells for days before month starts
    for (let i = 0; i < startingDayOfWeek; i++) {
        calendarHTML += `<div class="calendar-day other-month"></div>`;
    }
    
    // Add days of the month
    for (let day = 1; day <= daysInMonth; day++) {
        const isToday = day === today;
        const dayDeadlines = getDayDeadlines(deadlines, day, currentMonth, currentYear);
        
        calendarHTML += `
            <div class="calendar-day ${isToday ? 'today' : ''}" onclick="showDayDeadlines(${day}, ${currentMonth}, ${currentYear})">
                <div class="calendar-day-number">${day}</div>
                ${dayDeadlines.map(deadline => `
                    <div class="deadline-marker ${getDeadlineUrgency(deadline.deadline)}" title="${deadline.deadline}">
                        ${deadline.deadline.substring(0, 12)}${deadline.deadline.length > 12 ? '...' : ''}
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    calendarHTML += `
                </div>
                <div class="calendar-legend">
                    <div class="legend-item">
                        <div class="legend-color" style="background: var(--success-color);"></div>
                        <span>Low Priority</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: var(--warning-color);"></div>
                        <span>Medium Priority</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: var(--danger-color);"></div>
                        <span>High Priority</span>
                    </div>
                </div>
            </div>
        </div>
        <div class="deadlines-sidebar" style="width: 300px; background: var(--bg-secondary); padding: 1rem; border-left: 1px solid var(--border-light); overflow-y: auto; max-height: 70vh;">
            <h4>All Deadlines</h4>
            <div class="deadline-list">
                ${deadlines.map(deadline => `
                    <div class="deadline-item" style="padding: 0.75rem; border-bottom: 1px solid var(--border-light); margin-bottom: 0.5rem;">
                        <div class="deadline-text" style="font-weight: 600; color: var(--primary-color); margin-bottom: 0.5rem;">${deadline.deadline}</div>
                        <div class="deadline-description" style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 0.25rem;">${deadline.description}</div>
                        <div class="deadline-document" style="font-size: 0.8rem; color: var(--text-muted);">${deadline.document_name}</div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
    
    return calendarHTML;
}

function getDayDeadlines(deadlines, day, month, year) {
    // Better distribution logic - each deadline should appear on only one day
    return deadlines.filter((deadline, index) => {
        // Distribute deadlines across the month based on their index and content
        let targetDay;
        
        if (deadline.deadline.includes('15 days')) {
            targetDay = 5 + (index % 3); // Days 5, 6, 7
        } else if (deadline.deadline.includes('10 days')) {
            targetDay = 8 + (index % 3); // Days 8, 9, 10
        } else if (deadline.deadline.includes('30 days')) {
            targetDay = 15 + (index % 5); // Days 15-19
        } else if (deadline.deadline.includes('60 days')) {
            targetDay = 22 + (index % 5); // Days 22-26
        } else {
            targetDay = 12 + (index % 8); // Days 12-19 for others
        }
        
        return day === targetDay;
    });
}

function getDeadlineUrgency(deadlineText) {
    const text = deadlineText.toLowerCase();
    if (text.includes('15 days') || text.includes('10 days')) return 'high-urgency';
    if (text.includes('30 days')) return 'medium-urgency';
    return 'low-urgency';
}

function showDayDeadlines(day, month, year) {
    // You can implement a detailed view for a specific day here
    console.log(`Show deadlines for ${day}/${month + 1}/${year}`);
}

function closeCalendarModal() {
    const modal = document.querySelector('.calendar-modal');
    if (modal) {
        document.body.removeChild(modal);
    }
}

// Enhanced CSS for the proper calendar
const enhancedCalendarStyle = document.createElement('style');
enhancedCalendarStyle.textContent = `
    .calendar-modal .modal-content {
        display: flex;
        max-height: 90vh;
        overflow: hidden;
    }
    
    .calendar-body {
        flex: 2;
        padding: 1rem;
    }
    
    .deadlines-sidebar {
        flex: 1;
        background: var(--bg-secondary);
        padding: 1rem;
        border-left: 1px solid var(--border-light);
        overflow-y: auto;
    }
    
    .deadlines-sidebar h4 {
        margin: 0 0 1rem 0;
        color: var(--text-primary);
    }
    
    .calendar-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 1px;
        background: var(--border-light);
        border: 1px solid var(--border-light);
        border-radius: var(--radius);
        overflow: hidden;
    }
    
    .calendar-day-header {
        background: var(--bg-secondary);
        padding: 0.75rem 0.5rem;
        text-align: center;
        font-weight: 600;
        font-size: 0.9rem;
        color: var(--text-secondary);
    }
    
    .calendar-day {
        background: var(--bg-primary);
        min-height: 80px;
        padding: 0.5rem;
        cursor: pointer;
        transition: var(--transition);
        display: flex;
        flex-direction: column;
    }
    
    .calendar-day:hover {
        background: var(--bg-tertiary);
    }
    
    .calendar-day.other-month {
        background: var(--bg-secondary);
        opacity: 0.5;
    }
    
    .calendar-day.today {
        background: var(--primary-color);
        color: white;
    }
    
    .calendar-day.today:hover {
        background: var(--primary-dark);
    }
    
    .calendar-day-number {
        font-weight: 600;
        margin-bottom: 0.25rem;
        font-size: 0.9rem;
    }
    
    .deadline-marker {
        font-size: 0.7rem;
        padding: 0.15rem 0.3rem;
        border-radius: var(--radius-sm);
        margin-bottom: 0.15rem;
        color: white;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    
    .deadline-marker.high-urgency {
        background: var(--danger-color);
    }
    
    .deadline-marker.medium-urgency {
        background: var(--warning-color);
    }
    
    .deadline-marker.low-urgency {
        background: var(--success-color);
    }
    
    .calendar-legend {
        display: flex;
        gap: 1rem;
        padding: 1rem;
        background: var(--bg-secondary);
        border-radius: var(--radius);
        margin-top: 1rem;
        justify-content: center;
    }
    
    .legend-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.9rem;
    }
    
    .legend-color {
        width: 12px;
        height: 12px;
        border-radius: var(--radius-sm);
    }
    
    @media (max-width: 768px) {
        .calendar-modal .modal-content {
            flex-direction: column;
            max-height: 95vh;
        }
        
        .deadlines-sidebar {
            border-left: none;
            border-top: 1px solid var(--border-light);
            max-height: 200px;
        }
        
        .calendar-day {
            min-height: 60px;
        }
        
        .deadline-marker {
            font-size: 0.6rem;
            padding: 0.1rem 0.2rem;
        }
    }
`;

document.head.appendChild(enhancedCalendarStyle);
function renderDocumentAnalysis(documentData) {
    console.log('Rendering document analysis:', documentData);
    
    // Update header
    const titleElement = document.getElementById('document-title');
    const typeElement = document.getElementById('document-type');
    const statusElement = document.getElementById('document-status');
    const riskElement = document.getElementById('risk-score');
    
    if (titleElement) titleElement.textContent = documentData.filename;
    if (typeElement) {
        typeElement.textContent = documentData.document_type || 'Unknown Type';
        typeElement.className = `status-badge status-completed`;
    }
    if (statusElement) {
        statusElement.textContent = documentData.status;
        statusElement.className = `status-badge status-${documentData.status}`;
    }
    
    if (riskElement && documentData.risk_score !== null) {
        const riskLevel = getRiskLevel(documentData.risk_score);
        riskElement.textContent = `Risk: ${documentData.risk_score}/100`;
        riskElement.className = `risk-indicator risk-${riskLevel}`;
    }
    
    // Update summary
    const summaryContent = document.getElementById('summary-content');
    if (summaryContent && documentData.summary) {
        summaryContent.innerHTML = `<p>${documentData.summary}</p>`;
    }
    
    // Render clauses
    renderClauses(documentData.clauses || []);
    
    // Update quick stats
    updateQuickStats(documentData);
}
function updateQuickStats(documentData) {
    const clauses = documentData.clauses || [];
    
    const totalElement = document.getElementById('total-clauses');
    const highRiskElement = document.getElementById('high-risk-count');
    const deadlineElement = document.getElementById('deadline-count');
    const obligationElement = document.getElementById('obligation-count');
    
    if (totalElement) totalElement.textContent = clauses.length;
    if (highRiskElement) highRiskElement.textContent = clauses.filter(c => c.risk_level === 'high').length;
    if (deadlineElement) deadlineElement.textContent = clauses.filter(c => c.clause_type === 'deadline' || (c.deadlines && c.deadlines.length > 0)).length;
    if (obligationElement) obligationElement.textContent = clauses.filter(c => c.clause_type === 'obligation' || (c.obligations && c.obligations.length > 0)).length;
}

// Add CSS animation for spinner
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);

// function renderDocumentAnalysis(document) {
//     // This would be implemented in the document analysis template
//     console.log('Document analysis:', document);
// }
function renderClauses(clauses) {
    console.log('Rendering clauses:', clauses);
    const container = document.getElementById('clauses-container');
    
    if (!clauses || clauses.length === 0) {
        console.log('No clauses found');
        showNoClausesMessage();
        return;
    }
    
    container.innerHTML = clauses.map((clause, index) => `
        <div class="clause-container" data-type="${clause.clause_type}" data-risk="${clause.risk_level}" style="margin-bottom: 1rem; border: 1px solid var(--border-color); border-radius: var(--radius); overflow: hidden;">
            <div class="clause-header" onclick="toggleClause(this)" style="padding: 1rem; background: var(--bg-secondary); cursor: pointer; border-bottom: 1px solid var(--border-color);">
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div style="display: flex; align-items: center; gap: 1rem;">
                        <span class="clause-type" style="padding: 0.25rem 0.5rem; border-radius: var(--radius); background: ${getClauseColor(clause.clause_type)}20; color: ${getClauseColor(clause.clause_type)}; font-size: 0.8rem; font-weight: 600;">
                            <i class="fas fa-${getClauseIcon(clause.clause_type)}"></i>
                            ${clause.clause_type.toUpperCase()}
                        </span>
                        <span style="font-size: 0.9rem; color: var(--text-secondary);">Section ${clause.section_number}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span class="risk-indicator risk-${clause.risk_level}" style="padding: 0.25rem 0.5rem; border-radius: var(--radius); font-size: 0.8rem; font-weight: 600; background: ${getRiskColor(clause.risk_level)}20; color: ${getRiskColor(clause.risk_level)};">${clause.risk_level.toUpperCase()} RISK</span>
                        <i class="fas fa-chevron-down" style="transition: transform 0.2s; color: var(--text-secondary);"></i>
                    </div>
                </div>
            </div>
            <div class="clause-body" style="padding: 1rem; display: block;">
                <div class="clause-text" style="line-height: 1.6; margin-bottom: 1rem;">${clause.simplified_text}</div>
                <!-- Original text hidden in UI; showing only simplified_text -->
                ${clause.deadlines && clause.deadlines.length > 0 ? `
                    <div style="margin-bottom: 1rem; padding: 1rem; background: rgb(245 158 11 / 0.1); border-radius: var(--radius); border-left: 4px solid var(--warning-color);">
                        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                            <i class="fas fa-clock" style="color: var(--warning-color);"></i>
                            <strong style="color: var(--warning-color);">Important Deadlines:</strong>
                        </div>
                        <ul style="margin: 0; padding-left: 1rem;">
                            ${clause.deadlines.map(deadline => `<li style="margin-bottom: 0.25rem;">${deadline}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
                ${clause.obligations && clause.obligations.length > 0 ? `
                    <div style="margin-bottom: 1rem; padding: 1rem; background: rgb(16 185 129 / 0.1); border-radius: var(--radius); border-left: 4px solid var(--accent-color);">
                        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                            <i class="fas fa-tasks" style="color: var(--accent-color);"></i>
                            <strong style="color: var(--accent-color);">Your Obligations:</strong>
                        </div>
                        <ul style="margin: 0; padding-left: 1rem;">
                            ${clause.obligations.map(obligation => `<li style="margin-bottom: 0.25rem;">${obligation}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
                ${clause.advice ? `
                    <div style="padding: 1rem; background: rgb(59 130 246 / 0.1); border-radius: var(--radius); border-left: 4px solid var(--primary-color);">
                        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                            <i class="fas fa-lightbulb" style="color: var(--primary-color);"></i>
                            <strong style="color: var(--primary-color);">AI Advice:</strong>
                        </div>
                        <p style="margin: 0; font-size: 0.9rem;">${clause.advice}</p>
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
}

// Helper functions for styling
function getClauseIcon(type) {
    const icons = {
        obligation: 'tasks',
        right: 'shield-alt',
        risk: 'exclamation-triangle',
        penalty: 'gavel',
        deadline: 'clock',
        general: 'file-alt'
    };
    return icons[type] || 'file-alt';
}

function getClauseColor(type) {
    const colors = {
        obligation: '#10b981',
        right: '#3b82f6',
        risk: '#ef4444',
        penalty: '#dc2626',
        deadline: '#f59e0b',
        general: '#6b7280'
    };
    return colors[type] || '#6b7280';
}

function getRiskColor(level) {
    const colors = {
        low: '#10b981',
        medium: '#f59e0b',
        high: '#ef4444'
    };
    return colors[level] || '#6b7280';
}

function toggleClause(header) {
    const container = header.parentElement;
    const body = container.querySelector('.clause-body');
    const icon = header.querySelector('.fa-chevron-down');
    
    if (body.style.display === 'none') {
        body.style.display = 'block';
        icon.style.transform = 'rotate(0deg)';
    } else {
        body.style.display = 'none';
        icon.style.transform = 'rotate(-90deg)';
    }
}
function renderQASuggestions(suggestions, documentId) {
    const container = document.getElementById('qa-suggestions');
    if (!container || !suggestions.length) return;
    
    container.innerHTML = suggestions.map(suggestion => `
        <button class="btn btn-sm btn-secondary" onclick="askQuestionFromSuggestion('${suggestion}', '${documentId}')">
            ${suggestion}
        </button>
    `).join('');
}

async function askQuestionFromSuggestion(question, documentId) {
    const qaInput = document.getElementById('qa-input');
    if (qaInput) {
        qaInput.value = question;
        await submitQuestion(documentId);
    }
}

// In submitQuestion function
async function submitQuestion(documentId) {
    const qaInput = document.getElementById('qa-input');
    const question = qaInput.value.trim();
    
    if (!question) return;
    
    console.log('Submitting question:', question, 'for document:', documentId); // Debug log
    
    try {
        const response = await askQuestion(question, documentId);
        console.log('QA Response:', response); // Debug log
        if (response.conversation_id) {
            currentConversationId = response.conversation_id;
        }
        displayQAResponse(question, response);
        qaInput.value = '';
        
    } catch (error) {
        console.error('Question failed:', error);
        showToast('Failed to get answer: ' + error.message, 'error');
    }
}

function displayQAResponse(question, response) {
    const messagesContainer = document.getElementById('qa-messages');
    if (!messagesContainer) return;
    
    const messageHtml = `
        <div class="qa-message question">
            <strong>You:</strong> ${question}
        </div>
        <div class="qa-message answer">
            <strong>AI Assistant:</strong> ${response.answer}
            ${response.sources && response.sources.length > 0 ? `
                <div style="margin-top: 1rem; font-size: 0.9rem; color: var(--text-secondary);">
                    <strong>Sources:</strong> Sections ${response.sources.map(s => s.section).join(', ')}
                </div>
            ` : ''}
        </div>
    `;
    
    messagesContainer.insertAdjacentHTML('beforeend', messageHtml);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Export functions for global access
window.App = App;
window.showToast = showToast;
window.logout = logout;
window.showProfile = showProfile;
window.hideProfile = hideProfile;
window.deleteDocument = deleteDocument;
window.viewDocument = viewDocument;
window.downloadDocument = downloadDocument;