import type { Preview } from '@storybook/react-vite';
import React from 'react';
import { MantineProvider } from '@mantine/core';

import '../src/app/styles/main.css';

import { cssVariablesResolver, mantineTheme } from '../src/app/theme/mantine-theme';

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    backgrounds: {
      default: 'dark',
      values: [
        { name: 'dark', value: '#444444' },
        { name: 'widget', value: '#272727' },
        { name: 'light', value: '#fefcf9' },
      ],
    },
  },
  decorators: [
    (Story, context) => {
      const colorScheme = context.globals.colorScheme || 'dark';

      return (
        <MantineProvider
          theme={mantineTheme}
          defaultColorScheme={colorScheme}
          cssVariablesResolver={cssVariablesResolver}
          withStaticClasses={false}
        >
          <div
            style={{
              padding: '1rem',
              background: colorScheme === 'dark' ? '#444444' : '#fefcf9',
              minHeight: '100vh',
            }}
          >
            <Story />
          </div>
        </MantineProvider>
      );
    },
  ],
  globalTypes: {
    colorScheme: {
      name: 'Color Scheme',
      description: 'Mantine color scheme',
      defaultValue: 'dark',
      toolbar: {
        icon: 'mirror',
        items: [
          { value: 'light', title: 'Light' },
          { value: 'dark', title: 'Dark' },
        ],
        dynamicTitle: true,
      },
    },
  },
};

export default preview;
