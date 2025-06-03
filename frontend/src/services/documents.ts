import axios from 'axios';

const API_BASE_URL = '/api/documents';

export interface Document {
    id: string;
    title: string;
    content: string;
    createdAt: string;
    updatedAt: string;
}

export async function fetchDocuments(): Promise<Document[]> {
    const response = await axios.get<Document[]>(API_BASE_URL);
    return response.data;
}

export async function fetchDocumentById(id: string): Promise<Document> {
    const response = await axios.get<Document>(`${API_BASE_URL}/${id}`);
    return response.data;
}

export async function createDocument(document: Omit<Document, 'id' | 'createdAt' | 'updatedAt'>): Promise<Document> {
    const response = await axios.post<Document>(API_BASE_URL, document);
    return response.data;
}

export async function updateDocument(id: string, document: Partial<Omit<Document, 'id' | 'createdAt' | 'updatedAt'>>): Promise<Document> {
    const response = await axios.put<Document>(`${API_BASE_URL}/${id}`, document);
    return response.data;
}

export async function deleteDocument(id: string): Promise<void> {
    await axios.delete(`${API_BASE_URL}/${id}`);
}