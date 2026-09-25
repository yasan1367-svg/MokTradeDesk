import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import Badge from '../components/ui/Badge';
import ProgressBar from '../components/ui/ProgressBar';
import { Card, CardHeader } from '../components/ui/Card';

describe('Badge', () => {
  it('متن را نمایش می‌دهد', () => {
    render(<Badge variant="success">سود</Badge>);
    expect(screen.getByText('سود')).toBeInTheDocument();
  });

  it('کلاس variant درست را اعمال می‌کند', () => {
    render(<Badge variant="danger">ضرر</Badge>);
    expect(screen.getByText('ضرر').className).toContain('E45D72');
  });
});

describe('ProgressBar', () => {
  it('عرض را حداکثر تا ۱۰۰٪ محدود می‌کند', () => {
    const { container } = render(<ProgressBar value={150} />);
    const bar = container.querySelector('.h-full') as HTMLElement;
    expect(bar).not.toBeNull();
    expect(bar.style.width).toBe('100%');
  });

  it('عرض مقدار عادی را درست تنظیم می‌کند', () => {
    const { container } = render(<ProgressBar value={42} variant="profit" />);
    const bar = container.querySelector('.h-full') as HTMLElement;
    expect(bar.style.width).toBe('42%');
  });
});

describe('Card', () => {
  it('عنوان و زیرعنوان را در CardHeader نمایش می‌دهد', () => {
    render(
      <Card>
        <CardHeader title="عنوان تست" subtitle="زیرعنوان تست" />
      </Card>,
    );
    expect(screen.getByText('عنوان تست')).toBeInTheDocument();
    expect(screen.getByText('زیرعنوان تست')).toBeInTheDocument();
  });
});
