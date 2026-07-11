import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { WorkspacePanelTabs } from './WorkspacePanelTabs';

describe('WorkspacePanelTabs', () => {
  it('uses Chinese labels and changes the active panel', () => {
    const onChange = vi.fn();
    render(<WorkspacePanelTabs value="ai" onChange={onChange} />);

    expect(screen.getByRole('button', { name: 'AI 写作' })).toHaveClass(
      'bg-slate-900',
    );
    fireEvent.click(screen.getByRole('button', { name: '审查' }));

    expect(onChange).toHaveBeenCalledWith('review');
  });
});
