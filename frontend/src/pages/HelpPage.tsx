import React from "react";

const HelpPage: React.FC = () => {
  return (
    <div className="max-w-xl mx-auto bg-white rounded-xl shadow p-8 border mt-8">
      <h2 className="text-2xl font-bold mb-6 text-indigo-700">Help & Support</h2>
      <div className="text-gray-700 space-y-4">
        <p>
          <b>How does AutoResponder work?</b><br />
          Connect your Gmail or Google Workspace account, and let our AI generate and send replies to your customer emails automatically.
        </p>
        <p>
          <b>How do I use the AI response feature?</b><br />
          Click on an unread email, then click "Generate Response". Review, edit, and approve before sending.
        </p>
        <div className="bg-indigo-50 p-4 rounded mb-4">
          <b>Improve AI replies with your documents</b>
          <p className="mt-1 text-sm text-gray-700">
            For more accurate and helpful responses, upload your company FAQs, manuals, or policy documents using the <b>Documents</b> tab in the sidebar. The AI will use these to generate better replies to your customer emails.
          </p>
        </div>
        <p>
          <b>Need more help?</b><br />
          Contact us at <a href="mailto:support@yourdomain.com" className="text-indigo-600 underline">support@yourdomain.com</a>
        </p>
      </div>
    </div>
  );
};

export default HelpPage;