import { useCallback } from 'react';

type ToastType = 'success' | 'error' | 'info' | 'warning';

interface ToastOptions {
    type?: ToastType;
    duration?: number; // in ms
}

export function useToast() {
    const showToast = useCallback(
        (message: string, options: ToastOptions = {}) => {
            const { type = 'info'} = options;

            // Simple implementation using browser alert (replace with your UI library)
            // For real apps, integrate with a toast library like react-toastify or Chakra UI
            // Example: toast(message, { type, duration });
            window.alert(`[${type.toUpperCase()}] ${message}`);

            // Optionally, you can implement a custom event or state here
        },
        []
    );

    return { showToast };
}