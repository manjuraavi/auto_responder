import React, { useState, useEffect, ChangeEvent } from "react";
import api from "../../services/api";
import Button from "../../components/Button";

interface Document {
  id: string;
  filename: string;
  created_at: string;
  url: string;
}

const DocumentManager: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);

  const [ingestionStatus, setIngestionStatus] = useState<"idle" | "in_progress" | "completed" | "failed">("idle");


  useEffect(() => {
    api.get("/settings/ingestion-status").then(res => {
      console.log("Ingestion status:", res.data);
      setIngestionStatus(res.data.status)});
    const interval = setInterval(() => {
      api.get("/settings/ingestion-status").then(res => setIngestionStatus(res.data.status));
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (ingestionStatus === "completed") {
      fetchDocuments();
    }
  }, [ingestionStatus]);

  const fetchDocuments = () => {
    api.get("/documents/").then(res => setDocuments(res.data.documents || []));
  };

  if (ingestionStatus === "in_progress") {
    return <div className="text-yellow-600">Ingestion in progress. Uploads are disabled.</div>;
  }
  if (ingestionStatus === "failed") {
    return <div className="text-red-600">Ingestion failed. Please try again later.</div>;
  }
  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append("files", file);
    try {
      await api.post("/documents/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      fetchDocuments();
      setFile(null);
    } catch {
      // Optionally show error toast
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    setShowConfirm(true);
  };

  const confirmDelete = async () => {
    if (!deletingId) return;
    setLoading(true);
    try {
      await api.delete(`/documents/${deletingId}`);
      fetchDocuments();
    } catch {
      // Optionally show error toast
    } finally {
      setShowConfirm(false);
      setDeletingId(null);
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto bg-white rounded-xl shadow-lg p-8 border">
      <h2 className="text-2xl font-bold text-indigo-700 mb-6">📁 Document Management</h2>
      {/* Guidance Note */}
      <div className="bg-indigo-50 border-l-4 border-indigo-400 p-4 mb-6 rounded">
        <div className="font-semibold text-indigo-800 mb-1">
          Why upload documents?
        </div>
        <div className="text-indigo-700 text-sm">
          For the best AI-powered replies to your customer emails, upload your product documentation, FAQs, policy manuals, or any reference material here. The AI will use these documents to generate more accurate and helpful responses for your support or info email accounts.
        </div>
      </div>
      
      <div className="flex items-center gap-3 mb-8">
        <input
          type="file"
          className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
          onChange={e => setFile(e.target.files?.[0] || null)}
        />
        <Button
          variant="primary"
          onClick={handleUpload}
          disabled={!file || uploading}
          loading={uploading}
        >
          Upload
        </Button>
      </div>
      {loading ? (
        <div className="text-center text-gray-500 py-8">Loading documents...</div>
      ) : documents.length === 0 ? (
        <div className="text-gray-500 text-center py-16 text-lg">
          📂 No documents uploaded yet
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full bg-white rounded-lg shadow">
            <thead>
              <tr className="text-left text-gray-500 text-sm border-b">
                <th className="py-3 px-4 font-semibold">Name</th>
                <th className="py-3 px-4 font-semibold">Uploaded</th>
                <th className="py-3 px-4 font-semibold text-center">Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id} className="border-b hover:bg-indigo-50 transition">
                  <td className="py-3 px-4">{doc.filename}</td>
                  <td className="py-3 px-4 text-xs text-gray-400">
                    {doc.created_at ? new Date(doc.created_at).toLocaleString() : ""}
                  </td>
                  <td className="py-3 px-4 flex gap-2 justify-center">
                    <a
                      href={`/api/documents/${doc.id}/download`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="bg-indigo-100 text-indigo-700 px-3 py-1 rounded text-xs font-semibold hover:bg-indigo-200 transition"
                      download
                    >
                      View/Download
                    </a>
                    <Button
                      variant="danger"
                      className="text-xs px-3 py-1"
                      onClick={() => handleDelete(doc.id)}
                    >
                      Delete
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Confirmation Modal */}
      {showConfirm && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-lg p-8 max-w-xs w-full">
            <div className="text-lg font-semibold mb-4 text-gray-800">Delete Document?</div>
            <div className="text-gray-500 mb-6">Are you sure you want to delete this document? This action cannot be undone.</div>
            <div className="flex justify-end gap-3">
              <Button variant="secondary" onClick={() => setShowConfirm(false)}>
                Cancel
              </Button>
              <Button variant="danger" onClick={confirmDelete} loading={loading}>
                Delete
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentManager;