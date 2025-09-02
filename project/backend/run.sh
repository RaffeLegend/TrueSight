#!/bin/bash

# 终止旧的 Flask 和 cloudflared 进程
echo "Stopping old Flask and Tunnel processes..."
pkill -f "python app.py"
pkill -f "cloudflared tunnel run"

# 启动 Flask 项目
echo "Starting Flask on port 5000..."
nohup python app.py > flask.log 2>&1 &
sleep 3  # 等 Flask 启动稳定

# 启动 Cloudflare Tunnel
echo "Starting Cloudflare Tunnel..."
nohup cloudflared tunnel run mytunnel > tunnel.log 2>&1 &

# 显示状态信息
echo "Flask and Cloudflare Tunnel started."
echo "Flask logs: flask.log"
echo "Tunnel logs: tunnel.log"

# 显示 Zerotier 虚拟 IP（可选）
echo "Your Zerotier IP (if any):"
ip a | grep 'zt' -A 2
