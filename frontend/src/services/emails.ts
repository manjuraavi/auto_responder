import axios from 'axios';

const API_BASE_URL = '/api/emails';

export interface Email {
    id: string;
    from: string;
    to: string;
    subject: string;
    body: string;
    receivedAt: string;
    isRead: boolean;
}

export async function fetchEmails(): Promise<Email[]> {
    const response = await axios.get<Email[]>(API_BASE_URL);
    return response.data;
}

export async function fetchEmailById(id: string): Promise<Email> {
    const response = await axios.get<Email>(`${API_BASE_URL}/${id}`);
    return response.data;
}

export async function sendEmail(email: Omit<Email, 'id' | 'receivedAt' | 'isRead'>): Promise<Email> {
    const response = await axios.post<Email>(API_BASE_URL, email);
    return response.data;
}

export async function markEmailAsRead(id: string): Promise<void> {
    await axios.patch(`${API_BASE_URL}/${id}/read`);
}

export async function deleteEmail(id: string): Promise<void> {
    await axios.delete(`${API_BASE_URL}/${id}`);
}