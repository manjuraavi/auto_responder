import { useState, useEffect } from 'react';

const TOKEN_KEY = 'auth_token';

export function useToken() {
    const [token, setTokenState] = useState<string | null>(() => {
        return localStorage.getItem(TOKEN_KEY);
    });

    useEffect(() => {
        if (token) {
            localStorage.setItem(TOKEN_KEY, token);
        } else {
            localStorage.removeItem(TOKEN_KEY);
        }
    }, [token]);

    const setToken = (newToken: string | null) => {
        setTokenState(newToken);
    };

    const clearToken = () => {
        setTokenState(null);
    };

    return { token, setToken, clearToken };
}