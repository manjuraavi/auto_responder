import axios from 'axios';

const API_URL = '/api/auth';

export interface LoginCredentials {
    email: string;
    password: string;
}

export interface RegisterData {
    email: string;
    password: string;
    name?: string;
}

export interface AuthResponse {
    token: string;
    user: {
        id: string;
        email: string;
        name?: string;
    };
}

export const login = async (credentials: LoginCredentials): Promise<AuthResponse> => {
    const response = await axios.post<AuthResponse>(`${API_URL}/login`, credentials);
    return response.data;
};

export const register = async (data: RegisterData): Promise<AuthResponse> => {
    const response = await axios.post<AuthResponse>(`${API_URL}/register`, data);
    return response.data;
};

export const logout = (): void => {
    // Remove token or user data from storage
    localStorage.removeItem('authToken');
};

export const setAuthToken = (token: string): void => {
    localStorage.setItem('authToken', token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
};

export const getAuthToken = (): string | null => {
    return localStorage.getItem('authToken');
};