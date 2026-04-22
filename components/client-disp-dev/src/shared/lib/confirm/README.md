# Confirm

Модуль для вызова модальных окон подтверждения.

## Зачем нужен

Позволяет вызывать модалку подтверждения **из любого места** приложения через промис, без необходимости управлять
состоянием модалки вручную в каждом компоненте.

## Использование

```tsx
import { useConfirm } from '@/shared/lib/confirm';

function MyComponent() {
  const confirm = useConfirm();

  const handleDelete = async (item: Item) => {
    const confirmed = await confirm({
      title: 'Удаление',
      message: `Удалить ${item.name}?`,
      confirmText: 'Удалить',
      cancelText: 'Отмена',
    });

    if (confirmed) {
      await deleteItem(item.id);
    }
  };

  return <button onClick={() => handleDelete(item)}>Удалить</button>;
}
```
