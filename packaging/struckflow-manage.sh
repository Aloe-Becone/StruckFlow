#!/bin/bash
# ============================================================
# StruckFlow 管理脚本
# 用途：RPM 安装后的服务管理工具
# 使用：struckflow-manage <命令>
# ============================================================

set -euo pipefail

INSTALL_DIR="/usr/lib/struckflow"
DATA_DIR="/var/lib/struckflow/data"
ENV_FILE="$INSTALL_DIR/LangChain/.env"
VENV_PYTHON="$INSTALL_DIR/venv/bin/python"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

cmd_start()   { systemctl start struckflow-backend; systemctl start nginx; info "服务已启动"; }
cmd_stop()    { systemctl stop struckflow-backend; systemctl stop nginx; info "服务已停止"; }
cmd_restart() { systemctl restart struckflow-backend; systemctl restart nginx; info "服务已重启"; }
cmd_status()  { systemctl status struckflow-backend --no-pager; echo ""; systemctl status nginx --no-pager; }
cmd_logs()    { journalctl -u struckflow-backend -f; }

cmd_config() {
    local editor="${EDITOR:-vim}"
    if [ ! -f "$ENV_FILE" ]; then
        warn ".env 文件不存在，从模板创建..."
        cp "$INSTALL_DIR/LangChain/.env.example" "$ENV_FILE"
        chmod 600 "$ENV_FILE"
    fi
    info "编辑配置文件: $ENV_FILE"
    $editor "$ENV_FILE"
}

cmd_test() {
    info "运行测试..."

    # 测试 1: 检查 Python 环境
    info "[1/4] 检查 Python 环境..."
    if [ -x "$VENV_PYTHON" ]; then
        $VENV_PYTHON --version
        info "  Python 环境正常"
    else
        error "  Python 虚拟环境不可用: $VENV_PYTHON"
    fi

    # 测试 2: 检查关键 Python 包
    info "[2/4] 检查 Python 依赖..."
    $VENV_PYTHON -c "
import langchain; print(f'  langchain: {langchain.__version__}')
import flask; print(f'  flask: {flask.__version__}')
import torch; print(f'  torch: {torch.__version__}')
" 2>/dev/null || warn "  部分 Python 包缺失，请运行: $VENV_PYTHON -m pip install -r $INSTALL_DIR/LangChain/requirements.txt"

    # 测试 3: 检查 CUDA
    info "[3/4] 检查 GPU 支持..."
    $VENV_PYTHON -c "
import torch
if torch.cuda.is_available():
    print(f'  CUDA 可用: {torch.cuda.get_device_name(0)}')
else:
    print('  CUDA 不可用 (使用 CPU 模式)')
" 2>/dev/null || warn "  无法检测 GPU"

    # 测试 4: 检查服务连通性
    info "[4/4] 检查服务..."
    if systemctl is-active --quiet struckflow-backend; then
        info "  后端服务运行中"
        curl -sf http://localhost:5000/api/health 2>/dev/null && info "  API 响应正常" || warn "  API 未响应"
    else
        warn "  后端服务未运行"
    fi

    if systemctl is-active --quiet nginx; then
        info "  Nginx 服务运行中"
    else
        warn "  Nginx 服务未运行"
    fi

    info "测试完成"
}

cmd_pip() {
    # 便捷安装 Python 包
    local pkg="${1:?用法: struckflow-manage pip <包名>}"
    info "安装 Python 包: $pkg"
    "$INSTALL_DIR/venv/bin/pip" install "$pkg" \
        --index-url https://pypi.tuna.tsinghua.edu.cn/simple
    info "安装完成，重启服务生效: struckflow-manage restart"
}

cmd_help() {
    cat <<EOF
StruckFlow 管理工具

用法: struckflow-manage <命令>

命令:
  start     启动后端和 Nginx 服务
  stop      停止服务
  restart   重启服务
  status    查看服务状态
  logs      查看后端实时日志
  config    编辑 .env 配置文件
  test      运行环境诊断测试
  pip       在虚拟环境中安装 Python 包
  help      显示此帮助信息

示例:
  struckflow-manage start
  struckflow-manage config
  struckflow-manage pip langchain-openai
  struckflow-manage test
EOF
}

# ── 主入口 ──
case "${1:-help}" in
    start)   cmd_start ;;
    stop)    cmd_stop ;;
    restart) cmd_restart ;;
    status)  cmd_status ;;
    logs)    cmd_logs ;;
    config)  cmd_config ;;
    test)    cmd_test ;;
    pip)     cmd_pip "${2:-}" ;;
    help|*)  cmd_help ;;
esac