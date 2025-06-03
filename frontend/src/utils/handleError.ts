/**
 * Utility function to handle errors in a consistent way.
 * Logs the error and returns a user-friendly message.
 */

export function handleError(error: unknown): string {
    if (error instanceof Error) {
        console.error(error);
        return error.message;
    }
    if (typeof error === 'string') {
        console.error(error);
        return error;
    }
    console.error('An unknown error occurred:', error);
    return 'An unexpected error occurred. Please try again later.';
}