import React, { useState, ReactNode } from 'react';

type Tab = {
    label: string;
    content: ReactNode;
};

type TabsProps = {
    tabs: Tab[];
    initialIndex?: number;
    className?: string;
};

const Tabs: React.FC<TabsProps> = ({ tabs, initialIndex = 0, className }) => {
    const [activeIndex, setActiveIndex] = useState(initialIndex);

    return (
        <div className={className}>
            <div style={{ display: 'flex', borderBottom: '1px solid #ccc' }}>
                {tabs.map((tab, idx) => (
                    <button
                        key={tab.label}
                        onClick={() => setActiveIndex(idx)}
                        style={{
                            padding: '8px 16px',
                            border: 'none',
                            borderBottom: activeIndex === idx ? '2px solid #007bff' : '2px solid transparent',
                            background: 'none',
                            cursor: 'pointer',
                            fontWeight: activeIndex === idx ? 'bold' : 'normal',
                            outline: 'none',
                        }}
                        aria-selected={activeIndex === idx}
                        aria-controls={`tab-panel-${idx}`}
                        id={`tab-${idx}`}
                        role="tab"
                    >
                        {tab.label}
                    </button>
                ))}
            </div>
            <div
                id={`tab-panel-${activeIndex}`}
                role="tabpanel"
                aria-labelledby={`tab-${activeIndex}`}
                style={{ padding: '16px' }}
            >
                {tabs[activeIndex]?.content}
            </div>
        </div>
    );
};

export default Tabs;