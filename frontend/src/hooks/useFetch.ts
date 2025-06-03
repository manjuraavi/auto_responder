import { useState, useEffect } from 'react';
import api from '../services/api';

type UseFetchResult<T> = {
    data: T | null;
    loading: boolean;
    error: Error | null;
};

function useFetch<T = unknown>(url: string, options?: any): UseFetchResult<T> {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        let isMounted = true;
        setLoading(true);
        setError(null);

        api(url, options)
            .then((response) => {
                if (isMounted) setData(response.data as T);
            })
            .catch((err) => {
                if (isMounted) setError(err as Error);
            })
            .finally(() => {
                if (isMounted) setLoading(false);
            });

        return () => {
            isMounted = false;
        };
    }, [url, JSON.stringify(options)]);

    return { data, loading, error };
}

export default useFetch;