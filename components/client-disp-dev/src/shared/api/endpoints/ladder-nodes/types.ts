import type { EdgeGraph, NodeGraph } from '@/shared/api/endpoints/horizons/types';

/** Представляет модель запроса на создание лестницы между двумя узлами. */
export interface LadderConnectRequest {
  /** Идентификатор начального узла. */
  readonly from_node_id: number;
  /** Идентификатор конечного узла. */
  readonly to_node_id: number;
}

/** Представляет модель краткой информации о горизонте в ответе лестницы. */
export interface LadderHorizonInfo {
  /** Возвращает идентификатор горизонта. */
  readonly id: number;
  /** Возвращает наименование горизонта. */
  readonly name: string;
  /** Возвращает высоту горизонта. */
  readonly height: number;
}

/** Представляет модель ответа на создание лестницы между двумя узлами. */
export interface LadderConnectResponse {
  /** Возвращает сообщение о результате операции. */
  readonly message: string;
  /** Возвращает идентификатор созданной лестницы. */
  readonly ladder_id: number;
  /** Возвращает начальный узел лестницы. */
  readonly from_node: NodeGraph;
  /** Возвращает конечный узел лестницы. */
  readonly to_node: NodeGraph;
  /** Возвращает ребро лестницы. */
  readonly ladder_edge: EdgeGraph;
  /** Возвращает горизонт начального узла. */
  readonly from_horizon: LadderHorizonInfo;
  /** Возвращает горизонт конечного узла. */
  readonly to_horizon: LadderHorizonInfo;
}
