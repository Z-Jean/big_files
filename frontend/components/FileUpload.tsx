'use client';

import { useState, useRef } from 'react';
import ProgressBar from './ProgressBar';

interface UploadState {
  file: File | null;
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
  const [uploadState, setUploadState] = useState<UploadState>({
    file: null,
    md5: '',
    totalChunks: 0,
    uploadedChunks: [],
    currentChunk: 0,
    status: 'idle',
    progress: 0,
    speed: 0,
    remainingTime: 0,
    error: null,
  });

  const [isPaused, setIsPaused] = useState(false);
  const isPausedRef = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  // 计算文件 MD5（使用 Web Worker）
  const calculateMD5 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      // 检查是否支持 Web Worker
      if (typeof Worker === 'undefined') {
        // 降级到主线程计算
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

        worker.onerror = (e) => {
          worker.terminate();
          // 降级到主线程计算
          calculateMD5MainThread(file).then(resolve).catch(reject);
        };

        worker.postMessage({ file });
      } catch (err) {
        // Worker 创建失败，降级到主线程
        calculateMD5MainThread(file).then(resolve).catch(reject);
      }
    });
  };

  // 主线程计算 MD5（降级方案）
  const calculateMD5MainThread = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const spark = new (window as any).SparkMD5.ArrayBuffer();
      const reader = new FileReader();
      const chunkSize = 2 * 1024 * 1024; // 2MB
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
      headers: {
        'Authorization': `Bearer ${getToken()}`,
      },
    });
    return response.json();
  };

  // 查询已上传分片
  const getUploadedChunks = async (md5: string) => {
    const response = await fetch(`/api/upload/chunks/${md5}`, {
      headers: {
        'Authorization': `Bearer ${getToken()}`,
      },
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
      headers: {
        'Authorization': `Bearer ${getToken()}`,
      },
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
      headers: {
        'Authorization': `Bearer ${getToken()}`,
      },
      body: formData,
    });

    return response.json();
  };

  // 取消上传
  const cancelUpload = async (md5: string) => {
    await fetch(`/api/upload/cancel/${md5}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${getToken()}`,
      },
    });
  };

  // 处理文件选择
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // 检查文件大小
    if (file.size > 2 * 1024 * 1024 * 1024) {
      setUploadState(prev => ({
        ...prev,
        error: '文件大小超过 2GB 限制',
      }));
      return;
    }

    setUploadState(prev => ({
      ...prev,
      file,
      status: 'calculating',
      error: null,
    }));

    try {
      // 计算 MD5
      const md5 = await calculateMD5(file);
      const totalChunks = Math.ceil(file.size / CHUNK_SIZE);

      setUploadState(prev => ({
        ...prev,
        md5,
        totalChunks,
        status: 'idle',
      }));

      // 检查是否秒传
      const checkResult = await checkFileExists(md5, file.size);
      if (checkResult.exists) {
        setUploadState(prev => ({
          ...prev,
          status: 'completed',
          progress: 100,
        }));
        return;
      }

      // 查询已上传分片
      const chunksResult = await getUploadedChunks(md5);
      const uploadedChunks = chunksResult.uploaded_chunks || [];

      setUploadState(prev => ({
        ...prev,
        uploadedChunks,
      }));

      // 开始上传
      await startUpload(file, md5, totalChunks, uploadedChunks);
    } catch (err) {
      setUploadState(prev => ({
        ...prev,
        status: 'error',
        error: err instanceof Error ? err.message : '上传失败',
      }));
    }
  };

  // 开始上传
  const startUpload = async (
    file: File,
    md5: string,
    totalChunks: number,
    uploadedChunks: number[]
  ) => {
    setUploadState(prev => ({
      ...prev,
      status: 'uploading',
    }));

    const startTime = Date.now();
    let uploadedSize = 0;

    try {
      for (let i = 0; i < totalChunks; i++) {
        // 跳过已上传的分片
        if (uploadedChunks.includes(i)) {
          uploadedSize += CHUNK_SIZE;
          continue;
        }

        // 检查是否暂停（使用 ref 获取最新值）
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
        const speed = uploadedSize / elapsed / 1024 / 1024; // MB/s
        const remainingSize = file.size - uploadedSize;
        const remainingTime = remainingSize / (speed * 1024 * 1024);

        setUploadState(prev => ({
          ...prev,
          currentChunk: i + 1,
          progress,
          speed,
          remainingTime,
          uploadedChunks: [...prev.uploadedChunks, i],
        }));
      }

      // 所有分片上传完成，开始合并
      setUploadState(prev => ({
        ...prev,
        status: 'merging',
      }));

      await mergeChunks(md5, file.name, totalChunks);

      setUploadState(prev => ({
        ...prev,
        status: 'completed',
        progress: 100,
      }));

      // 通知父组件刷新文件列表
      onUploadComplete?.();
    } catch (err) {
      // 检查是否是用户主动中止（暂停操作）
      if (err instanceof DOMException && err.name === 'AbortError') {
        // 这是用户主动暂停，不是错误，直接返回
        return;
      }

      // 其他错误
      setUploadState(prev => ({
        ...prev,
        status: 'error',
        error: err instanceof Error ? err.message : '上传失败',
      }));
    }
  };

  // 暂停上传
  const handlePause = () => {
    isPausedRef.current = true;
    setIsPaused(true);
    // 先设置状态，再中止请求
    setUploadState(prev => ({
      ...prev,
      status: 'paused',
    }));
    abortControllerRef.current?.abort();
  };

  // 继续上传
  const handleResume = async () => {
    isPausedRef.current = false;
    setIsPaused(false);
    if (uploadState.file && uploadState.md5) {
      await startUpload(
        uploadState.file,
        uploadState.md5,
        uploadState.totalChunks,
        uploadState.uploadedChunks
      );
    }
  };

  // 取消上传
  const handleCancel = async () => {
    if (uploadState.md5) {
      await cancelUpload(uploadState.md5);
    }
    setUploadState({
      file: null,
      md5: '',
      totalChunks: 0,
      uploadedChunks: [],
      currentChunk: 0,
      status: 'idle',
      progress: 0,
      speed: 0,
      remainingTime: 0,
      error: null,
    });
  };

  return (
    <div>
      {/* 文件选择区域 */}
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center mb-4">
        <input
          type="file"
          onChange={handleFileSelect}
          className="hidden"
          id="file-input"
          disabled={uploadState.status === 'uploading' || uploadState.status === 'merging'}
        />
        <label
          htmlFor="file-input"
          className="cursor-pointer text-gray-600 hover:text-gray-800"
        >
          {uploadState.file ? (
            <div>
              <p className="font-semibold">{uploadState.file.name}</p>
              <p className="text-sm text-gray-500">
                {(uploadState.file.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
          ) : (
            <div>
              <p className="text-lg">点击选择文件或拖拽文件到这里</p>
              <p className="text-sm text-gray-500">支持所有格式，最大 2GB</p>
            </div>
          )}
        </label>
      </div>

      {/* 错误信息 */}
      {uploadState.error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {uploadState.error}
        </div>
      )}

      {/* 上传进度 */}
      {uploadState.status !== 'idle' && (
        <div className="mb-4">
          <ProgressBar
            progress={uploadState.progress}
            speed={uploadState.speed}
            remainingTime={uploadState.remainingTime}
            status={uploadState.status}
          />

          {/* 分片信息 */}
          <div className="mt-2 text-sm text-gray-600">
            <p>
              分片进度：{uploadState.currentChunk} / {uploadState.totalChunks}
            </p>
          </div>
        </div>
      )}

      {/* 控制按钮 */}
      <div className="flex gap-4">
        {uploadState.status === 'idle' && uploadState.file && (
          <button
            onClick={() => {
              if (uploadState.file && uploadState.md5) {
                startUpload(
                  uploadState.file,
                  uploadState.md5,
                  uploadState.totalChunks,
                  uploadState.uploadedChunks
                );
              }
            }}
            className="bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600"
          >
            开始上传
          </button>
        )}

        {uploadState.status === 'uploading' && (
          <button
            onClick={handlePause}
            className="bg-yellow-500 text-white px-4 py-2 rounded-md hover:bg-yellow-600"
          >
            暂停
          </button>
        )}

        {uploadState.status === 'paused' && (
          <button
            onClick={handleResume}
            className="bg-green-500 text-white px-4 py-2 rounded-md hover:bg-green-600"
          >
            继续
          </button>
        )}

        {(uploadState.status === 'uploading' || uploadState.status === 'paused') && (
          <button
            onClick={handleCancel}
            className="bg-red-500 text-white px-4 py-2 rounded-md hover:bg-red-600"
          >
            取消
          </button>
        )}

        {uploadState.status === 'completed' && (
          <div className="text-green-600 font-semibold">
            ✅ 上传完成！
          </div>
        )}

        {uploadState.status === 'merging' && (
          <div className="text-blue-600">
            ⏳ 正在合并文件...
          </div>
        )}
      </div>
    </div>
  );
}
