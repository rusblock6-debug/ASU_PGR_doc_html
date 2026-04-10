import type { ScenePoint } from '../../lib/drawing/model/types';

/** Состояние редактирования графа. */
export interface GraphEditState {
  /** Граф на момент начала редактирования, нужен для определения изменился и нет. */
  readonly initialDraft: GraphData | null;
  /** Текущая рабочая копия графа, изменяемая пользователем. */
  readonly draft: GraphData | null;
  /** Превью цвета дороги при изменении через ColorPicker (до сохранения). */
  readonly previewColor: string | null;
}

/** Тип для дорожного графа. */
export interface GraphData {
  /** Вершины графа. */
  readonly nodes: readonly GraphNode[];
  /** Ненаправленные ребра между вершинами. */
  readonly edges: readonly GraphEdge[];
}

/** Узел графа в координатах сцены. */
export interface GraphNode extends ScenePoint {
  /** Серверный идентификатор узла. `null` для узлов, созданных в редакторе. */
  readonly id: number | null;
  /** Клиентский идентификатор (nanoid) — React-key и ключ ссылок ребер (`fromId`/`toId`). */
  readonly tempId: string;
}

/** Ребро графа (ненаправленное). */
export interface GraphEdge {
  /** Серверный идентификатор ребра. `null` для рёбер, созданных в редакторе. */
  readonly id: number | null;
  /** Клиентский идентификатор (nanoid) — React-key и идентификатор для операций в редакторе. */
  readonly tempId: string;
  /** Временный идентификатор первого узла ребра. */
  readonly fromId: string;
  /** Временный идентификатор второго узла ребра. */
  readonly toId: string;
}
