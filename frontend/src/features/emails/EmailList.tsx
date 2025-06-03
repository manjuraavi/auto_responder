import React, { useState } from "react";
import Spinner from "../../components/Spinner";
import Button from "../../components/Button";

interface Email {
  id: string;
  subject: string;
  from: string;
  body: string;
  date: string;
  labels: string[];
  is_unread?: boolean;
}

interface EmailListProps {
  emails: Email[];
  loading: boolean;
  onView: (email: Email) => void;
  onSearch: (search: string) => void;
  onRefresh: () => void;
  search: string;
}

const EmailList: React.FC<EmailListProps> = ({
  emails,
  loading,
  onView,
  onSearch,
  onRefresh,
  search,
}) => {
  const [searchTerm, setSearchTerm] = useState(search);

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
    onSearch(e.target.value);
  };

  return (
    <div>
      <div className="flex flex-col md:flex-row items-center mb-6 gap-3">
        <input
          type="text"
          className="border rounded-lg px-4 py-2 flex-1 shadow-sm focus:ring-2 focus:ring-indigo-200"
          placeholder="🔍 Search unread emails"
          value={searchTerm}
          onChange={handleSearch}
        />
        <Button
          variant="primary"
          onClick={onRefresh}
          disabled={loading}
        >
          {loading ? "Refreshing..." : "🔄 Refresh"}
        </Button>
      </div>
      {loading ? (
        <Spinner />
      ) : emails.length === 0 ? (
        <div className="text-gray-500 text-center py-16 text-lg">
          📭 No unread emails found
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg shadow">
          <table className="min-w-full bg-white">
            <tbody>
              {emails.map((email) => {
                const isUnread = email.labels?.includes("UNREAD") || email.is_unread;
                return (
                  <tr
                    key={email.id}
                    className={`cursor-pointer border-b hover:bg-indigo-50 transition group ${
                      isUnread ? "font-bold bg-indigo-50/50" : "font-normal"
                    }`}
                    onClick={() => onView(email)}
                  >
                    {/* Sender */}
                    <td className="py-3 px-4 whitespace-nowrap w-1/5 group-hover:text-indigo-700">
                      {email.from}
                    </td>
                    {/* Subject + Snippet */}
                    <td className="py-3 px-4 w-3/5">
                      <span className="mr-2">{email.subject}</span>
                      <span className="text-gray-500 font-normal">
                        &nbsp;– {email.body.replace(/\s+/g, " ").slice(0, 60)}...
                      </span>
                    </td>
                    {/* Date */}
                    <td className="py-3 px-4 text-xs text-gray-400 text-right w-1/5">
                      {email.date ? new Date(Number(email.date)).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : ""}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default EmailList;