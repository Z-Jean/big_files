'use client';

interface ProgressBarProps {
  progress: number;
  speed: number;
  remainingTime: number;
  status: string;
}

export default function ProgressBar({ progress, speed, remainingTime, status }: ProgressBarProps) {
  const formatTime = (seconds: number) => {
    if (seconds < 60) {
      return `${Math.round(seconds)}秒`;
    } else if (seconds < 3600) {
      return `${Math.round(seconds / 60)}分${Math.round(seconds % 60)}秒`;
    } else {
      return `${Math.round(seconds / 3600)}时${Math.round((seconds % 3600) / 60)}分`;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'calculating':
        return '计算文件哈希中...';
      case 'uploading':
        return '上传中...';
      case 'paused':
        return '已暂停';
      case 'merging':
        return '合并文件中...';
      case 'completed':
        return '上传完成';
      case 'error':
        return '上传失败';
      default:
        return '';
    }
  };

  return (
    <div className="w-full">
      {/* 进度条 */}
      <div className="w-full bg-gray-200 rounded-full h-4 mb-2">
        <div
          className="bg-blue-500 h-4 rounded-full transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* 进度信息 */}
      <div className="flex justify-between text-sm text-gray-600">
        <div>
          <span className="font-semibold">{getStatusText()}</span>
          <span className="ml-2">{progress.toFixed(1)}%</span>
        </div>
        <div>
          {status === 'uploading' && (
            <>
              <span className="mr-4">速度：{speed.toFixed(2)} MB/s</span>
              <span>剩余：{formatTime(remainingTime)}</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
