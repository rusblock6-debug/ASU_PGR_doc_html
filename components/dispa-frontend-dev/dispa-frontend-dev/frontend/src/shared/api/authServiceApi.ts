/**
 * API клиент для Auth Service
 */
import axios from 'axios';

// Важно: используем префикс '/auth-api', который проксируется Vite на auth backend
const AUTH_API_BASE_URL = '/auth-api';

const authApiClient = axios.create({
  baseURL: AUTH_API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface LoginRequestBody {
  username: string;
  password: string;
}

export interface LoginResponse {
  // Оставляем тип свободным, так как контракт не уточнен
  [key: string]: unknown;
}

export const authServiceApi = {
  login: async (data: LoginRequestBody): Promise<LoginResponse> => {
    const response = await authApiClient.post<LoginResponse>('/auth/login', data);
    return response.data;
  },
};


