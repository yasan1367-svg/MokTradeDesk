import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { parse } from 'postcss';
import { readFileSync } from 'node:fs';
import Sidebar from '../components/Sidebar';
import KpiCard from '../components/ui/KpiCard';
import { applyFontSize } from '../utils/theme';

// Read the actual stylesheet; Vitest stubs CSS imports in this configuration.
const css = parse(readFileSync('src/index.css', 'utf8'));
const initialFontSize = document.documentElement.style.fontSize;
const initialClassName = document.documentElement.className;

afterEach(() => {
  document.documentElement.style.fontSize = initialFontSize;
  document.documentElement.className = initialClassName;
});

describe('Sidebar font settings', () => {
  it('uses scalable font sizes throughout the sidebar after changing the setting', () => {
    const { container } = render(<Sidebar currentPage="dashboard" onNavigate={vi.fn()} />);
    for (const fontSize of [13, 18]) {
      applyFontSize(fontSize);
      expect(document.documentElement.style.fontSize).toBe(`${fontSize}px`);
    }
    css.walkRules(rule => {
      if (!rule.selector.includes('sidebar')) return;
      rule.walkDecls('font-size', declaration => {
        expect(declaration.value).toMatch(/^(inherit|[\d.]+(?:rem|em))$/);
      });
    });
    for (const element of container.querySelectorAll('.app-sidebar, .app-sidebar *')) {
      expect(element.className.toString()).not.toMatch(/text-\[[\d.]+px\]/);
    }
    const sidebarRule = css.nodes.find(node => node.type === 'rule' && node.selector === '.app-sidebar');
    expect(sidebarRule?.toString()).toContain('font-size: 1rem');
  });

  it('defines every sidebar class used for its layout and appearance', () => {
    const selectors = new Set<string>();
    css.walkRules(rule => { selectors.add(rule.selector); });
    for (const name of ['app-sidebar', 'sidebar-item', 'sidebar-brand', 'sidebar-group-label', 'sidebar-more', 'sidebar-avatar', 'sidebar-profile']) {
      expect(selectors.has(`.${name}`)).toBe(true);
    }
  });
});

describe.each(['light', 'dark'])('KPI colors in %s mode', theme => {
  it.each(['profit', 'loss', 'neutral', 'accent', 'purple', 'warning'] as const)(
    'uses the %s theme token for both the value and top border', valueColor => {
      document.documentElement.classList.toggle('dark', theme === 'dark');
      const { container } = render(<KpiCard icon={null} label="Profit factor" value="1.82" valueColor={valueColor} />);
      const variable = `--kpi-${valueColor}-tone`;
      expect(screen.getByText('1.82').style.color).toBe(`var(${variable})`);
      const card = container.querySelector('.kpi-card') as HTMLElement;
      expect(card.style.borderTopColor).toBe(`var(${variable})`);
      expect(card.style.borderTopStyle).toBe('solid');
      expect(card.style.borderTopWidth).toBe('2px');
      const themeRule = css.nodes.find(node => node.type === 'rule' && node.selector === (theme === 'dark' ? '.dark' : ':root'));
      expect(themeRule?.toString()).toContain(`${variable}:`);
      if (theme === 'dark' && valueColor === 'purple') {
        expect(themeRule?.toString()).toContain('--kpi-purple-tone: #C084FC');
      }
    },
  );
});
