interface DownloadButtonProps {
  blob: Blob;
  filename: string;
  onReset: () => void;
}

export function DownloadButton({ blob, filename, onReset }: DownloadButtonProps) {
  const handleDownload = () => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="download-container">
      <button className="download-btn" onClick={handleDownload}>
        📥 下载审计报告
      </button>
      <button className="reset-btn" onClick={onReset}>
        重新审计
      </button>
    </div>
  );
}