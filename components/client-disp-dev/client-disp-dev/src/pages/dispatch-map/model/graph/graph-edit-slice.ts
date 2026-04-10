import type { PayloadAction } from '@reduxjs/toolkit';
import { createSlice, nanoid } from '@reduxjs/toolkit';

import { areConnected } from './graph-operations';
import { serverToEditor } from './mappers';
import type { GraphData, GraphEdge, GraphEditState } from './types';

const initialState: GraphEditState = {
  initialDraft: null,
  draft: null,
  previewColor: null,
};

export const graphEditSlice = createSlice({
  name: 'graphEdit',
  initialState,
  reducers: {
    initDraft: {
      prepare(serverData: Parameters<typeof serverToEditor>[0]) {
        const { nodes, edges } = serverToEditor(serverData);
        return { payload: { nodes, edges } };
      },
      reducer(state, action: PayloadAction<GraphData>) {
        const { nodes, edges } = action.payload;
        state.initialDraft = { nodes: [...nodes], edges: [...edges] };
        state.draft = { nodes: [...nodes], edges: [...edges] };
      },
    },

    resetDraft(state) {
      state.initialDraft = null;
      state.draft = null;
    },

    setPreviewColor(state, action: PayloadAction<string | null>) {
      state.previewColor = action.payload;
    },

    addNode: {
      prepare(x: number, z: number, fromNodeTempId: string | null = null) {
        return { payload: { tempId: nanoid(), edgeId: nanoid(), x, z, fromNodeTempId } };
      },
      reducer(
        state,
        action: PayloadAction<{ tempId: string; edgeId: string; x: number; z: number; fromNodeTempId: string | null }>,
      ) {
        if (!state.draft) return;
        const { tempId, edgeId, x, z, fromNodeTempId } = action.payload;
        state.draft.nodes.push({ id: null, tempId, x, z });
        if (fromNodeTempId) {
          state.draft.edges.push({ id: null, tempId: edgeId, fromId: fromNodeTempId, toId: tempId });
        }
      },
    },

    addEdge: {
      prepare(fromId: string, toId: string) {
        return { payload: { edgeId: nanoid(), fromId, toId } };
      },
      reducer(state, action: PayloadAction<{ edgeId: string; fromId: string; toId: string }>) {
        if (!state.draft) return;
        const { edgeId, fromId, toId } = action.payload;
        if (fromId === toId || areConnected(state.draft.edges, fromId, toId)) return;
        state.draft.edges.push({ id: null, tempId: edgeId, fromId, toId });
      },
    },

    moveNode(state, action: PayloadAction<{ tempId: string; x: number; z: number }>) {
      if (!state.draft) return;
      const node = state.draft.nodes.find((node) => node.tempId === action.payload.tempId);
      if (node) {
        node.x = action.payload.x;
        node.z = action.payload.z;
      }
    },

    /** Внутренний reducer — вызывается только из thunk `removeNode`. */
    _removeNode(state, action: PayloadAction<{ nodeId: string; reconnectEdges: GraphEdge[] }>) {
      if (!state.draft) return;
      const { nodeId, reconnectEdges } = action.payload;

      const remainingEdges = state.draft.edges.filter((edge) => {
        return edge.fromId !== nodeId && edge.toId !== nodeId;
      });
      const edges = [...remainingEdges, ...reconnectEdges];

      const nodesInEdges = new Set(edges.flatMap((edge) => [edge.fromId, edge.toId]));
      state.draft.nodes = state.draft.nodes.filter((node) => node.tempId !== nodeId && nodesInEdges.has(node.tempId));
      state.draft.edges = edges;
    },

    /** Внутренний reducer — вызывается только из thunk `splitEdge`. */
    _splitEdge(
      state,
      action: PayloadAction<{ edgeId: string; x: number; z: number; tempId: string; edgeAId: string; edgeBId: string }>,
    ) {
      if (!state.draft) return;
      const { edgeId, x, z, tempId, edgeAId, edgeBId } = action.payload;

      const edgeIndex = state.draft.edges.findIndex((edge) => edge.tempId === edgeId);
      if (edgeIndex === -1) return;

      const edge = state.draft.edges[edgeIndex];
      state.draft.nodes.push({ id: null, tempId, x, z });
      state.draft.edges.splice(
        edgeIndex,
        1,
        { id: null, tempId: edgeAId, fromId: edge.fromId, toId: tempId },
        { id: null, tempId: edgeBId, fromId: tempId, toId: edge.toId },
      );
    },
  },
});

export const graphEditActions = graphEditSlice.actions;
export const graphEditReducer = graphEditSlice.reducer;
