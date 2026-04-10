import type { Place } from '@/shared/api/endpoints/places';
import type { Shaft } from '@/shared/api/endpoints/shafts';
import type { Tag } from '@/shared/api/endpoints/tags';
import type { Pagination } from '@/shared/api/types/pagination';

/** Представляет модель горизонта. */
export interface Horizon {
  /** Возвращает идентификатор. */
  readonly id: number;
  /** Возвращает наименование уровня. */
  readonly name: string;
  /** Возвращает высоту уровня в метрах. */
  readonly height: number;
  /** Возвращает цвет. */
  readonly color: string;
  /** Возвращает дату создания. */
  readonly created_at: string;
  /** Возвращает дату изменения. */
  readonly updated_at: string;
  /** Возвращает список шахт, относящихся к горизонту. */
  readonly shafts: readonly Pick<Shaft, 'id' | 'name'>[];
}

/** Представляет модель данных, получаемую по запросу горизонтов. */
export interface HorizonResponse extends Pagination {
  /** Возвращает список горизонтов. */
  readonly items: readonly Horizon[];
}

/** Представляет модель данных для создания горизонта. */
export interface CreateHorizonRequest {
  /** Возвращает наименование уровня. */
  readonly name: string;
  /** Возвращает высоту уровня в метрах. */
  readonly height: number;
  /** Возвращает цвет. */
  readonly color?: string;
  /** Возвращает список шахт, относящихся к горизонту. */
  readonly shafts?: readonly number[];
}

/** Представляет модель данных для редактирования горизонта. */
export interface UpdateHorizonRequest {
  /** Возвращает наименование уровня. */
  readonly name?: string;
  /** Возвращает высоту уровня в метрах. */
  readonly height?: number;
  /** Возвращает цвет. */
  readonly color?: string;
  /** Возвращает список шахт, относящихся к горизонту. */
  readonly shafts?: readonly number[];
}

/** Представляет ответ API полного графа горизонта (узлы, рёбра, метки). Включает вертикальные рёбра между горизонтами. */
export interface HorizonGraphResponse {
  /** Возвращает горизонт. */
  readonly horizon: Horizon;
  /** Возвращает список узлов графа. */
  readonly nodes: readonly HorizonGraphNode[];
  /** Возвращает список рёбер графа (горизонтальных и вертикальных). */
  readonly edges: readonly HorizonGraphEdge[];
  /** Возвращает список меток на графе. */
  readonly tags: readonly Tag[];
  /** Возвращает список мест на графе. */
  readonly places: readonly Place[];
  /** Схема на стороне бэкенда пока не определена. */
  readonly node_places: readonly unknown[];
  /** Схема на стороне бэкенда пока не определена. */
  readonly ladders: readonly unknown[];
}

/** Представляет узел графа горизонта. */
export interface HorizonGraphNode {
  /** Возвращает идентификатор узла. */
  readonly id: number;
  /** Возвращает координату X. */
  readonly x: number;
  /** Возвращает координату Y. */
  readonly y: number;
  /** Возвращает высоту (Z-координата). */
  readonly z: number;
  /** Возвращает тип узла (например, "road"). */
  readonly node_type: string;
  /** Возвращает список идентификаторов связанных узлов. */
  readonly linked_nodes: readonly number[] | null;
  /** Возвращает список идентификаторов лестниц. */
  readonly ladders_ids: readonly number[] | null;
  /** Возвращает дату создания. */
  readonly created_at: string;
  /** Возвращает дату изменения. */
  readonly updated_at: string;
  /** Возвращает идентификатор горизонта. */
  readonly horizon_id: number;
}

/** Представляет ребро графа горизонта. Включает горизонтальные и вертикальные (между горизонтами) рёбра. */
export interface HorizonGraphEdge {
  /** Возвращает идентификатор ребра. */
  readonly id: number;
  /** Возвращает идентификатор начального узла. */
  readonly from_node_id: number;
  /** Возвращает идентификатор конечного узла. */
  readonly to_node_id: number;
  /** Возвращает тип ребра (например, "horizontal", "vertical"). */
  readonly edge_type: string;
  /** Возвращает направление ребра (например, "Двунаправленное"). */
  readonly direction: string;
  /** Возвращает дату создания. */
  readonly created_at: string;
  /** Возвращает дату изменения. */
  readonly updated_at: string;
  /** Возвращает идентификатор горизонта. */
  readonly horizon_id: number;
}

/** Тело запроса на обновление графа горизонта (полная замена). */
export interface UpdateHorizonGraphRequest {
  readonly nodes: readonly {
    /** Серверный id для существующих узлов, строковый клиентский id для новых. */
    readonly id: number | string;
    /** Возвращает координату X. */
    readonly x: number;
    /** Возвращает координату Y. */
    readonly y: number;
  }[];
  readonly edges: readonly {
    /** Серверный id ребра. Передаётся только для существующих ребер. */
    readonly id?: number;
    /** Возвращает идентификатор начального узла, строковый клиентский id для новых. */
    readonly from_node_id: number | string;
    /** Возвращает идентификатор конечного узла, строковый клиентский id для новых. */
    readonly to_node_id: number | string;
  }[];
}
