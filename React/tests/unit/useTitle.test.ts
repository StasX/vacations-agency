import { renderHook } from '@testing-library/react';
import { useTitle } from '../../src/Hooks/useTitle';

test('sets the document title and updates it when the title changes', () => {
    const previous = document.title;
    const { rerender, unmount } = renderHook(({ title }) => useTitle(title), { initialProps: { title: 'Home' } });
    expect(document.title).toBe('Home');
    rerender({ title: 'Statistics' });
    expect(document.title).toBe('Statistics');
    unmount();
    document.title = previous;
});
