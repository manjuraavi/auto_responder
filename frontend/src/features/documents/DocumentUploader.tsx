import React, { useRef, useState } from 'react';

interface DocumentUploaderProps {
    onUpload: (file: File) => void;
}

const DocumentUploader: React.FC<DocumentUploaderProps> = ({ onUpload }) => {
    const fileInputRef = useRef<HTMLInputElement | null>(null);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            setSelectedFile(file);
            setError(null);
        }
    };

    const handleUpload = () => {
        if (!selectedFile) {
            setError('Please select a file to upload.');
            return;
        }
        onUpload(selectedFile);
        setSelectedFile(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    return (
        <div>
            <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept=".pdf,.doc,.docx,.txt"
            />
            <button onClick={handleUpload}>Upload</button>
            {selectedFile && <div>Selected: {selectedFile.name}</div>}
            {error && <div style={{ color: 'red' }}>{error}</div>}
        </div>
    );
};

export default DocumentUploader;