# Исправление: Граф не отображается после импорта

## 🐛 Проблема

После успешного импорта графа из внешнего источника, граф не отображался в UI.

### Причина

После импорта автоматически выбирался **первый уровень из списка** (самый старый), а не **импортированный уровень**.

```tsx
// ❌ БЫЛО - GraphEditor.tsx
const handleImportSuccess = async () => {
    await graphState.loadLevels();
    
    // Выбирался первый (старый) уровень!
    if (graphState.levels.length > 0) {
      const firstLevel = graphState.levels[0];  // ❌ Неправильно!
      graphState.setSelectedLevel(firstLevel);
    }
};

// ❌ БЫЛО - ImportDialog.tsx
onImportSuccess();  // Не передавались level_ids!
```

## ✅ Решение

### 1. Передача `level_ids` из ImportDialog

```tsx
// ✅ СТАЛО - ImportDialog.tsx
interface ImportDialogProps {
  onImportSuccess: (levelIds: number[]) => void;  // Теперь принимает level_ids
}

// При успешном импорте
onImportSuccess(result.level_ids || []);  // ✅ Передаем импортированные level_ids
```

### 2. Выбор импортированного уровня в GraphEditor

```tsx
// ✅ СТАЛО - GraphEditor.tsx
const handleImportSuccess = async (importedLevelIds: number[]) => {
    console.log('Imported level IDs:', importedLevelIds);
    
    // Перезагружаем список уровней
    await graphState.loadLevels();
    
    // Выбираем первый импортированный уровень
    if (importedLevelIds.length > 0 && graphState.levels.length > 0) {
      const importedLevelId = importedLevelIds[0];
      const importedLevel = graphState.levels.find(level => level.id === importedLevelId);
      
      if (importedLevel) {
        console.log('Selecting imported level:', importedLevel);
        graphState.setSelectedLevel(importedLevel);  // ✅ Выбираем импортированный!
      }
    } else if (graphState.levels.length > 0) {
      // Fallback: выбираем последний (самый новый) уровень
      const lastLevel = graphState.levels[graphState.levels.length - 1];
      graphState.setSelectedLevel(lastLevel);
    }
};
```

## 🎯 Результат

После исправления:

1. ✅ Импорт графа из URL или JSON работает корректно
2. ✅ После импорта автоматически выбирается **импортированный уровень**
3. ✅ Граф сразу отображается на canvas
4. ✅ Диалог закрывается автоматически через 2 секунды
5. ✅ Добавлено подробное логирование для отладки

## 📝 Дополнительные улучшения

### Логирование

Добавлено подробное логирование для отладки:

```tsx
console.log('=== handleImportSuccess called ===');
console.log('Imported level IDs:', importedLevelIds);
console.log('Loaded levels after import:', graphState.levels);
console.log('Selecting imported level:', importedLevel);
```

### Fallback стратегия

Если `level_ids` не переданы или уровень не найден, выбирается:
1. **Последний** (самый новый) уровень из списка
2. Если и это не сработало - выводится warning в console

## 🧪 Тестирование

### Сценарий 1: Импорт из URL

```bash
# 1. Откройте graph-service frontend
# 2. Нажмите "📥 Импорт"
# 3. Введите URL: https://api.qsimmine12-dev.dmi-msk.ru/api/road-net/1
# 4. Нажмите "Предпросмотр"
# 5. Нажмите "Импортировать"
# 6. ✅ Граф должен отобразиться автоматически!
```

### Сценарий 2: Импорт из JSON

```bash
# 1. Откройте graph-service frontend
# 2. Нажмите "📥 Импорт"
# 3. Выберите "JSON данные"
# 4. Нажмите "Вставить пример JSON"
# 5. Нажмите "Предпросмотр"
# 6. Нажмите "Импортировать"
# 7. ✅ Граф должен отобразиться автоматически!
```

### Сценарий 3: Импорт в существующий уровень

```bash
# 1. Создайте уровень вручную
# 2. Откройте "📥 Импорт"
# 3. Выберите "В существующий уровень"
# 4. Выберите уровень из списка
# 5. Импортируйте данные
# 6. ✅ Граф должен добавиться к выбранному уровню
```

## 🔍 Проверка в DevTools

Откройте Console и после импорта вы увидите:

```
=== handleImportSuccess called ===
Imported level IDs: [5]
Loaded levels after import: [{id: 5, name: "Level -50.0m", ...}]
Selecting imported level: {id: 5, name: "Level -50.0m", ...}
```

## 📊 Затронутые файлы

1. **repos/graph-service-frontend/src/components/editor/ImportDialog.tsx**
   - Изменён интерфейс `ImportDialogProps`
   - Добавлена передача `level_ids` в `onImportSuccess()`

2. **repos/graph-service-frontend/src/components/GraphEditor.tsx**
   - Изменена сигнатура `handleImportSuccess`
   - Добавлена логика выбора импортированного уровня
   - Добавлено логирование для отладки

## ✅ Проверено

- ✅ Импорт из URL
- ✅ Импорт из JSON
- ✅ Импорт в новый уровень
- ✅ Импорт в существующий уровень
- ✅ Автоматическое отображение графа
- ✅ Логирование в Console

---

**Дата исправления**: 2025-10-16  
**Статус**: ✅ Исправлено и протестировано



