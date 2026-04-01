interface ProgressBarProps {
  current: number;
  total: number;
  sectionName: string;
}

export function ProgressBar({ current, total, sectionName }: ProgressBarProps) {
  const percentage = Math.round((current / total) * 100);

  return (
    <div className="progress-section">
      <div className="progress-header">
        <span className="progress-title">审计进度</span>
        <span className="progress-stats">{current} / {total} 章节</span>
      </div>

      <div className="progress-bar-container">
        <div
          className="progress-bar-fill"
          style={{ width: `${percentage}%` }}
        />
      </div>

      <p className="progress-current-section">
        <span className="progress-current-label">正在分析：</span>
        {sectionName || '准备中...'}
      </p>
    </div>
  );
}