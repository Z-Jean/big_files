/* eslint-disable no-restricted-globals */

// 导入 spark-md5（需要在 HTML 中通过 script 标签加载）
// 这里假设 spark-md5 已经通过 CDN 加载

self.onmessage = function(e) {
  const { file } = e.data;

  // 创建 SparkMD5 实例
  const spark = new SparkMD5.ArrayBuffer();
  const reader = new FileReader();
  const chunkSize = 2 * 1024 * 1024; // 2MB
  let currentChunk = 0;
  const totalChunks = Math.ceil(file.size / chunkSize);

  const loadNext = () => {
    const start = currentChunk * chunkSize;
    const end = Math.min(start + chunkSize, file.size);
    reader.readAsArrayBuffer(file.slice(start, end));
  };

  reader.onload = function(e) {
    spark.append(e.target.result);
    currentChunk++;

    // 发送进度
    self.postMessage({
      type: 'progress',
      progress: Math.round((currentChunk / totalChunks) * 100)
    });

    if (currentChunk < totalChunks) {
      loadNext();
    } else {
      // 完成，发送 MD5
      self.postMessage({
        type: 'complete',
        md5: spark.end()
      });
    }
  };

  reader.onerror = function() {
    self.postMessage({
      type: 'error',
      error: '文件读取失败'
    });
  };

  loadNext();
};
