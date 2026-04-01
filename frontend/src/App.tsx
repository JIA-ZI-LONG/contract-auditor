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
    <div className="app-container">
      {/* Hero Header */}
      <header className="hero">
        <div className="hero-content">
          <h1 className="hero-title">税务合同审计助手</h1>
          <div className="gold-line" />
          <p className="hero-subtitle">智能合规分析 · 专业风险识别</p>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {/* Upload Card */}
        <div className={`upload-card ${status === 'uploading' ? 'processing-overlay' : ''}`}>
          <FileUpload
            onFileSelect={handleFileSelect}
            disabled={status === 'uploading' || status === 'processing'}
            selectedFile={selectedFile}
          />

          {status === 'idle' && selectedFile && (
            <div style={{ textAlign: 'center' }}>
              <button
                className="btn-primary"
                onClick={handleStart}
                disabled={!selectedFile}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9 18l6-6-6-6" />
                </svg>
                开始审计
              </button>
            </div>
          )}

          {(status === 'uploading' || status === 'processing') && (
            <ProgressBar
              current={progress.current}
              total={progress.total}
              sectionName={progress.section}
            />
          )}

          {status === 'error' && (
            <div className="error-section">
              <svg className="error-icon" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
              </svg>
              <p className="error-message">{error}</p>
              <button className="btn-secondary" onClick={handleReset} style={{ marginTop: '1rem' }}>
                重新上传
              </button>
            </div>
          )}
        </div>

        {/* Success State */}
        {status === 'done' && resultBlob && (
          <div className="success-section">
            <div className="success-icon-wrapper">
              <svg className="success-icon" viewBox="0 0 24 24">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </div>
            <h2 className="success-title">审计完成</h2>
            <p className="success-subtitle">您的合同合规性审计报告已生成</p>
            <DownloadButton
              blob={resultBlob}
              filename="审计报告.docx"
              onReset={handleReset}
            />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="footer">
        <p className="footer-text">
          Powered by <span className="footer-brand">EY-Technology Risk and Data Analytics</span> · 专业税务合规智能分析
        </p>
      </footer>
    </div>
  );
}

export default App;