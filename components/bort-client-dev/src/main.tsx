import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import App from '@/app/App';

import { assertHasValue } from '@/shared/lib/assert-has-value';

const rootElement = document.getElementById('root');

assertHasValue(rootElement, 'DOM root element not found');

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
