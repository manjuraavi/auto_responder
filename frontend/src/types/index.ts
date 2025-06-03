export interface User {
  email: string;
  name?: string;
  picture?: string;
  id: string;
}

export interface Email {
  id: string;
  subject: string;
  from: string;
  to: string;
  body: string;
  date: string;
  labels: string[];
  thread?: EmailMessage[];
  isUnread?: boolean;
}

export interface EmailMessage {
  id: string;
  from: string;
  to: string;
  subject: string;
  body: string;
  date: string;
  isReply?: boolean;
}

export interface Document {
  id: string;
  filename: string;
  uploadedAt: string;
  size: number;
  type: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  access_token: string;
  refresh_token?: string;
  user: User;
}

export interface EmailResponse {
  emails: Email[];
  total: number;
  unread_count: number;
}

export interface GenerateResponseRequest {
  email_id: string;
}

export interface SendReplyRequest {
  content: string;
  use_generated: boolean;
}

export interface UploadDocumentsResponse {
  uploaded_count: number;
  documents: Document[];
}

export interface ApiError {
  detail: string;
  status_code: number;
}

export interface LoadingState {
  isLoading: boolean;
  error: string | null;
}

export interface EmailFilters {
  unread_only?: boolean;
  search?: string;
  labels?: string[];
}

export interface EmailLabel {
  id: string;
  name: string;
  type: 'system' | 'user';
}