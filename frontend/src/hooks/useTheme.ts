import { useEffect, useState } from 'react';

type Theme = 'light' | 'dark';

function getSystemTheme(): Theme {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function getStoredTheme(): Theme | null {
  const stored = localStorage.getItem('theme');
  return stored === 'light' || stored === 'dark' ? stored : null;
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => getStoredTheme() ?? getSystemTheme());

  // Apply the theme to the document root so CSS selectors can use [data-theme="dark"]
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  // Listen for system preference changes (only applies when no manual override is stored)
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    function handleChange() {
      if (!getStoredTheme()) {
        setTheme(getSystemTheme());
      }
    }
    mq.addEventListener('change', handleChange);
    return () => mq.removeEventListener('change', handleChange);
  }, []);

  function toggleTheme() {
    const next = theme === 'light' ? 'dark' : 'light';
    setTheme(next);
    localStorage.setItem('theme', next);
  }

  return { theme, toggleTheme };
}
