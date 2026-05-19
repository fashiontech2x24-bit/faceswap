#!/usr/bin/env bash
# setup.sh — GHOST 2.0 face-swap API
# Works locally (conda ghost2 env activated) and in Docker
# (pytorch/pytorch:2.4.1-cuda12.4-cudnn9-devel).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

info()  { echo "[INFO]  $*"; }
warn()  { echo "[WARN]  $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

# Prevent ~/.local leaking into builds
export PYTHONNOUSERSITE=1

# ── 0. Basic checks ───────────────────────────────────────────────────────────
python --version || error "python not found"
pip --version    || error "pip not found"

# ── 1. PyTorch (install if missing, skip if already present e.g. Docker image) ─
if ! python -c "import torch" 2>/dev/null; then
    info "torch not found — installing..."
    TORCH_INDEX="https://download.pytorch.org/whl/cpu"
    if command -v nvidia-smi &>/dev/null; then
        CUDA_MAJOR=$(nvidia-smi 2>/dev/null | grep -oP "CUDA Version: \K\d+" || echo "")
        if   [[ "${CUDA_MAJOR:-0}" -ge 12 ]]; then TORCH_INDEX="https://download.pytorch.org/whl/cu124"
        elif [[ "${CUDA_MAJOR:-0}" -ge 11 ]]; then TORCH_INDEX="https://download.pytorch.org/whl/cu118"
        fi
        info "CUDA ${CUDA_MAJOR} detected → $TORCH_INDEX"
    fi
    pip install torch torchvision --index-url "$TORCH_INDEX"
else
    TORCH_CUDA=$(python -c "import torch; print(torch.version.cuda)")
    info "torch already installed (CUDA $TORCH_CUDA) — skipping."
fi

# ── 2. Clone GHOST 2.0 ────────────────────────────────────────────────────────
info "Cloning GHOST 2.0..."
if [ ! -d "ghost" ]; then
    git clone https://github.com/ai-forever/ghost-2.0.git ghost
else
    info "ghost/ already present, skipping."
fi

# ── 3. Clone external repos ───────────────────────────────────────────────────
info "Cloning external repos into ghost/repos/..."
mkdir -p ghost/repos

clone_repo() {
    local url="$1" dest="ghost/repos/$2"
    if [ ! -d "$dest" ]; then
        info "  Cloning $2..."
        git clone --depth 1 "$url" "$dest"
    else
        info "  $2 already present, skipping."
    fi
}

clone_repo https://github.com/yfeng95/DECA.git                  DECA
clone_repo https://github.com/radekd91/emoca.git                emoca
clone_repo https://github.com/hollance/BlazeFace-PyTorch.git    BlazeFace-PyTorch
clone_repo https://github.com/chroneus/stylematte.git           stylematte

# ── 4. face-alignment, facenet_pytorch ───────────────────────────────────────
info "Installing face-alignment and facenet_pytorch..."
pip install --no-cache-dir face-alignment facenet_pytorch

# ── 5. GHOST 2.0 requirements ────────────────────────────────────────────────
info "Installing GHOST 2.0 requirements..."
# chumpy==0.70: broken setup.py imports `pip` as a module — bypass with --no-build-isolation.
pip install --no-cache-dir --no-build-isolation chumpy

# simple-lama-inpainting==0.1.2: declares pillow<10 but works fine with 10+;
# pin conflicts with scikit-image>=0.25 which needs pillow>=10.1. Install --no-deps.
pip install --no-cache-dir --no-deps simple-lama-inpainting

# Install the rest, excluding the two packages handled above.
grep -v "^chumpy\|^simple-lama-inpainting" ghost/requirements.txt \
    | pip install --no-cache-dir -r /dev/stdin

# numpy must be pinned AFTER everything else
info "Pinning numpy<2 (GHOST 2.0 compatibility)..."
pip install --no-cache-dir "numpy<2"

# ── 6. API server ─────────────────────────────────────────────────────────────
info "Installing API server dependencies..."
pip install --no-cache-dir \
    "fastapi>=0.100.0" \
    "uvicorn[standard]>=0.23.0" \
    "python-multipart>=0.0.6" \
    "aiofiles>=23.0.0"

# ── 7. Download GHOST 2.0 model checkpoints ───────────────────────────────────
info "Downloading GHOST 2.0 model checkpoints..."
BASE_URL="https://github.com/ai-forever/ghost-2.0/releases/download/aligner"

dl() {
    local dest="$1" url="$2"
    if [ ! -f "$dest" ]; then
        info "  Downloading $(basename "$dest")..."
        mkdir -p "$(dirname "$dest")"
        curl -L --insecure --progress-bar -o "$dest" "$url"
    else
        info "  $(basename "$dest") already present, skipping."
    fi
}

dl ghost/aligner_checkpoints/aligner_1020_gaze_final.ckpt  "$BASE_URL/aligner_1020_gaze_final.ckpt"
dl ghost/blender_checkpoints/blender_lama.ckpt             "$BASE_URL/blender_lama.ckpt"
dl ghost/weights/backbone50_1.pth                          "$BASE_URL/backbone50_1.pth"
dl ghost/weights/vgg19-d01eb7cb.pth                        "$BASE_URL/vgg19-d01eb7cb.pth"
dl ghost/weights/segformer_B5_ce.onnx                      "$BASE_URL/segformer_B5_ce.onnx"

GAZE_DIR="ghost/src/losses/gaze_models"
if [ ! -d "$GAZE_DIR" ] || [ -z "$(ls -A "$GAZE_DIR" 2>/dev/null)" ]; then
    info "  Downloading gaze_models.zip..."
    curl -L --insecure --progress-bar -o /tmp/gaze_models.zip "$BASE_URL/gaze_models.zip"
    mkdir -p "$GAZE_DIR"
    unzip -q /tmp/gaze_models.zip -d "$GAZE_DIR"
    rm /tmp/gaze_models.zip
else
    info "  gaze_models already present, skipping."
fi

# ── 8. Results directory ──────────────────────────────────────────────────────
mkdir -p results

info ""
info "Setup complete."
info "Start the server:  ./start.sh"
info "Open in browser:   http://localhost:8000"
