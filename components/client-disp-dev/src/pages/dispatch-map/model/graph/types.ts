import type { ScenePoint } from '../../lib/drawing/model/types';

/** Тип элемента графа: дорожный или лестничный (переезд). */
export const GraphElementType = {
  ROAD: 'road',
  LADDER: 'ladder',
} as const;

/** Значение типа элемента графа. */
export type GraphElementTypeValue = (typeof GraphElementType)[keyof typeof GraphElementType];

/** Конечная точка переезда (лестницы): вершина + горизонт. */
export interface LadderEndpoint {
  /** Вершина. */
  readonly nodeId: number;
  /** Идентификатор горизонта. */
  readonly horizonId: number;
}

/** Состояние редактирования графа. */
export interface GraphEditState {
  /** Граф на момент начала редактирования, нужен для определения изменился и нет. */
  readonly initialDraft: GraphData | null;
  /** Текущая рабочая копия графа, изменяемая пользователем. */
  readonly draft: GraphData | null;
  /** Превью цвета дороги при изменении через ColorPicker (до сохранения). */
  readonly previewColor: string | null;
  /** Цвет дороги горизонта на момент начала редактирования (из `horizon.color`). */
  readonly roadColor: string | null;
  /** Активен ли режим редактирования переездов (лестниц). */
  readonly isLadderEditActive: boolean;
  /** Вершина-источник переезда на исходном горизонте. */
  readonly ladderSource: LadderEndpoint | null;
  /** Целевая вершина переезда на другом горизонте. */
  readonly ladderTarget: LadderEndpoint | null;
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
  /** Серверный идентификатор вершины. `null` для узлов, созданных в редакторе. */
  readonly id: number | null;
  /** Клиентский идентификатор (nanoid) — React-key и ключ ссылок ребер (`fromId`/`toId`). */
  readonly tempId: string;
  /** Идентификатор горизонта вершины. `null` для узлов, созданных в редакторе. */
  readonly horizonId: number | null;
  /** Тип вершины: `'road'` — дорожный, `'ladder'` — лестничный (переезд между горизонтами). */
  readonly nodeType: GraphElementTypeValue;
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
  /** Тип ребра: `'road'` — в пределах горизонта, `'ladder'` — между горизонтами (лестница). */
  readonly edgeType: GraphElementTypeValue;
}
