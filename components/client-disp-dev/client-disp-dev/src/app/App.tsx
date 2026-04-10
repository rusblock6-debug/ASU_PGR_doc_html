import { MantineProvider } from '@mantine/core';

import { FavoritePagesProvider } from '@/features/favorite-page';
import { PinnedPagesProvider } from '@/features/pin-page';

import { ConfirmProvider } from '@/shared/lib/confirm';
import { ToastProvider } from '@/shared/ui/Toast';

import { AppRouter } from './providers/router';
import { StoreProvider } from './providers/StoreProvider';
import { ThemeProvider } from './providers/ThemeProvider';
import { cssVariablesResolver, mantineTheme } from './theme/mantine-theme';

import './styles/main.css';

function App() {
  return (
    <StoreProvider>
      <ThemeProvider
        defaultTheme="dark"
        storageKey="asu-gtk-ui-theme"
      >
        <MantineProvider
          theme={mantineTheme}
          defaultColorScheme="dark"
          cssVariablesResolver={cssVariablesResolver}
          withStaticClasses={false}
        >
          <ToastProvider />
          <ConfirmProvider>
            <FavoritePagesProvider>
              <PinnedPagesProvider>
                <AppRouter />
              </PinnedPagesProvider>
            </FavoritePagesProvider>
          </ConfirmProvider>
        </MantineProvider>
      </ThemeProvider>
    </StoreProvider>
  );
}

export default App;
