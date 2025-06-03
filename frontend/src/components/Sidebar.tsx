import Button from "./Button";
import appLogo from "../assets/app_logo.jpg";

interface SidebarProps {
  user: { email?: string };
  onLogout: () => void;
  tab: "emails" | "documents" | "settings" | "help";
  setTab: (tab: "emails" | "documents" | "settings" | "help") => void;
}

const navItems = [
  { label: "Emails", icon: "", value: "emails" },
  { label: "Documents", icon: "", value: "documents" },
  { label: "Settings", icon: "", value: "settings" },
  { label: "Help", icon: "", value: "help" },
];

const Sidebar: React.FC<SidebarProps> = ({ user, onLogout, tab, setTab }) => {
  return (
    <aside className="w-72 bg-white border-r shadow-lg flex flex-col min-h-screen">
      <div className="flex flex-col items-center py-8">
        <img src={appLogo} alt="Logo" className="w-12 h-12 mb-2" />
        <div className="text-lg font-bold text-indigo-700 mb-1">AutoResponder</div>
        <div className="text-xs text-gray-400 mb-4">{user.email}</div>
      </div>
      <nav className="flex-1">
        <ul>
          {navItems.map((item) => (
            <li key={item.value}>
              <button
                className={`w-full flex items-center gap-3 px-8 py-3 text-left text-base font-medium rounded-r-full transition ${
                  tab === item.value
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-gray-600 hover:bg-indigo-50"
                }`}
                onClick={() =>
                  setTab(item.value as "emails" | "documents" | "settings" | "help")
                }
              >
                <span className="text-xl">{item.icon}</span>
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      </nav>
      <div className="p-6">
        <Button variant="secondary" className="w-full" onClick={onLogout}>
          Log out
        </Button>
      </div>
    </aside>
  );
};

export default Sidebar;