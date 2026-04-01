const API_BASE = 'http://localhost:8002';

export interface ProgressEvent {
  stage: string;
  current: number;
  total: number;
  section: string;
  message?: string;
}

export function uploadContractWithProgress(
  file: File,
  onProgress: (event: ProgressEvent) => void
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);

    fetch(`${API_BASE}/api/upload-stream`, {
      method: 'POST',
      body: formData,
    }).then(response => {
      if (!response.ok) {
        reject(new Error('上传失败'));
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        reject(new Error('无法读取响应'));
        return;
      }

      const decoder = new TextDecoder();
      let buffer = '';

      const processChunk = ({ done, value }: ReadableStreamReadResult<Uint8Array>): Promise<void> | void => {
        if (done) {
          resolve(new Blob());
          return;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event: ProgressEvent = JSON.parse(line.slice(6));

              if (event.stage === 'done') {
                // 下载报告
                fetch(`${API_BASE}/api/download/审计报告.docx`)
                  .then(res => res.blob())
                  .then(blob => resolve(blob))
                  .catch(() => resolve(new Blob()));
                return;
              }

              if (event.stage === 'error') {
                reject(new Error(event.message || '处理失败'));
                return;
              }

              onProgress(event);
            } catch (e) {
              // 忽略解析错误
            }
          }
        }

        return reader.read().then(processChunk);
      };

      reader.read().then(processChunk);
    }).catch(reject);
  });
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/api/health`);
    return response.ok;
  } catch {
    return false;
  }
}