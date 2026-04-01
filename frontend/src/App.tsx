import React, { useState } from 'react';
import { FileUpload } from './components/FileUpload';
import { ProgressBar } from './components/ProgressBar';
import { DownloadButton } from './components/DownloadButton';
import { uploadContract } from './api/upload';
import './App.css';

type Status = 'idle' | 'uploading' | 'processing' | 'done' | 'error';

export function App() {
  const [status, setStatus] = useState<Status>('idle');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [resultBlob, setResultBlob] = useState<Blob | null>(null);
  const [error, setError] = useState<string>('');
  const [progress, setProgress] = useState({ current: 0, total: 0, section: '' });

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setStatus('idle');
    setError('');
  };

  const handleStart = async () => {
    if (!selectedFile) return;

    setStatus('uploading');
    setError('');

    try {
      const blob = await uploadContract(selectedFile);
      setResultBlob(blob);
      setStatus('done');
    } catch (err) {
      setStatus('error');
      setError(err instanceof Error ? err.message : '审计失败，请重试');
    }
  };

  const handleReset = () => {
    setStatus('idle');
    setSelectedFile(null);
    setResultBlob(null);
    setError('');
    setProgress({ current: 0, total: 0, section: '' });
  };

  return (
    <div className="container">
      <h1 className="title">税务合同审计助手</h1>

      <FileUpload
        onFileSelect={handleFileSelect}
        disabled={status === 'uploading' || status === 'processing'}
      />

      {status === 'idle' && selectedFile && (
        <button
          className="btn start-btn"
          onClick={handleStart}
          disabled={!selectedFile}
        >
          开始审计
        </button>
      )}

      {(status === 'uploading' || status === 'processing') && (
        <ProgressBar
          current={progress.current}
          total={progress.total}
          sectionName={progress.section}
        />
      )}

      {status === 'error' && (
        <p className="error-message">{error}</p>
      )}

      {status === 'done' && resultBlob && (
        <DownloadButton
          blob={resultBlob}
          filename="审计报告.docx"
          onReset={handleReset}
        />
      )}
    </div>
  );
}

export default App;