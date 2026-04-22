import axios from 'axios';

const GRAPH_API_URL = import.meta.env.VITE_GRAPH_API_URL || '/graph-api';

const graphApiClient = axios.create({
  baseURL: GRAPH_API_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Place {
  id: number;
  name: string;
  type: string;
  tag_point_id?: string | null;
}

export interface PlacesResponse {
  items: Place[];
  total: number;
  limit: number;
  offset: number;
}

export const graphServiceApi = {
  async getPlaces(params?: { type?: string; limit?: number; offset?: number }): Promise<PlacesResponse> {
    const response = await graphApiClient.get<PlacesResponse>('/api/places', { params });
    return response.data;
  },
};

