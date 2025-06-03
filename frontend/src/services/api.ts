import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  withCredentials: true, // Enable cookies and credentials
});

api.interceptors.response.use(
  response => response,
  error => {
    if (error.response && error.response.status === 429) {
      window.dispatchEvent(
        new CustomEvent("rateLimitExceeded", {
          detail: error.response.data.detail || "You are sending requests too quickly. Please wait and try again."
        })
      );
    }
    return Promise.reject(error);
  }
);

export const setAuthToken = (token: string | null) => {
  if (token) {
    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common["Authorization"];
  }
};

export default api;