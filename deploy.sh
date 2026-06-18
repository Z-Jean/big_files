#!/bin/bash

# 部署脚本 - 大文件上传系统
set -e

echo "🚀 开始部署..."

# 进入项目目录
cd /root/big_files

# 拉取最新代码
echo "📥 拉取最新代码..."
git pull origin main

# 停止旧容器
echo "⏹️  停止旧容器..."
docker-compose down

# 构建并启动新容器（在服务器上构建，不受 Actions 超时限制）
echo "🔨 构建并启动容器（首次构建需要 5-10 分钟）..."
docker-compose up -d --build

# 等待服务启动
echo "⏳ 等待服务启动..."
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
