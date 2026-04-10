import { createTheme, type CSSVariablesResolver, type MantineColorsTuple } from '@mantine/core';

// Создаем кастомную цветовую палитру на основе --base-orange-2
const orange: MantineColorsTuple = [
  '#fff4e6',
  '#ffe8cc',
  '#ffd8a8',
  '#ffc078',
  '#ffa94d',
  '#ff922b',
  '#fe6f31', // --base-orange-2
  '#fd5901',
  '#e65100',
  '#cc4700',
];

// Создаем цветовую палитру на основе --base-red
const red: MantineColorsTuple = [
  '#ffe9ea',
  '#ffd2d4',
  '#faa2a7',
  '#f56e77',
  '#f0434f',
  '#ee3036', // --base-red
  '#e61f26',
  '#c9151b',
  '#b01116',
  '#950d11',
];

// Создаем серую палитру
const gray: MantineColorsTuple = [
  '#fefcf9', // --base-white
  '#f5f5f5',
  '#e0e0e0',
  '#bdbdbd',
  '#9e9e9e',
  '#aeaeae', // --text-primary
  '#757575',
  '#585858', // --text-secondary
  '#424242',
  '#272727', // --bg-widget
];

export const mantineTheme = createTheme({
  // Основные цвета
  colors: {
    orange,
    red,
    gray,
  },

  // Основной цвет приложения
  primaryColor: 'orange',

  // Цветовая схема по умолчанию
  defaultRadius: 'md',

  // Шрифты
  fontFamily: "'Roboto Mono', var(--font-sans), monospace",
  fontSizes: {
    xs: 'var(--font-size-xs)',
    sm: 'var(--font-size-sm)',
    md: 'var(--font-size-md)',
    lg: 'var(--font-size-lg)',
    xl: 'var(--font-size-xl)',
  },

  // Line height
  lineHeights: {
    xs: 'var(--line-height-tight)',
    sm: 'var(--line-height-normal)',
    md: 'var(--line-height-normal)',
    lg: 'var(--line-height-relaxed)',
    xl: 'var(--line-height-loose)',
  },

  // Размеры заголовков
  headings: {
    fontFamily: "'Roboto Mono', var(--font-sans), monospace",
    sizes: {
      h1: { fontSize: 'var(--font-size-5xl)', lineHeight: 'var(--line-height-tight)' },
      h2: { fontSize: 'var(--font-size-4xl)', lineHeight: 'var(--line-height-tight)' },
      h3: { fontSize: 'var(--font-size-3xl)', lineHeight: 'var(--line-height-normal)' },
      h4: { fontSize: 'var(--font-size-2xl)', lineHeight: 'var(--line-height-normal)' },
      h5: { fontSize: 'var(--font-size-xl)', lineHeight: 'var(--line-height-normal)' },
      h6: { fontSize: 'var(--font-size-lg)', lineHeight: 'var(--line-height-relaxed)' },
    },
  },

  // Отступы и размеры
  spacing: {
    xs: '0.5rem',
    sm: '0.75rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
  },

  // Радиусы
  radius: {
    xs: '0.125rem',
    sm: '0.25rem',
    md: '0.5rem',
    lg: '0.75rem',
    xl: '1rem',
  },

  // Другие настройки
  other: {
    // CSS переменные из variables.css
    baseOrange: 'var(--base-orange)',
    baseOrange2: 'var(--base-orange-2)',
    baseWhite: 'var(--base-white)',
    baseRed: 'var(--base-red)',
    baseGrey: 'var(--text-primary)',
    baseGrey2: 'var(--text-secondary)',
    bgPage: 'var(--bg-page)',
    bgWidget: 'var(--bg-widget)',
    bgWidgetHover: 'var(--bg-widget-hover)',
    bgTableHeader: 'var(--bg-table-header)',
    unknownBorders: 'var(--lines-stokes-fa-connector)',
  },

  components: {
    Checkbox: {
      styles: {
        input: {
          '--checkbox-color': 'var(--base-orange-2)',
        },
      },
    },
    Drawer: {
      defaultProps: {
        zIndex: 'var(--z-modal)',
      },
    },
    Button: {
      defaultProps: {
        fw: 400,
        fz: '16px',
      },
    },
  },
});

/**
 * Переопределяет CSS переменные Mantine под токены проекта.
 */
export const cssVariablesResolver: CSSVariablesResolver = () => ({
  variables: {
    '--mantine-primary-color-filled': 'var(--color-outline-primary)',
    '--mantine-color-error': 'var(--orem-red-400)',
  },
  light: {
    '--mantine-color-error': 'var(--orem-red-400)',
  },
  dark: {
    '--mantine-color-error': 'var(--orem-red-400)',
  },
});
