/**
 * Runic Reflections v2 - Theme & Reading Controls
 * Handles light/dark mode switching, system preference sync,
 * font-size adjustments, and mobile navigation.
 */

(function() {
  const THEME_KEY = 'theme-preference';
  const FONT_SIZE_KEY = 'reading-size-preference';
  const DARK_CLASS = 'dark';
  const LIGHT_CLASS = 'light';

  /**
   * Initialize theme on load
   */
  function initializeTheme() {
    const savedTheme = localStorage.getItem(THEME_KEY);
    const html = document.documentElement;

    if (savedTheme === 'dark') {
      html.classList.add(DARK_CLASS);
      html.classList.remove(LIGHT_CLASS);
    } else if (savedTheme === 'light') {
      html.classList.remove(DARK_CLASS);
      html.classList.add(LIGHT_CLASS);
    } else {
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
   * Toggle between light and dark
   */
  function toggleTheme() {
    const html = document.documentElement;
    const isDark = html.classList.contains(DARK_CLASS);

    if (isDark) {
      html.classList.remove(DARK_CLASS);
      html.classList.add(LIGHT_CLASS);
      localStorage.setItem(THEME_KEY, 'light');
    } else {
      html.classList.add(DARK_CLASS);
      html.classList.remove(LIGHT_CLASS);
      localStorage.setItem(THEME_KEY, 'dark');
    }

    updateToggleButton();

    window.dispatchEvent(new CustomEvent('themechange', {
      detail: { theme: isDark ? 'light' : 'dark' }
    }));
  }

  /**
   * Update theme toggle button state
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
        button.setAttribute('aria-label', 'Switch to light mode');
        button.setAttribute('title', 'Switch to light mode');
      } else {
        sunIcon.classList.add('hidden');
        moonIcon.classList.remove('hidden');
        button.setAttribute('aria-label', 'Switch to dark mode');
        button.setAttribute('title', 'Switch to dark mode');
      }
    }
  }

  /**
   * Reading Font Size Controls
   */
  const SIZES = ['reading-size-sm', 'reading-size-md', 'reading-size-lg'];
  const DEFAULT_SIZE_INDEX = 1; // md

  function initializeReadingSize() {
    const savedSize = localStorage.getItem(FONT_SIZE_KEY) || 'reading-size-md';
    const article = document.querySelector('article');
    if (article) {
      SIZES.forEach(s => article.classList.remove(s));
      article.classList.add(savedSize);
    }
  }

  function adjustReadingSize(delta) {
    const article = document.querySelector('article');
    if (!article) return;

    let currentIndex = SIZES.findIndex(s => article.classList.contains(s));
    if (currentIndex === -1) currentIndex = DEFAULT_SIZE_INDEX;

    let newIndex = currentIndex + delta;
    if (newIndex >= 0 && newIndex < SIZES.length) {
      SIZES.forEach(s => article.classList.remove(s));
      article.classList.add(SIZES[newIndex]);
      localStorage.setItem(FONT_SIZE_KEY, SIZES[newIndex]);
    }
  }

  /**
   * Mobile Menu & Scroll Handlers
   */
  function setupMobileMenu() {
    const toggleBtn = document.getElementById('mobile-menu-toggle');
    const menu = document.getElementById('nav-menu');
    if (toggleBtn && menu) {
      toggleBtn.addEventListener('click', function() {
        const isExpanded = this.getAttribute('aria-expanded') === 'true';
        this.setAttribute('aria-expanded', !isExpanded);
        menu.classList.toggle('hidden');
      });
    }
  }

  function setupSmartScrollHeader() {
    const header = document.getElementById('banner');
    if (!header) return;

    let lastScrollTop = window.pageYOffset || document.documentElement.scrollTop;

    window.addEventListener('scroll', function() {
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      if (scrollTop > lastScrollTop && scrollTop > 120) {
        // Scrolling down
        header.style.transform = 'translateY(-100%)';
      } else {
        // Scrolling up
        header.style.transform = 'translateY(0)';
      }
      lastScrollTop = scrollTop <= 0 ? 0 : scrollTop;
    }, { passive: true });

    document.addEventListener('mousemove', function(e) {
      if (e.clientY < 50) {
        header.style.transform = 'translateY(0)';
      }
    });
  }

  function setupSystemListener() {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (e) => {
      if (!localStorage.getItem(THEME_KEY)) {
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

    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handler);
    } else if (mediaQuery.addListener) {
      mediaQuery.addListener(handler);
    }
  }

  function init() {
    initializeTheme();

    const onReady = () => {
      updateToggleButton();
      const toggleBtn = document.getElementById('theme-toggle');
      if (toggleBtn) {
        toggleBtn.addEventListener('click', toggleTheme);
      }
      initializeReadingSize();
      setupMobileMenu();
      setupSmartScrollHeader();
      setupSystemListener();

      const fontDecBtn = document.getElementById('font-decrease-btn');
      const fontIncBtn = document.getElementById('font-increase-btn');
      if (fontDecBtn) fontDecBtn.addEventListener('click', () => adjustReadingSize(-1));
      if (fontIncBtn) fontIncBtn.addEventListener('click', () => adjustReadingSize(1));
    };

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', onReady);
    } else {
      onReady();
    }
  }

  window.toggleTheme = toggleTheme;
  window.adjustReadingSize = adjustReadingSize;

  init();
})();
