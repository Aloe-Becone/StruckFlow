#!/bin/bash
# ============================================================
# StruckFlow - openEuler 24.03-LTS-SP3 环境部署脚本
# 用途：安装系统依赖、配置 Python 虚拟环境、构建前端
# 使用：sudo bash setup-openeuler.sh [--dev|--prod|--gpu]
#   --dev  开发模式（仅安装依赖，不配置服务）
#   --prod 生产模式（安装依赖 + 配置 systemd + nginx）
#   --gpu  额外安装 CUDA/PyTorch GPU 支持
# ============================================================

set -euo pipefail

MODE="${1:---dev}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── 1. 检查操作系统 ──
check_os() {
    if [ ! -f /etc/os-release ]; then
        warn "无法检测操作系统，继续执行..."
        return
    fi
    source /etc/os-release
    info "操作系统: $PRETTY_NAME"
    if [[ "$ID" != "openEuler" ]]; then
        warn "此脚本专为 openEuler 设计，当前系统为 $ID，可能需要调整"
    fi
}

# ── 2. 安装系统依赖 ──
install_system_deps() {
    info "安装系统依赖..."
    dnf makecache --refresh

    # 基础工具
    dnf install -y \
        python3 python3-pip python3-devel \
        git tar gzip curl wget \
        nginx

    # Node.js (openEuler 24.03 仓库可能需要 EPEL 或手动安装)
    if ! command -v node &>/dev/null; then
        info "安装 Node.js..."
        dnf install -y nodejs npm 2>/dev/null || {
            warn "系统仓库无 Node.js，尝试 NodeSource..."
            curl -fsSL https://rpm.nodesource.com/setup_22.x | bash -
            dnf install -y nodejs
        }
    fi

    info "系统依赖安装完成"
    python3 --version
    node --version
    npm --version
}

# ── 3. 配置 Python 虚拟环境 ──
setup_python_venv() {
    local venv_dir="$PROJECT_ROOT/.venv"
    info "创建 Python 虚拟环境: $venv_dir"

    python3 -m venv "$venv_dir"
    source "$venv_dir/bin/activate"

    pip install --upgrade pip setuptools wheel

    # 安装项目依赖
    pip install -r "$PROJECT_ROOT/LangChain/requirements.txt" \
        --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
        --trusted-host pypi.tuna.tsinghua.edu.cn

    info "Python 依赖安装完成"
    pip list | head -20
}

# ── 4. GPU 支持 (可选) ──
install_gpu_support() {
    info "安装 GPU (CUDA) 支持..."

    # 检测 GPU
    if ! command -v nvidia-smi &>/dev/null; then
        warn "未检测到 NVIDIA GPU 驱动，跳过 CUDA 安装"
        return
    fi

    info "检测到 NVIDIA GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader)"

    # 安装 CUDA Toolkit (openEuler 可能需要手动安装)
    if [ ! -d /usr/local/cuda ]; then
        warn "CUDA Toolkit 未安装，请参考 https://developer.nvidia.com/cuda-downloads 手动安装"
        warn "安装 CUDA 后，重新运行此脚本以安装 GPU 版 PyTorch"
        return
    fi

    # 安装 GPU 版 PyTorch
    source "$PROJECT_ROOT/.venv/bin/activate"
    pip install torch --index-url https://download.pytorch.org/whl/cu121

    info "GPU 支持安装完成"
    python3 -c "import torch; print(f'CUDA 可用: {torch.cuda.is_available()}')"
}

# ── 5. 构建前端 ──
build_frontend() {
    info "构建 Vue 前端..."
    cd "$PROJECT_ROOT/web/vue"

    npm install --registry=https://registry.npmmirror.com
    npm run build

    info "前端构建完成: $PROJECT_ROOT/web/vue/dist/"
    cd "$PROJECT_ROOT"
}

# ── 6. 生产环境配置 ──
setup_production() {
    info "配置生产环境..."

    local install_dir="/usr/lib/struckflow"
    local data_dir="/var/lib/struckflow/data"

    # 创建系统用户
    if ! id struckflow &>/dev/null; then
        useradd -r -s /sbin/nologin -d "$install_dir" struckflow
        info "创建系统用户: struckflow"
    fi

    # 安装应用文件
    mkdir -p "$install_dir"
    cp -r "$PROJECT_ROOT/LangChain" "$install_dir/"
    cp -r "$PROJECT_ROOT/web/flask" "$install_dir/web/flask"

    # 安装前端构建产物
    mkdir -p /usr/share/struckflow/web
    cp -r "$PROJECT_ROOT/web/vue/dist/"* /usr/share/struckflow/web/

    # 创建 Python venv
    python3 -m venv "$install_dir/venv"
    "$install_dir/venv/bin/pip" install --upgrade pip
    "$install_dir/venv/bin/pip" install \
        -r "$install_dir/LangChain/requirements.txt" \
        --index-url https://pypi.tuna.tsinghua.edu.cn/simple

    # 创建数据目录
    mkdir -p "$data_dir/memories" "$data_dir/chats"
    chown -R struckflow:struckflow "$data_dir"

    # 配置 .env
    if [ ! -f "$install_dir/LangChain/.env" ]; then
        cp "$install_dir/LangChain/.env.example" "$install_dir/LangChain/.env"
        chmod 600 "$install_dir/LangChain/.env"
        warn "请编辑 $install_dir/LangChain/.env 配置 API 密钥"
    fi

    # 安装 systemd 服务
    cp "$PROJECT_ROOT/packaging/struckflow-backend.service" \
       /usr/lib/systemd/system/
    systemctl daemon-reload
    systemctl enable struckflow-backend

    # 安装 nginx 配置
    cp "$PROJECT_ROOT/packaging/nginx-struckflow.conf" \
       /etc/nginx/conf.d/
    # 移除默认 server 块冲突
    if [ -f /etc/nginx/conf.d/default.conf ]; then
        mv /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.bak
    fi
    nginx -t && systemctl enable nginx

    info "========================================="
    info "生产环境配置完成！"
    info "========================================="
    info "1. 编辑配置:  vim $install_dir/LangChain/.env"
    info "2. 启动后端:  systemctl start struckflow-backend"
    info "3. 启动前端:  systemctl start nginx"
    info "4. 查看状态:  systemctl status struckflow-backend"
    info "5. 查看日志:  journalctl -u struckflow-backend -f"
    info "6. 访问地址:  http://<服务器IP>"
    info "========================================="
}

# ── 主流程 ──
main() {
    info "StruckFlow openEuler 部署脚本"
    info "模式: $MODE"
    info "项目目录: $PROJECT_ROOT"
    echo ""

    check_os
    install_system_deps
    setup_python_venv

    if [[ "$MODE" == "--gpu" ]]; then
        install_gpu_support
    fi

    build_frontend

    if [[ "$MODE" == "--prod" || "$MODE" == "--gpu" ]]; then
        setup_production
    else
        info "========================================="
        info "开发环境配置完成！"
        info "========================================="
        info "启动后端:"
        info "  cd $PROJECT_ROOT"
        info "  source .venv/bin/activate"
        info "  python LangChain/main.py"
        info ""
        info "启动 Flask API:"
        info "  python web/flask/app.py"
        info ""
        info "启动前端开发服务器:"
        info "  cd web/vue && npm run dev"
        info "========================================="
    fi
}

main