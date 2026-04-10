import { MantineProvider } from '@mantine/core';
import { Notifications } from '@mantine/notifications';

import { AuthProvider } from '@/shared/lib/auth';
import { ConfirmProvider } from '@/shared/lib/confirm';

import { AppRouter } from './providers/router';
import { StoreProvider } from './providers/StoreProvider';
import { ThemeProvider } from './providers/ThemeProvider';
import { cssVariablesResolver, mantineTheme } from './theme/mantine-theme';

import './styles/main.css';

/** Корневой компонент приложения. */
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
          <Notifications />
          <ConfirmProvider>
            <AuthProvider>
              <AppRouter />
            </AuthProvider>
          </ConfirmProvider>
        </MantineProvider>
      </ThemeProvider>
    </StoreProvider>
  );
}

export default App;
