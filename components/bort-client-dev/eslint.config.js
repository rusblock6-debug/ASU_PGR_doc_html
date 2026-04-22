import eslintPluginPrettier from 'eslint-plugin-prettier';
import eslintPluginTs from '@typescript-eslint/eslint-plugin';
import eslint from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import tseslint from 'typescript-eslint';
import { globalIgnores } from 'eslint/config';
import eslintPluginImport from 'eslint-plugin-import';
import eslintPluginCssModules from 'eslint-plugin-css-modules';
import eslintPluginReact from 'eslint-plugin-react';
import eslintPluginJsxA11y from 'eslint-plugin-jsx-a11y';
import fsdPlugin from 'eslint-plugin-fsd-lint';
import unusedImports from 'eslint-plugin-unused-imports';
import sonarjs from 'eslint-plugin-sonarjs';
import jsdoc from 'eslint-plugin-jsdoc';

export default tseslint.config(
  [
    globalIgnores(['dist', 'node_modules', '.storybook']),
    {
      files: ['**/*.{ts,tsx}'],
      extends: [
        eslint.configs.recommended,
        tseslint.configs.recommendedTypeChecked,
        tseslint.configs.stylistic,
        reactHooks.configs['recommended-latest'],
        reactRefresh.configs.vite,
      ],
      languageOptions: {
        ecmaVersion: 2020,
        globals: globals.browser,
        parserOptions: {
          ecmaFeatures: {
            jsx: true,
          },
          projectService: true,
        },
      },
      plugins: {
        '@typescript-eslint': eslintPluginTs,
        prettier: eslintPluginPrettier,
        import: eslintPluginImport,
        'css-modules': eslintPluginCssModules,
        react: eslintPluginReact,
        'jsx-a11y': eslintPluginJsxA11y,
        fsd: fsdPlugin,
        'unused-imports': unusedImports,
      },
      settings: {
        'import/resolver': {
          typescript: {
            alwaysTryTypes: true,
            project: './tsconfig.json',
          },
          node: {
            extensions: ['.js', '.jsx', '.ts', '.tsx'],
          },
        },
        react: {
          version: 'detect',
        },
      },
      rules: {
        'prettier/prettier': 'warn',

        // Запрет non-null assertion (!)
        '@typescript-eslint/no-non-null-assertion': 'error',

        // Отключаем стандартное правило в пользу unused-imports
        '@typescript-eslint/no-unused-vars': 'off',

        // Правила для автоматического удаления неиспользуемых импортов
        'unused-imports/no-unused-imports': 'error',
        'unused-imports/no-unused-vars': [
          'warn',
          {
            vars: 'all',
            varsIgnorePattern: '^_',
            args: 'after-used',
            argsIgnorePattern: '^_',
            ignoreRestSiblings: true,
          },
        ],

        '@typescript-eslint/naming-convention': [
          'error',
          // Переменные (включая React компоненты): camelCase или PascalCase для компонентов
          {
            selector: 'variable',
            format: ['camelCase', 'PascalCase'], // PascalCase для React компонентов
            leadingUnderscore: 'allow',
            trailingUnderscore: 'forbid',
          },
          // Функции: camelCase или PascalCase для компонентов
          {
            selector: 'function',
            format: ['camelCase', 'PascalCase'], // PascalCase для React компонентов
          },
          // Параметры: camelCase
          {
            selector: 'parameter',
            format: ['camelCase'],
            leadingUnderscore: 'allow',
          },
          // Константы: UPPER_CASE, PascalCase или camelCase
          {
            selector: 'variable',
            modifiers: ['const'],
            format: ['camelCase', 'PascalCase', 'UPPER_CASE'],
          },
          // Типы, интерфейсы, классы: PascalCase
          {
            selector: ['typeLike', 'class'],
            format: ['PascalCase'],
          },
          // Методы классов: camelCase
          {
            selector: ['classMethod', 'objectLiteralMethod'],
            format: ['camelCase'],
            leadingUnderscore: 'allow',
          },
          {
            selector: ['typeProperty'],
            format: ['camelCase', 'snake_case', 'PascalCase', 'UPPER_CASE'],
          },
          // Enum: PascalCase или UPPER_CASE
          {
            selector: 'enumMember',
            format: ['PascalCase', 'UPPER_CASE'],
          },
        ],
        // Базовое правило camelcase отключено в пользу более гибкого TypeScript правила
        camelcase: 'off',

        // React правила
        'react/prop-types': 'off', // Отключено, так как TypeScript берет на себя проверку типов
        'react/jsx-key': 'error', // Требует key для элементов в списках
        'react/jsx-no-target-blank': 'error', // Безопасность ссылок с target="_blank"
        'react/no-unescaped-entities': 'error', // Предотвращает проблемы с символами в JSX
        'react/display-name': 'warn', // Помогает при отладке в React DevTools
        'react/jsx-uses-react': 'off', // Отключено для JSX Runtime
        'react/jsx-uses-vars': 'error', // Предотвращает ложные предупреждения о неиспользуемых переменных JSX
        'react/jsx-curly-brace-presence': ['error', { props: 'never', children: 'never' }], // Запрещает фигурные скобки для простых строк: className="…" вместо className={'…'}
        'react/no-deprecated': 'warn', // Предупреждает об устаревших методах React
        'react/no-string-refs': 'error', // Запрещает использование строковых refs
        'react/require-render-return': 'error', // Требует return в render методах
        'react-hooks/exhaustive-deps': 'error',
        'react-refresh/only-export-components': 'off',

        // JSX A11y правила
        'jsx-a11y/alt-text': 'error', // Требует alt атрибут для изображений
        'jsx-a11y/anchor-is-valid': 'error', // Проверяет валидность ссылок
        'jsx-a11y/click-events-have-key-events': 'warn', // Требует keyboard events для click events
        'jsx-a11y/no-static-element-interactions': 'warn', // Предупреждает о событиях на статичных элементах
        'jsx-a11y/role-has-required-aria-props': 'error', // Проверяет наличие обязательных ARIA свойств
        'jsx-a11y/role-supports-aria-props': 'error', // Проверяет поддержку ARIA свойств ролями
        'jsx-a11y/img-redundant-alt': 'warn', // Предупреждает об избыточном тексте в alt

        // Дополнительные правила из Airbnb style guide
        'no-console': 'warn', // Предупреждает о console.log в продакшене
        'no-debugger': 'error', // Запрещает debugger statements
        'no-alert': 'error', // Предупреждает об использовании alert/confirm/prompt
        'no-eval': 'error', // Запрещает eval() - опасно для безопасности
        'no-implied-eval': 'error', // Запрещает неявные eval (setTimeout с строкой)
        'no-new-func': 'error', // Запрещает new Function() - потенциально опасно
        'no-return-assign': 'error', // Запрещает присваивание в return statements
        'no-script-url': 'error', // Запрещает javascript: urls
        'no-self-compare': 'error', // Запрещает сравнение переменной с самой собой
        'no-sequences': 'error', // Запрещает comma operator (кроме for loops)
        'no-throw-literal': 'error', // Требует throw только Error objects
        'no-unused-expressions': 'error', // Запрещает неиспользуемые выражения
        'no-useless-concat': 'error', // Запрещает бессмысленные конкатенации строк
        'no-useless-return': 'error', // Запрещает ненужные return statements
        'prefer-promise-reject-errors': 'error', // Требует reject с Error objects
        'require-await': 'error', // Требует await в async functions

        // Отслеживание неиспользуемых классов CSS Modules
        'css-modules/no-unused-class': ['error'],
        'css-modules/no-undef-class': ['error'],

        // Запрет циклических импортов
        'import/no-cycle': [
          'error',
          {
            maxDepth: 10,
            ignoreExternal: true,
            allowUnsafeDynamicCyclicDependency: false,
          },
        ],
        'import/no-self-import': 'error',
        'import/no-useless-path-segments': 'error',

        // Запрет расширений файлов для TypeScript/React импортов
        'import/extensions': [
          'error',
          'ignorePackages',
          {
            js: 'never',
            jsx: 'never',
            ts: 'never',
            tsx: 'never',
          },
        ],

        'no-restricted-imports': [
          'error',
          {
            paths: [
              {
                name: 'classnames',
                message:
                  "Прямой импорт classnames запрещен. Используйте: import { cn } from '@/shared/lib/classnames-utils'",
              },
              {
                name: 'classnames/bind',
                message:
                  "Прямой импорт classnames/bind запрещен. Используйте: import { createBoundClassNames } from '@/shared/lib/classnames-utils'",
              },
            ],
            patterns: [
              {
                group: ['classnames/*'],
                message: 'Импорт из classnames/* запрещен. Используйте утилиты из shared/lib/classnames-utils',
              },
              {
                group: ['**/*.css', '!**/*.module.css'],
                message:
                  'Импорт обычных CSS файлов запрещен. Используйте CSS Modules (*.module.css) для локальных стилей или классы для глобальных стилей.',
              },
            ],
          },
        ],

        // Правила для запрета «export type *» и «export *»
        'no-restricted-syntax': [
          'error',
          {
            selector: 'ExportAllDeclaration[exportKind="type"]',
            message:
              'Запрещен export type * from "...". Экспортируйте типы явно: export type { Type1, Type2 } from "..."',
          },
          {
            selector: 'ExportAllDeclaration[exportKind="value"]',
            message: 'Запрещен export * from "...". Используйте явные именованные экспорты.',
          },
        ],

        // Правила для FSD архитектуры
        'fsd/forbidden-imports': [
          'error',
          {
            layers: {
              shared: {
                pattern: 'shared',
                priority: 7,
                allowedToImport: ['shared'], // Разрешаем импорты внутри shared
              },
            },
          },
        ],
        'fsd/no-relative-imports': 'error',
        'fsd/no-public-api-sidestep': 'error',
        'fsd/no-cross-slice-dependency': 'error',
        'fsd/no-ui-in-business-logic': 'error',
        'fsd/no-global-store-imports': 'error',
        'fsd/ordered-imports': 'off',
        'import/order': [
          'error',
          {
            groups: [
              'builtin', // Node.js встроенные модули
              'external', // Внешние пакеты (react, lodash, etc.)
              'internal', // Внутренние модули (@/shared, @/entities, @/features, @/pages)
              'parent', // Родительские модули (../)
              'sibling', // Соседние модули (./)
              'index', // index файлы
            ],
            'newlines-between': 'always',
            alphabetize: {
              order: 'asc',
              caseInsensitive: true,
            },
            pathGroups: [
              {
                pattern: '@/app/**',
                group: 'internal',
                position: 'before',
              },
              {
                pattern: '@/pages/**',
                group: 'internal',
                position: 'before',
              },
              {
                pattern: '@/widgets/**',
                group: 'internal',
                position: 'before',
              },
              {
                pattern: '@/features/**',
                group: 'internal',
                position: 'before',
              },
              {
                pattern: '@/entities/**',
                group: 'internal',
                position: 'before',
              },
              {
                pattern: '@/shared/**',
                group: 'internal',
                position: 'before',
              },
            ],
            pathGroupsExcludedImportTypes: ['builtin'],
          },
        ],
      },
    },
    {
      files: ['**/shared/lib/classnames-utils.ts'],
      rules: {
        'no-restricted-imports': 'off',
      },
    },
    {
      files: ['**/vite.config.ts'],
      rules: {
        '@typescript-eslint/naming-convention': 'off',
        camelcase: 'off',
      },
    },
    {
      // /app — корень приложения, папки (providers, store) не являются изолированными слайсами.
      // Отключаем правило для app, т.к. в eslint-plugin-fsd-lint excludeLayers не работает из-за бага (mergeConfig теряет поле).
      files: ['**/app/**/*.{ts,tsx}'],
      rules: {
        'fsd/no-cross-slice-dependency': 'off',
      },
    },
    {
      // Исключения для файлов, которым разрешен импорт обычных CSS
      files: ['**/app/**/*.{ts,tsx}', '**/main.tsx'],
      rules: {
        'no-restricted-imports': [
          'error',
          {
            paths: [
              {
                name: 'classnames',
                message:
                  "Прямой импорт classnames запрещен. Используйте: import { cn } from '@/shared/lib/classnames-utils'",
              },
              {
                name: 'classnames/bind',
                message:
                  "Прямой импорт classnames/bind запрещен. Используйте: import { createBoundClassNames } from '@/shared/lib/classnames-utils'",
              },
            ],
            patterns: [
              {
                group: ['classnames/*'],
                message: 'Импорт из classnames/* запрещен. Используйте утилиты из shared/lib/classnames-utils',
              },
            ],
          },
        ],
      },
    },
    {
      // Исключения для .d.ts файлов (декларации типов)
      files: ['**/*.d.ts'],
      rules: {
        'unused-imports/no-unused-vars': 'off',
        '@typescript-eslint/no-unused-vars': 'off',
      },
    },
  ],
  sonarjs.configs.recommended,
  // JSDoc — только для src/, исключая тесты и stories
  {
    files: ['src/**/*.{ts,tsx}'],
    ignores: ['**/*.stories.{ts,tsx}', '**/*.test.{ts,tsx}', '**/*.spec.{ts,tsx}', 'src/shared/lib/msw/**'],
    ...jsdoc.configs['flat/recommended-typescript'],
    rules: {
      ...jsdoc.configs['flat/recommended-typescript'].rules,
      // Требовать JSDoc для всех функций, методов, классов и React компонентов
      'jsdoc/require-jsdoc': [
        'warn',
        {
          enableFixer: false,
          minLineCount: 3,
          require: {
            FunctionDeclaration: true,
            MethodDefinition: true,
            ClassDeclaration: true,
            ArrowFunctionExpression: false,
            FunctionExpression: false,
          },
          contexts: [
            // Top-level React компоненты как const arrow functions (исключаем вложенные)
            'Program > VariableDeclaration > VariableDeclarator > ArrowFunctionExpression',
            'ExportNamedDeclaration > VariableDeclaration > VariableDeclarator > ArrowFunctionExpression',
            'ExportDefaultDeclaration > ArrowFunctionExpression',
            // Top-level React компоненты как function expressions
            'Program > VariableDeclaration > VariableDeclarator > FunctionExpression',
            'ExportNamedDeclaration > VariableDeclaration > VariableDeclarator > FunctionExpression',
            // TS interfaces и types
            'TSInterfaceDeclaration',
            'TSTypeAliasDeclaration',
          ],
          checkConstructors: true,
          checkGetters: true,
          checkSetters: true,
        },
      ],
      // Требовать описание для функций/компонентов/интерфейсов
      'jsdoc/require-description': [
        'warn',
        {
          contexts: [
            'FunctionDeclaration',
            'MethodDefinition',
            'TSInterfaceDeclaration',
            'TSTypeAliasDeclaration',
            'Program > VariableDeclaration > VariableDeclarator > ArrowFunctionExpression',
            'ExportNamedDeclaration > VariableDeclaration > VariableDeclarator > ArrowFunctionExpression',
            'Program > VariableDeclaration > VariableDeclarator > FunctionExpression',
            'ExportNamedDeclaration > VariableDeclaration > VariableDeclarator > FunctionExpression',
          ],
        },
      ],
      // Для TypeScript типы уже есть, @param/@returns не обязательны
      'jsdoc/require-param': 'off',
      'jsdoc/require-param-description': 'off',
      'jsdoc/require-returns': 'off',
      'jsdoc/require-returns-description': 'off',
      'jsdoc/tag-lines': ['warn', 'any', { startLines: 1 }],

      '@typescript-eslint/no-misused-promises': 'off',
      '@typescript-eslint/unbound-method': 'off',
    },
  },
);
