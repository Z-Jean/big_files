'use client';

import { useState, useRef } from 'react';
import ProgressBar from './ProgressBar';

interface UploadItem {
  file: File;
  md5: string;
  totalChunks: number;
  uploadedChunks: number[];
  currentChunk: number;
  status: 'idle' | 'calculating' | 'uploading' | 'paused' | 'merging' | 'completed' | 'error';
  progress: number;
  speed: number;
  remainingTime: number;
  error: string | null;
}

const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB

interface FileUploadProps {
  onUploadComplete?: () => void;
}

export default function FileUpload({ onUploadComplete }: FileUploadProps) {
  const [uploadQueue, setUploadQueue] = useState<UploadItem[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const isPausedRef = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  // 计算文件 MD5（使用 Web Worker）
  const calculateMD5 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      if (typeof Worker === 'undefined') {
        calculateMD5MainThread(file).then(resolve).catch(reject);
        return;
      }

      try {
        const worker = new Worker('/md5-worker.js');

        worker.onmessage = (e) => {
          const { type, md5, error } = e.data;
          if (type === 'complete') {
            worker.terminate();
            resolve(md5);
          } else if (type === 'error') {
            worker.terminate();
            reject(new Error(error));
          }
        };

        worker.onerror = () => {
          worker.terminate();
          calculateMD5MainThread(file).then(resolve).catch(reject);
        };

        worker.postMessage({ file });
      } catch {
        calculateMD5MainThread(file).then(resolve).catch(reject);
      }
    });
  };

  // 主线程计算 MD5（降级方案）
  const calculateMD5MainThread = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const spark = new (window as any).SparkMD5.ArrayBuffer();
      const reader = new FileReader();
      const chunkSize = 2 * 1024 * 1024;
      let currentChunk = 0;
      const totalChunks = Math.ceil(file.size / chunkSize);

      const loadNext = () => {
        const start = currentChunk * chunkSize;
        const end = Math.min(start + chunkSize, file.size);
        reader.readAsArrayBuffer(file.slice(start, end));
      };

      reader.onload = (e) => {
        spark.append(e.target?.result);
        currentChunk++;
        if (currentChunk < totalChunks) {
          loadNext();
        } else {
          resolve(spark.end());
        }
      };

      reader.onerror = reject;
      loadNext();
    });
  };

  // 获取 token
  const getToken = () => localStorage.getItem('token');

  // 秒传检测
  const checkFileExists = async (md5: string, fileSize: number) => {
    const response = await fetch(`/api/upload/check?md5=${md5}&file_size=${fileSize}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${getToken()}` },
    });
    return response.json();
  };

  // 查询已上传分片
  const getUploadedChunks = async (md5: string) => {
    const response = await fetch(`/api/upload/chunks/${md5}`, {
      headers: { 'Authorization': `Bearer ${getToken()}` },
    });
    return response.json();
  };

  // 上传单个分片
  const uploadChunk = async (chunk: Blob, md5: string, index: number, totalChunks: number) => {
    abortControllerRef.current = new AbortController();

    const formData = new FormData();
    formData.append('md5', md5);
    formData.append('chunk_index', index.toString());
    formData.append('total_chunks', totalChunks.toString());
    formData.append('chunk', chunk);

    const response = await fetch('/api/upload/chunk', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${getToken()}` },
      body: formData,
      signal: abortControllerRef.current.signal,
    });

    if (!response.ok) {
      throw new Error('分片上传失败');
    }

    return response.json();
  };

  // 合并分片
  const mergeChunks = async (md5: string, filename: string, totalChunks: number) => {
    const formData = new FormData();
    formData.append('md5', md5);
    formData.append('filename', filename);
    formData.append('total_chunks', totalChunks.toString());

    const response = await fetch('/api/upload/merge', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${getToken()}` },
      body: formData,
    });

    return response.json();
  };

  // 取消上传
  const cancelUpload = async (md5: string) => {
    await fetch(`/api/upload/cancel/${md5}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${getToken()}` },
    });
  };

  // 更新队列中某个文件的状态
  const updateQueueItem = (file: File, updates: Partial<UploadItem>) => {
    setUploadQueue(prev => {
      const newQueue = [...prev];
      const index = prev.findIndex(p => p.file === file);
      if (index !== -1) {
        newQueue[index] = { ...newQueue[index], ...updates };
      }
      return newQueue;
    });
  };

  // 开始上传单个文件
  const startUpload = async (item: UploadItem) => {
    const { file, md5, totalChunks, uploadedChunks } = item;

    updateQueueItem(file, { status: 'uploading' });

    const startTime = Date.now();
    let uploadedSize = 0;

    try {
      for (let i = 0; i < totalChunks; i++) {
        // 跳过已上传的分片
        if (uploadedChunks.includes(i)) {
          uploadedSize += CHUNK_SIZE;
          continue;
        }

        // 检查是否暂停
        if (isPausedRef.current) {
          return;
        }

        const start = i * CHUNK_SIZE;
        const end = Math.min(start + CHUNK_SIZE, file.size);
        const chunk = file.slice(start, end);

        await uploadChunk(chunk, md5, i, totalChunks);

        uploadedSize += CHUNK_SIZE;
        const progress = Math.min((uploadedSize / file.size) * 100, 100);
        const elapsed = (Date.now() - startTime) / 1000;
        const speed = uploadedSize / elapsed / 1024 / 1024;
        const remainingSize = file.size - uploadedSize;
        const remainingTime = remainingSize / (speed * 1024 * 1024);

        updateQueueItem(file, {
          currentChunk: i + 1,
          progress,
          speed,
          remainingTime,
          uploadedChunks: [...uploadedChunks, i],
        });
      }

      // 所有分片上传完成，开始合并
      updateQueueItem(file, { status: 'merging' });

      await mergeChunks(md5, file.name, totalChunks);

      updateQueueItem(file, { status: 'completed', progress: 100 });

      // 通知父组件刷新文件列表
      onUploadComplete?.();

      // 开始下一个上传
      startNextUpload();
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        return;
      }

      updateQueueItem(file, {
        status: 'error',
        error: err instanceof Error ? err.message : '上传失败',
      });
    }
  };

  // 开始下一个上传
  const startNextUpload = () => {
    const nextItem = uploadQueue.find(item => item.status === 'idle' && item.md5);
    if (nextItem) {
      startUpload(nextItem);
    }
  };

  // 处理文件选择（支持多选）
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    // 检查文件大小
    const oversizedFiles = Array.from(files).filter(f => f.size > 2 * 1024 * 1024 * 1024);
    if (oversizedFiles.length > 0) {
      alert(`以下文件超过 2GB 限制：\n${oversizedFiles.map(f => f.name).join('\n')}`);
      return;
    }

    // 创建上传队列
    const newItems: UploadItem[] = Array.from(files).map(file => ({
      file,
      md5: '',
      totalChunks: 0,
      uploadedChunks: [],
      currentChunk: 0,
      status: 'calculating',
      progress: 0,
      speed: 0,
      remainingTime: 0,
      error: null,
    }));

    setUploadQueue(prev => [...prev, ...newItems]);

    // 为每个文件计算 MD5 并准备上传
    for (const item of newItems) {
      try {
        const md5 = await calculateMD5(item.file);
        const totalChunks = Math.ceil(item.file.size / CHUNK_SIZE);

        updateQueueItem(item.file, { md5, totalChunks, status: 'idle' });

        // 检查是否秒传
        const checkResult = await checkFileExists(md5, item.file.size);
        if (checkResult.exists) {
          updateQueueItem(item.file, { status: 'completed', progress: 100 });
          continue;
        }

        // 查询已上传分片
        const chunksResult = await getUploadedChunks(md5);
        const uploadedChunks = chunksResult.uploaded_chunks || [];

        updateQueueItem(item.file, { uploadedChunks });
      } catch (err) {
        updateQueueItem(item.file, {
          status: 'error',
          error: err instanceof Error ? err.message : '上传失败',
        });
      }
    }

    // 开始上传第一个未完成的文件
    startNextUpload();
  };

  // 暂停上传
  const handlePause = () => {
    isPausedRef.current = true;
    setIsPaused(true);
    abortControllerRef.current?.abort();
  };

  // 继续上传
  const handleResume = () => {
    isPausedRef.current = false;
    setIsPaused(false);
    startNextUpload();
  };

  // 取消所有上传
  const handleCancelAll = async () => {
    for (const item of uploadQueue) {
      if (item.md5 && item.status !== 'completed') {
        await cancelUpload(item.md5);
      }
    }
    setUploadQueue([]);
    setIsPaused(false);
    isPausedRef.current = false;
  };

  // 获取当前正在上传的文件
  const currentUploading = uploadQueue.find(item => item.status === 'uploading' || item.status === 'paused');
  const hasUploading = uploadQueue.some(item => item.status === 'uploading');
  const hasPaused = uploadQueue.some(item => item.status === 'paused');
  const hasIdle = uploadQueue.some(item => item.status === 'idle' && item.md5);

  return (
    <div>
      {/* 文件选择区域 */}
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center mb-4">
        <input
          type="file"
          onChange={handleFileSelect}
          className="hidden"
          id="file-input"
          multiple
          disabled={hasUploading}
        />
        <label
          htmlFor="file-input"
          className="cursor-pointer text-gray-600 hover:text-gray-800"
        >
          <div>
            <p className="text-lg">点击选择文件或拖拽文件到这里</p>
            <p className="text-sm text-gray-500">支持多选，所有格式，最大 2GB</p>
          </div>
        </label>
      </div>

      {/* 上传队列 */}
      {uploadQueue.length > 0 && (
        <div className="mb-4 space-y-3">
          {uploadQueue.map((item, index) => (
            <div key={index} className="border rounded-lg p-3">
              <div className="flex justify-between items-center mb-2">
                <div className="flex-1">
                  <p className="font-medium truncate">{item.file.name}</p>
                  <p className="text-sm text-gray-500">
                    {(item.file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
                <div className="ml-4">
                  {item.status === 'completed' && (
                    <span className="text-green-600">✅ 完成</span>
                  )}
                  {item.status === 'error' && (
                    <span className="text-red-600">❌ {item.error}</span>
                  )}
                  {item.status === 'calculating' && (
                    <span className="text-blue-600">⏳ 计算中...</span>
                  )}
                  {item.status === 'merging' && (
                    <span className="text-blue-600">⏳ 合并中...</span>
                  )}
                </div>
              </div>

              {(item.status === 'uploading' || item.status === 'paused') && (
                <ProgressBar
                  progress={item.progress}
                  speed={item.speed}
                  remainingTime={item.remainingTime}
                  status={item.status}
                />
              )}

              {item.status === 'uploading' && (
                <p className="text-sm text-gray-500 mt-1">
                  分片：{item.currentChunk} / {item.totalChunks}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 控制按钮 */}
      <div className="flex gap-4">
        {hasIdle && !hasUploading && (
          <button
            onClick={startNextUpload}
            className="bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600"
          >
            开始上传
          </button>
        )}

        {hasUploading && (
          <button
            onClick={handlePause}
            className="bg-yellow-500 text-white px-4 py-2 rounded-md hover:bg-yellow-600"
          >
            暂停
          </button>
        )}

        {hasPaused && (
          <button
            onClick={handleResume}
            className="bg-green-500 text-white px-4 py-2 rounded-md hover:bg-green-600"
          >
            继续
          </button>
        )}

        {uploadQueue.length > 0 && (
          <button
            onClick={handleCancelAll}
            className="bg-red-500 text-white px-4 py-2 rounded-md hover:bg-red-600"
          >
            取消全部
          </button>
        )}
      </div>
    </div>
  );
}
