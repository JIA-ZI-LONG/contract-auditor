import React, { useState, useRef } from 'react';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  disabled: boolean;
  selectedFile: File | null;
}

export function FileUpload({ onFileSelect, disabled, selectedFile }: FileUploadProps) {
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.name.endsWith('.docx')) {
        onFileSelect(file);
      } else {
        alert('请上传docx格式文件');
      }
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.name.endsWith('.docx')) {
        onFileSelect(file);
      } else {
        alert('请上传docx格式文件');
      }
    }
  };

  const handleClick = () => {
    inputRef.current?.click();
  };

  return (
    <div
      className={`upload-zone ${dragActive ? 'drag-active' : ''} ${disabled ? 'disabled' : ''}`}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      onClick={handleClick}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".docx"
        onChange={handleChange}
        disabled={disabled}
        style={{ display: 'none' }}
      />

      <div className="upload-icon-wrapper">
        <svg className="upload-icon" viewBox="0 0 24 24">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="12" y1="18" x2="12" y2="12" />
          <line x1="9" y1="15" x2="12" y2="12" />
          <line x1="15" y1="15" x2="12" y2="12" />
        </svg>
      </div>

      {selectedFile ? (
        <p className="upload-text-selected">{selectedFile.name}</p>
      ) : (
        <>
          <p className="upload-text">点击或拖拽上传合同文件</p>
          <p className="upload-hint">仅支持 .docx 格式</p>
        </>
      )}
    </div>
  );
}