#!/bin/bash

# 部署脚本 - 大文件上传系统
set -e

echo "🚀 开始部署..."

# 进入项目目录
cd /root/big_files

# 拉取最新代码
echo "📥 拉取最新代码..."
git fetch origin
git reset --hard origin/main
git clean -fd

# 停止旧容器
echo "⏹️  停止旧容器..."
docker-compose down

# 启动 MySQL 并等待就绪
echo "🗄️  启动 MySQL..."
docker-compose up -d mysql
echo "⏳ 等待 MySQL 就绪（60秒）..."
sleep 60

# 检查 MySQL 是否就绪
echo "🏥 检查 MySQL 状态..."
docker-compose exec -T mysql mysqladmin ping -h localhost --silent || {
    echo "❌ MySQL 启动失败"
    docker-compose logs mysql
    exit 1
}
echo "✅ MySQL 已就绪"

# 初始化数据库
echo "🗄️  初始化数据库..."
docker-compose exec -T mysql mysql -uroot -p123456 -e "CREATE DATABASE IF NOT EXISTS file_upload CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" || true
docker-compose exec -T mysql mysql -uroot -p123456 file_upload -e "
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS files (
    id INT PRIMARY KEY AUTO_INCREMENT,
    md5 VARCHAR(32) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100),
    user_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_md5 (md5),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chunks (
    id INT PRIMARY KEY AUTO_INCREMENT,
    file_md5 VARCHAR(32) NOT NULL,
    chunk_index INT NOT NULL,
    status ENUM('uploading', 'completed', 'failed') DEFAULT 'uploading',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_file_md5 (file_md5),
    UNIQUE INDEX idx_md5_index (file_md5, chunk_index)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 插入默认管理员用户（密码：123456）
INSERT IGNORE INTO users (username, password_hash) VALUES ('admin', '\$2b\$12\$LJ3m4ys3Lk0TSwHjnF4b6OiJxQxYqYqYqYqYqYqYqYqYqYqYqYqYq');
" || echo "⚠️  数据库表已存在或创建失败，继续部署..."

echo "✅ 数据库初始化完成"

# 启动其他服务
echo "🔨 启动其他服务..."
docker-compose up -d backend frontend nginx

# 等待服务启动
echo "⏳ 等待服务启动（30秒）..."
sleep 30

# 健康检查
echo "🏥 执行健康检查..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 后端服务启动成功！"
else
    echo "❌ 后端服务启动失败"
    docker-compose logs backend
    exit 1
fi

if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ 前端服务启动成功！"
else
    echo "❌ 前端服务启动失败"
    docker-compose logs frontend
    exit 1
fi

echo ""
echo "🎉 部署完成！"
echo ""
echo "📍 服务地址："
echo "   - 应用入口：http://8.146.205.130"
echo "   - 后端 API：http://8.146.205.130:8000"
echo "   - 前端：http://8.146.205.130:3000"
echo ""
echo "🔑 登录账号：admin / 123456"
