import React, { useState, useEffect } from "react";
import api from "../services/api";

const SettingsPage: React.FC = () => {
  const [toggle, setToggle] = useState(false);
  const [ingestionStatus, setIngestionStatus] = useState("idle");
  const [loading, setLoading] = useState(false);

   useEffect(() => {
    api.get("/settings/ingest-toggle").then(res => setToggle(res.data.enabled));
    api.get("/settings/ingestion-status").then(res => setIngestionStatus(res.data.status));
  }, []);

  useEffect(() => {
    if (toggle) {
      const interval = setInterval(() => {
        api.get("/settings/ingestion-status").then(res => setIngestionStatus(res.data.status));
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [toggle]);

  const handleToggle = async () => {
    setLoading(true);
    await api.post("/settings/ingest-toggle", { enabled: !toggle });
    setToggle(!toggle);
    setLoading(false);
  };

  

  return (
    <div className="max-w-xl mx-auto bg-white rounded-xl shadow p-8 border mt-8">
      <h2 className="text-2xl font-bold mb-6 text-indigo-700">Settings</h2>
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="font-semibold text-gray-800 mb-1">
            Enable email ingestion
          </div>
          <div className="text-gray-500 text-sm">
            Enable this to allow the system to use your entire email history for more precise customer support responses.
          </div>
        </div>
        <label className="inline-flex items-center cursor-pointer relative">
          <input
            type="checkbox"
            className="sr-only peer"
            checked={toggle}
            onChange={handleToggle}
            disabled={ingestionStatus === "in_progress" || loading}
          />
          <div className="w-11 h-6 bg-gray-200 rounded-full peer peer-checked:bg-indigo-600 transition"></div>
          <div className={`absolute ml-1 mt-1 w-4 h-4 bg-white rounded-full shadow transform transition peer-checked:translate-x-5`}></div>
        </label>
        {ingestionStatus === "in_progress" && (
          <div className="text-yellow-600 text-sm mt-2">
            Ingestion in progress. Please wait before turning it off.
          </div>
          )}
      </div>
      {status && (
        <div className="text-sm text-indigo-700 mt-2">{status}</div>
      )}
    </div>
  );
};

export default SettingsPage;
