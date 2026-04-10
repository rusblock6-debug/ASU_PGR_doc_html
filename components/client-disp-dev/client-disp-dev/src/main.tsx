import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import App from '@/app/App';

import { assertHasValue } from '@/shared/lib/assert-has-value';

async function enableMocking() {
  // MSW включается только если явно указано VITE_ENABLE_MSW=true
  if (import.meta.env.VITE_ENABLE_MSW !== 'true') {
    return;
  }

  const { worker } = await import('@/shared/lib/msw');

  return worker.start({
    onUnhandledRequest: 'bypass', // Пропускать запросы без обработчиков
  });
}

enableMocking().then(() => {
  const rootElement = document.getElementById('root');

  assertHasValue(rootElement, 'DOM root element not found');

  createRoot(rootElement).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
});
