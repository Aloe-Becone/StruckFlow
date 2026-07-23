#!/bin/bash
# ============================================================
# StruckFlow - RPM 包构建脚本
# 用途：在 openEuler 24.03-LTS-SP3 上构建 RPM 安装包
# 使用：bash build-rpm.sh [--skip-frontend]
# ============================================================

set -euo pipefail

SKIP_FRONTEND=false
[[ "${1:-}" == "--skip-frontend" ]] && SKIP_FRONTEND=true

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION="1.0.0"
RELEASE="1"
PKG_NAME="struckflow"
BUILD_DIR="/tmp/${PKG_NAME}-build"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── 1. 检查构建工具 ──
check_build_tools() {
    info "检查构建工具..."
    for cmd in rpmbuild python3 node npm tar; do
        command -v "$cmd" &>/dev/null || error "缺少必要工具: $cmd"
    done
    info "构建工具检查通过"
}

# ── 2. 构建前端 ──
build_frontend() {
    if $SKIP_FRONTEND; then
        warn "跳过前端构建 (--skip-frontend)"
        return
    fi

    info "构建 Vue 前端..."
    cd "$PROJECT_ROOT/web/vue"
    npm install --registry=https://registry.npmmirror.com
    npm run build
    cd "$PROJECT_ROOT"
    info "前端构建完成"
}

# ── 3. 准备源码包 ──
prepare_source() {
    info "准备源码包..."
    rm -rf "$BUILD_DIR"
    mkdir -p "$BUILD_DIR/SOURCES" "$BUILD_DIR/SPECS" "$BUILD_DIR/RPMS" "$BUILD_DIR/SRPMS"

    local src_dir="$BUILD_DIR/SOURCES/${PKG_NAME}-${VERSION}"
    mkdir -p "$src_dir"

    # 复制项目文件 (排除不需要的文件)
    rsync -a \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='.venv' \
        --exclude='node_modules' \
        --exclude='.env' \
        --exclude='*.pyc' \
        --exclude='.joycode' \
        "$PROJECT_ROOT/" "$src_dir/"

    # 创建 tar.gz
    cd "$BUILD_DIR/SOURCES"
    tar czf "${PKG_NAME}-${VERSION}.tar.gz" "${PKG_NAME}-${VERSION}"
    cd "$PROJECT_ROOT"

    info "源码包: $BUILD_DIR/SOURCES/${PKG_NAME}-${VERSION}.tar.gz"
}

# ── 4. 构建 RPM ──
build_rpm() {
    info "构建 RPM 包..."

    # 复制 spec 文件
    cp "$PROJECT_ROOT/packaging/struckflow.spec" "$BUILD_DIR/SPECS/"

    # 创建 rpmbuild 目录结构
    mkdir -p ~/rpmbuild/{SOURCES,SPECS,BUILD,RPMS,SRPMS}

    # 链接源码包
    ln -sf "$BUILD_DIR/SOURCES/${PKG_NAME}-${VERSION}.tar.gz" \
           ~/rpmbuild/SOURCES/

    # 复制 spec
    cp "$BUILD_DIR/SPECS/struckflow.spec" ~/rpmbuild/SPECS/

    # 安装构建依赖
    info "安装构建依赖..."
    sudo dnf builddep -y ~/rpmbuild/SPECS/struckflow.spec 2>/dev/null || {
        warn "dnf builddep 失败，尝试手动安装..."
        sudo dnf install -y python3-devel python3-pip nodejs npm
    }

    # 构建
    rpmbuild -ba ~/rpmbuild/SPECS/struckflow.spec

    # 查找生成的 RPM
    local rpm_file
    rpm_file=$(find ~/rpmbuild/RPMS -name "${PKG_NAME}-*.rpm" -type f | head -1)

    if [ -n "$rpm_file" ]; then
        info "========================================="
        info "RPM 构建成功！"
        info "========================================="
        info "RPM 包: $rpm_file"
        info "大小: $(du -h "$rpm_file" | cut -f1)"
        info ""
        info "安装命令:"
        info "  sudo dnf install -y $rpm_file"
        info ""
        info "查看包信息:"
        info "  rpm -qip $rpm_file"
        info "========================================="

        # 复制到项目目录
        cp "$rpm_file" "$PROJECT_ROOT/packaging/"
        info "已复制到: $PROJECT_ROOT/packaging/$(basename "$rpm_file")"
    else
        error "RPM 构建失败，请检查构建日志"
    fi
}

# ── 5. 验证 RPM ──
verify_rpm() {
    local rpm_file
    rpm_file=$(find ~/rpmbuild/RPMS -name "${PKG_NAME}-*.rpm" -type f | head -1)

    if [ -z "$rpm_file" ]; then
        warn "未找到 RPM 包，跳过验证"
        return
    fi

    info "验证 RPM 包..."
    echo "--- 包信息 ---"
    rpm -qip "$rpm_file" 2>/dev/null || true
    echo ""
    echo "--- 文件列表 ---"
    rpm -qlp "$rpm_file" 2>/dev/null | head -30
    echo ""
    echo "--- 依赖列表 ---"
    rpm -qpR "$rpm_file" 2>/dev/null || true
}

# ── 主流程 ──
main() {
    info "StruckFlow RPM 构建脚本"
    info "版本: ${VERSION}-${RELEASE}"
    echo ""

    check_build_tools
    build_frontend
    prepare_source
    build_rpm
    verify_rpm

    info "构建流程全部完成！"
}

main