import { createContext, useContext, useState, ReactNode, useEffect } from 'react';
import api, { setAuthToken } from '../services/api';
import { useNavigate } from 'react-router-dom';

interface User {
    id?: string;
    email: string;
    name?: string;
    picture?: string;
}

interface AuthContextType {
    user: User | null;
    accessToken: string | null;
    refreshToken: string | null;
    loading: boolean;
    login: () => void;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
    const [user, setUser] = useState<User | null>(null);
    const [accessToken, setAccessToken] = useState<string | null>(null);
    const [refreshToken, setRefreshToken] = useState<string | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const navigate = useNavigate();

    // On mount, check if user is authenticated (via cookie/session)
    useEffect(() => {
        setLoading(true);
        api.get('/auth/me')
            .then(res => {
                const data = res.data;
                setUser(data.user);
                setAccessToken(data.access_token || null);
                setRefreshToken(data.refresh_token || null);
            })
            .catch(() => {
                setUser(null);
                setAccessToken(null);
                setRefreshToken(null);
            })
            .finally(() => setLoading(false));
    }, []);

    // Start OAuth flow
    const login = async () => {
        setLoading(true);
        try {
            const resp = await api.post('/auth/google');
            const data = resp.data;
            window.location.href = data.auth_url;
        } catch {
            setLoading(false);
        }
    };

    const logout = () => {
        setUser(null);
        setAccessToken(null);
        setRefreshToken(null);
        localStorage.removeItem('user');
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        setAuthToken(null);
        api.post('/auth/logout').finally(() => {
            navigate('/login');
        });
    };

    return (
        <AuthContext.Provider value={{ user, accessToken, refreshToken, loading, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};