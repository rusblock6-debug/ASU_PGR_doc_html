# API Endpoints

Каждый endpoint — отдельная папка с файлами:

```
endpoints/
  example/
    example-rtk.ts    # RTK Query endpoint (injectEndpoints)
    types.ts          # Типы запросов/ответов
    index.ts          # Реэкспорт
```

## Паттерн создания endpoint

```typescript
// example-rtk.ts
import { rtkApi } from '../rtk-api';

import type { ExampleResponse } from './types';

const exampleApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    getExamples: build.query<ExampleResponse[], void>({
      query: () => '/examples',
    }),
  }),
});

export const { useGetExamplesQuery } = exampleApi;
```

```typescript
// types.ts
export interface ExampleResponse {
  readonly id: number;
  readonly name: string;
}
```

```typescript
// index.ts
export { useGetExamplesQuery } from './example-rtk';
export type { ExampleResponse } from './types';
```
