interface ProgressBarProps {
  current: number;
  total: number;
  sectionName: string;
}

export function ProgressBar({ current, total, sectionName }: ProgressBarProps) {
  const percentage = Math.round((current / total) * 100);

  return (
    <div className="progress-container">
      <div className="progress-info">
        <span>处理进度:</span>
        <span>{current}/{total} 章节</span>
      </div>
      <div className="progress-bar">
        <div
          className="progress-fill"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <p className="progress-section">正在分析: {sectionName}</p>
    </div>
  );
}