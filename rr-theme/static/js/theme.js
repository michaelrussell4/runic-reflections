/**
 * Theme Toggle Logic
 * Handles switching between light and dark modes with localStorage persistence
 * and system preference fallback
 */

(function() {
  const THEME_KEY = 'theme-preference';
  const DARK_CLASS = 'dark';
  const LIGHT_CLASS = 'light';

  /**
   * Initialize theme on page load
   * 1. Check localStorage for saved preference
   * 2. Fall back to system preference (prefers-color-scheme)
   * 3. Default to light mode
   */
  function initializeTheme() {
    const savedTheme = localStorage.getItem(THEME_KEY);
    const html = document.documentElement;

    if (savedTheme) {
      // Use saved preference
      if (savedTheme === 'dark') {
        html.classList.add(DARK_CLASS);
        html.classList.remove(LIGHT_CLASS);
      } else {
        html.classList.remove(DARK_CLASS);
        html.classList.add(LIGHT_CLASS);
      }
    } else {
      // Use system preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      if (prefersDark) {
        html.classList.add(DARK_CLASS);
        html.classList.remove(LIGHT_CLASS);
      } else {
        html.classList.remove(DARK_CLASS);
        html.classList.add(LIGHT_CLASS);
      }
    }

    updateToggleButton();
  }

  /**
   * Toggle between light and dark mode
   */
  function toggleTheme() {
    const html = document.documentElement;
    const isDark = html.classList.contains(DARK_CLASS);

    if (isDark) {
      // Switch to light
      html.classList.remove(DARK_CLASS);
      html.classList.add(LIGHT_CLASS);
      localStorage.setItem(THEME_KEY, 'light');
    } else {
      // Switch to dark
      html.classList.add(DARK_CLASS);
      html.classList.remove(LIGHT_CLASS);
      localStorage.setItem(THEME_KEY, 'dark');
    }

    updateToggleButton();
    
    // Dispatch custom event for other listeners
    window.dispatchEvent(new CustomEvent('themechange', {
      detail: { theme: isDark ? 'light' : 'dark' }
    }));
  }

  /**
   * Update toggle button icon to reflect current theme
   */
  function updateToggleButton() {
    const button = document.getElementById('theme-toggle');
    if (!button) return;

    const isDark = document.documentElement.classList.contains(DARK_CLASS);
    const sunIcon = button.querySelector('.sun-icon');
    const moonIcon = button.querySelector('.moon-icon');

    if (sunIcon && moonIcon) {
      if (isDark) {
        sunIcon.classList.remove('hidden');
        moonIcon.classList.add('hidden');
      } else {
        sunIcon.classList.add('hidden');
        moonIcon.classList.remove('hidden');
      }
    }
  }

  /**
   * Listen for system preference changes
   * Only update if user hasn't explicitly set a preference
   */
  function initializeSystemPreferenceListener() {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    // Handle browser compatibility for addEventListener
    const handleChange = (e) => {
      const savedTheme = localStorage.getItem(THEME_KEY);
      
      // Only update if user hasn't set explicit preference
      if (!savedTheme) {
        const html = document.documentElement;
        if (e.matches) {
          html.classList.add(DARK_CLASS);
          html.classList.remove(LIGHT_CLASS);
        } else {
          html.classList.remove(DARK_CLASS);
          html.classList.add(LIGHT_CLASS);
        }
        updateToggleButton();
      }
    };

    // Modern API
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
    } else if (mediaQuery.addListener) {
      // Fallback for older browsers
      mediaQuery.addListener(handleChange);
    }
  }

  /**
   * Attach toggle button click handler
   */
  function initializeToggleButton() {
    const button = document.getElementById('theme-toggle');
    if (button) {
      button.addEventListener('click', toggleTheme);
    }
  }

  /**
   * Initialize all theme functionality when DOM is ready
   */
  function init() {
    // 1. Run theme initialization immediately to apply class to <html> tag.
    // This blocks parser execution momentarily to prevent Flash of Unstyled Content (FOUC).
    initializeTheme();

    // 2. Initialize DOM-dependent controls when DOM is ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function() {
        updateToggleButton(); // Ensure button icon is properly updated once DOM exists
        initializeToggleButton();
        initializeSystemPreferenceListener();
      });
    } else {
      updateToggleButton();
      initializeToggleButton();
      initializeSystemPreferenceListener();
    }
  }

  // Make toggleTheme available globally for onclick handlers
  window.toggleTheme = toggleTheme;

  // Start initialization
  init();
})();
