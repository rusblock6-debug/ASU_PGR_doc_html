# Mantine Styles

CSS-модули со **стилями Mantine**, которые подключаются **только в компонентах** (`shared/ui/*`) через `classNames`.

Цель — вынести повторяющиеся куски оформления (например, базовый `Input`/`InputWrapper`) в одно место и **не размазывать** их по каждому компоненту адаптеру. Специфичные стили конкретного компонента (иконки, отступы, нестандартные состояния) остаются рядом с адаптером в его `*.module.css`.

Стили подключаются **только через `classNames`** в адаптерах, а **не глобально** через `mantineTheme.components`.

## Использование

Пример использования смотрите в `shared/ui/TextInput/TextInput.tsx`.

Важно: `mod={{ 'input-size': size }}` добавляет атрибут data-input-size к корневому элементу, который используется в input-wrapper.module.css для применения размеров.

`mod={{ 'label-position': labelPosition }}` добавляет атрибут data-label-position к корневому элементу, который используется в input-wrapper.module.css для применения горизонтального расположения лейбла и инпута.

## Контракт

### Правила

1. **Файл = компонент Mantine** (kebab-case): `input.module.css`, `date-time-picker.module.css`
2. **Классы внутри = слоты Mantine** (1:1): `wrapper`, `input`, `section`, `label`, `error`
3. **Никаких произвольных имён**: только слоты из API `classNames` Mantine.
   Пример https://mantine.dev/core/input/?t=styles-api

### Запрещено

- Подключать глобально через `mantineTheme.components`
- Использовать селекторы `.mantine-*`
- Добавлять классы, не соответствующие слотам Mantine

### Разрешено

- Использовать `[data-size]`, `[data-variant]`, `[data-error]` и прочие кастомные дата-атрибуты внутри слотов
- Использовать CSS переменные из `app/styles/variables.css`
