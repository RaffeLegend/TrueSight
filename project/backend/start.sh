#!/bin/bash

# 1. 启动 Flask 项目（后台运行）
echo "Starting Flask App on port 5000..."
conda activate true
nohup python app.py > flask.log 2>&1 &

# 2. 安装 cloudflared（如果没有的话）
if ! command -v cloudflared &> /dev/null
then
    echo "Installing Cloudflared..."
    wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
    chmod +x cloudflared-linux-amd64
    sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
fi

# 3. 启动 Cloudflared Tunnel
echo "Starting Cloudflared Tunnel..."
cloudflared tunnel --url http://localhost:5000
