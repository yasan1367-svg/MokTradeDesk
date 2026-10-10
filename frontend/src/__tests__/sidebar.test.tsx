import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import Sidebar from '../components/Sidebar';

describe('Sidebar navigation', () => {
  it('preserves all destinations and highlights a secondary page', () => {
    const onNavigate = vi.fn();
    const { container } = render(<Sidebar currentPage="strategy" onNavigate={onNavigate} />);
    expect(container.querySelector('.sidebar-more')).toHaveAttribute('open');
    expect(screen.getByRole('button', { name: 'استراتژی' })).toHaveAttribute('aria-current', 'page');
    for (const [label, page] of [['معاملات', 'trades'], ['برداشت‌ها', 'payouts'], ['مدیریت ریسک', 'risk'], ['واردات', 'import']]) {
      fireEvent.click(screen.getByRole('button', { name: label }));
      expect(onNavigate).toHaveBeenLastCalledWith(page);
    }
  });

  it('closes the mobile drawer after navigating', () => {
    const onNavigate = vi.fn();
    render(<Sidebar currentPage="dashboard" onNavigate={onNavigate} />);
    fireEvent.click(screen.getByRole('button', { name: 'منو', exact: true }));
    const drawer = screen.getByLabelText('منوی ناوبری');
    fireEvent.click(within(drawer).getByRole('button', { name: 'مالی', exact: true }));
    expect(onNavigate).toHaveBeenCalledWith('finance');
    expect(screen.queryByLabelText('منوی ناوبری')).not.toBeInTheDocument();
  });
});
