/**
 * Formats a Date object or date string into 'YYYY-MM-DD' format.
 * @param date - The date to format (Date object or string)
 * @returns Formatted date string
 */
export function formatDate(date: Date | string): string {
    const d = typeof date === 'string' ? new Date(date) : date;
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}