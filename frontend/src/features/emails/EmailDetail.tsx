import React from "react";
import Button from "../../components/Button";
import api from "../../services/api";
import { toast } from "react-toastify";

interface Email {
  id: string;
  subject: string;
  from: string;
  body: string;
  date: string;
  labels: string[];
  is_unread?: boolean;
}

interface EmailDetailProps {
  email: Email;
  onBack: () => void;
  onSent?: () => void;
  token?: string | null;
  hasDocuments?: boolean;
}

const EmailDetail: React.FC<EmailDetailProps> = ({ email, onBack, onSent, hasDocuments }) => {
  const [aiResponse, setAiResponse] = React.useState("");
  const [editing, setEditing] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [showSentPopup, setShowSentPopup] = React.useState(false);

  const handleAutoRespond = async () => {
    if (!hasDocuments) {
      toast.info("Please upload at least one document before generating AI responses. Go to the Documents tab to upload product docs, FAQs, or policies.");
      return;
    }
    setLoading(true);
    try {
      const res = await api.post(`/emails/${email.id}/generate-response`);
      setAiResponse(res.data.content);
      setEditing(true);
    } catch (e) {
      setAiResponse("Failed to generate AI response.");
      setEditing(true);
    } finally {
      setLoading(false);
    }
  };

  const handleSendResponse = async () => {
    setLoading(true);
    try {
      await api.post(`/emails/${email.id}/reply`, {
        content: aiResponse,
        use_generated: true,
      });
      // Optionally, mark as read if not handled by backend:
      // await api.post(`/emails/${email.id}/mark-read`);
      setAiResponse("");
      setEditing(false);
      setShowSentPopup(true);
    } catch (e) {
      toast.error("Failed to send response.");
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setEditing(false);
    setAiResponse("");
  };

  return (
    <div className="w-full max-w-4xl mx-auto bg-white rounded-xl shadow border border-gray-100 mt-4">
      {/* Header: Back, Subject, Date */}
      <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4 bg-gray-50 rounded-t-xl">
        <button
          className="text-indigo-600 hover:bg-indigo-50 px-2 py-1 rounded transition text-sm font-medium"
          onClick={onBack}
        >
          ← Back
        </button>
        <span className="text-xs text-gray-400 font-mono">
          {email.date ? new Date(Number(email.date)).toLocaleString() : ""}
        </span>
      </div>
      {/* Subject */}
      <div className="px-6 pt-6 pb-2 border-b border-gray-100 bg-white">
        <h2 className="text-2xl font-bold text-gray-900 mb-1">{email.subject}</h2>
        <div className="flex items-center gap-2 mb-1">
          <span className="font-semibold text-gray-700">{email.from}</span>
          {email.labels?.includes("UNREAD") || email.is_unread ? (
            <span className="ml-2 bg-red-50 text-red-500 px-2 py-0.5 rounded-full text-xs font-semibold border border-red-100">
              Unread
            </span>
          ) : null}
        </div>
      </div>
      {/* Body */}
      <div className="px-6 py-6 whitespace-pre-line text-gray-800 text-base leading-relaxed bg-white">
        {email.body}
        {/* AI Response Editor */}
        {!editing && !hasDocuments && (
          <div className="px-6 pb-2 text-red-600 text-sm">
            Please upload at least one document in the Documents tab to enable AI-powered responses.
          </div>
        )}
        {editing && (
          <div className="mt-6 p-4 bg-indigo-50 rounded text-indigo-800">
            <div className="font-semibold mb-2">AI Suggested Response:</div>
            <textarea
              className="w-full rounded border p-2 text-gray-800 bg-white mb-4"
              rows={5}
              value={aiResponse}
              onChange={e => setAiResponse(e.target.value)}
              disabled={loading}
            />
            <div className="flex gap-3 justify-end">
              <Button
                variant="primary"
                className="shadow-sm"
                onClick={handleSendResponse}
                loading={loading}
                disabled={!aiResponse.trim()}
              >
                Approve &amp; Send
              </Button>
              <Button
                variant="secondary"
                className="shadow-sm"
                onClick={handleCancel}
                disabled={loading}
              >
                Cancel
              </Button>
            </div>
          </div>
        )}
      </div>
      
      {/* Actions */}
      {!editing && (
        <div className="flex justify-end gap-3 px-6 pb-6 pt-2 bg-white rounded-b-xl border-t border-gray-100">
          
          <Button
            variant="primary"
            className="shadow-sm"
            onClick={handleAutoRespond}
            loading={loading}
            disabled={!hasDocuments}
          >
            🤖 Generate Response
          </Button>
        </div>
      )}

      {/* Sent Popup Modal */}
      {showSentPopup && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="bg-white rounded-xl shadow-lg p-8 max-w-xs w-full flex flex-col items-center">
            <div className="text-2xl mb-4 text-green-600">✅</div>
            <div className="text-lg font-semibold mb-4 text-gray-800">Response sent!</div>
            <Button
              variant="primary"
              className="w-full"
              onClick={() => {
                setShowSentPopup(false);
                if (onSent) onSent();
                onBack();
              }}
            >
              OK
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default EmailDetail;