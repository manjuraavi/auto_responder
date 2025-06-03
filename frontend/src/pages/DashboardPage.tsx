import React, { useEffect, useState, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import EmailDetail from "../features/emails/EmailDetail";
import EmailList from "../features/emails/EmailList";
import DocumentManager from "../features/documents/DocumentManager";
import Sidebar from "../components/Sidebar";
import api from "../services/api";
import HelpPage from "./HelpPage";
import SettingsPage from "./SettingsPage";

const DashboardPage: React.FC = () => {
  const { user, logout } = useAuth();
  const [tab, setTab] = useState<"emails" | "documents" | "settings" | "help">("emails");
  const [selectedEmail, setSelectedEmail] = useState<any>(null);
  const [refreshEmails, setRefreshEmails] = useState(false);
  const [search, setSearch] = useState("");
  const [emails, setEmails] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasDocuments, setHasDocuments] = useState<boolean>(true);
  const hasRedirectedToDocs = useRef(false);

  useEffect(() => {
    // Check if user has documents on mount and when switching tabs
    if (!hasRedirectedToDocs.current) {
      api.get("/documents/").then((res) => {
        if ((res.data.documents || []).length === 0) {
          setTab("documents");
          hasRedirectedToDocs.current = true;
        }
      });
    }
  }, []);

  useEffect(() => {
    api.get("/documents/").then((res) => {
      setHasDocuments((res.data.documents || []).length > 0);
    });
  }, [tab]);

  useEffect(() => {
    if (tab === "emails") {
      setLoading(true);
      api
        .get(`/emails/`, {
          params: {
            unread_only: true,
            search: search || undefined,
          },
        })
        .then((res) => setEmails(res.data.emails || []))
        .catch(() => setEmails([]))
        .finally(() => setLoading(false));
    }
  }, [tab, refreshEmails, search]);

  return (
    <div className="flex min-h-screen bg-gradient-to-br from-gray-50 to-indigo-50">
      <Sidebar
        user={user || { email: "" }}
        onLogout={logout}
        tab={tab}
        setTab={setTab}
      />
      <main className="flex-1 p-8 max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-indigo-700 tracking-tight">
            {tab === "emails"
              ? "Email Dashboard"
              : tab === "documents"
              ? "Document Management"
              : tab === "settings"
              ? "Settings"
              : tab === "help"
              ? "Help"
              : ""}
          </h1>
        </div>
        {tab === "emails" ? (
          selectedEmail ? (
            <EmailDetail
              email={selectedEmail}
              onBack={() => setSelectedEmail(null)}
              onSent={() => setRefreshEmails((r) => !r)}
              hasDocuments={hasDocuments}
            />
          ) : (
            <EmailList
              emails={emails}
              loading={loading}
              onView={setSelectedEmail}
              onSearch={setSearch}
              onRefresh={() => setRefreshEmails((r) => !r)}
              search={search}
            />
          )
        ) : tab === "documents" ? (
          <DocumentManager />
        ) : tab === "settings" ? (
          <SettingsPage />
        ): tab === "help" ? (
          <HelpPage />
        ) : null}
      </main>
    </div>
  );
};

export default DashboardPage;