/**
 * G&C Central Deal and Brokerage Automation Platform
 * Luxury Login Page & Authentication Component
 */
const LoginPageComponent = {
  render(container) {
    container.innerHTML = `
      <div class="login-page-wrapper animate-fade-in">
        <div class="login-card">
          
          <!-- Brand Crest & Header -->
          <div class="login-crest-header">
            <div class="login-crest-icon">G&C</div>
            <h1 class="login-title">GANESH & <span>COMPANY</span></h1>
            <p class="login-subtitle">
              Central Deal, Multi-Link Resale Margins & Dual-Party Brokerage Platform
            </p>
          </div>

          <!-- Alert Container for Errors -->
          <div id="login-error-box" style="display: none; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); color: #fca5a5; padding: 10px 14px; border-radius: var(--radius-md); font-size: 0.8125rem; margin-bottom: 18px;">
          </div>

          <!-- Login Form -->
          <form id="login-form" onsubmit="LoginPageComponent.handleLogin(event)">
            
            <!-- Username Input -->
            <div class="login-input-group">
              <label class="form-label" style="font-size: 0.75rem;">Username or Email</label>
              <span class="login-input-icon">👤</span>
              <input 
                type="text" 
                id="login-username" 
                class="form-control login-input-with-icon font-mono" 
                placeholder="e.g. admin" 
                value="admin"
                required 
                autocomplete="username"
              >
            </div>

            <!-- Password Input -->
            <div class="login-input-group">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <label class="form-label" style="font-size: 0.75rem; margin-bottom: 4px;">Password</label>
              </div>
              <span class="login-input-icon">🔒</span>
              <input 
                type="password" 
                id="login-password" 
                class="form-control login-input-with-icon font-mono" 
                placeholder="Enter password" 
                value="admin123"
                required 
                autocomplete="current-password"
              >
              <button 
                type="button" 
                class="password-toggle-btn" 
                onclick="LoginPageComponent.togglePasswordVisibility()" 
                title="Toggle password visibility"
              >
                <span id="password-toggle-icon">👁️</span>
              </button>
            </div>

            <!-- Remember Me & Forgot Links -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; font-size: 0.75rem;">
              <label style="display: flex; align-items: center; gap: 6px; cursor: pointer; color: var(--text-secondary);">
                <input type="checkbox" id="login-remember" checked>
                <span>Remember session on this device</span>
              </label>
            </div>

            <!-- Submit Button -->
            <button 
              type="submit" 
              id="btn-login-submit" 
              class="btn btn-primary btn-lg glow-gold" 
              style="width: 100%; justify-content: center; font-size: 0.9375rem; font-weight: 700; padding: 12px;"
            >
              <span>🔑</span> Sign In to G&C Platform
            </button>
          </form>

          <!-- 1-Click Quick Demo Profiles -->
          <div class="demo-users-section">
            <div class="demo-users-title">
              <span>⚡ 1-Click Demo Profiles</span>
              <span style="font-size: 0.65rem; color: var(--text-muted); font-weight: normal;">Click to Quick-Fill</span>
            </div>

            <div class="demo-user-grid">
              <div class="demo-chip" onclick="LoginPageComponent.fillCredentials('admin', 'admin123')">
                <div class="demo-chip-role">
                  <span>👑</span> Administrator
                </div>
                <div class="demo-chip-user">user: admin (Full Control)</div>
              </div>

              <div class="demo-chip" onclick="LoginPageComponent.fillCredentials('broker', 'broker123')">
                <div class="demo-chip-role">
                  <span>📈</span> Senior Broker
                </div>
                <div class="demo-chip-user">user: broker (Deals & Resale)</div>
              </div>

              <div class="demo-chip" onclick="LoginPageComponent.fillCredentials('accounts', 'accounts123')">
                <div class="demo-chip-role">
                  <span>💳</span> Accounts Head
                </div>
                <div class="demo-chip-user">user: accounts (Billing & Ledger)</div>
              </div>

              <div class="demo-chip" onclick="LoginPageComponent.fillCredentials('viewer', 'viewer123')">
                <div class="demo-chip-role">
                  <span>👁️</span> Auditor / Viewer
                </div>
                <div class="demo-chip-user">user: viewer (Read-Only)</div>
              </div>
            </div>
          </div>

          <!-- Security Badge Footer -->
          <div class="login-security-badge">
            <span>🔒</span>
            <span>256-bit Salted Authentication | Role-Based Access Control</span>
          </div>

        </div>
      </div>
    `;
  },

  fillCredentials(username, password) {
    const userField = document.getElementById('login-username');
    const passField = document.getElementById('login-password');
    if (userField) userField.value = username;
    if (passField) passField.value = password;
    
    // Animate submit button slightly to prompt user or auto-submit
    const btn = document.getElementById('btn-login-submit');
    if (btn) {
      btn.classList.add('glow-gold');
      Store.showToast(`Selected demo profile: ${username.toUpperCase()}`, 'info');
    }
  },

  togglePasswordVisibility() {
    const passField = document.getElementById('login-password');
    const toggleIcon = document.getElementById('password-toggle-icon');
    if (!passField) return;

    if (passField.type === 'password') {
      passField.type = 'text';
      if (toggleIcon) toggleIcon.innerText = '🙈';
    } else {
      passField.type = 'password';
      if (toggleIcon) toggleIcon.innerText = '👁️';
    }
  },

  async handleLogin(event) {
    if (event) event.preventDefault();

    const username = document.getElementById('login-username')?.value?.trim();
    const password = document.getElementById('login-password')?.value;
    const errorBox = document.getElementById('login-error-box');
    const btn = document.getElementById('btn-login-submit');

    if (!username || !password) {
      if (errorBox) {
        errorBox.style.display = 'block';
        errorBox.innerText = 'Please enter both username and password.';
      }
      return;
    }

    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="loading-spinner"></span> Authenticating...';
    }

    if (errorBox) {
      errorBox.style.display = 'none';
      errorBox.innerText = '';
    }

    try {
      const res = await API.login(username, password);
      if (res && res.success && res.session) {
        const session = res.session;
        Store.setAuth({
          user_id: session.user_id,
          username: session.username,
          full_name: session.full_name,
          role: session.role
        }, session.token);

        Store.showToast(`Welcome back, ${session.full_name}!`, 'success');
        
        // Transition to main workspace
        App.onLoginSuccess();
      } else {
        throw new Error((res && res.error) || 'Invalid username or password.');
      }
    } catch (err) {
      console.error('Login error:', err);
      if (errorBox) {
        errorBox.style.display = 'block';
        errorBox.innerText = err.message || 'Authentication failed. Please check your credentials.';
      }
      Store.showToast(err.message || 'Authentication failed', 'error');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<span>🔑</span> Sign In to G&C Platform';
      }
    }
  }
};

window.LoginPageComponent = LoginPageComponent;
