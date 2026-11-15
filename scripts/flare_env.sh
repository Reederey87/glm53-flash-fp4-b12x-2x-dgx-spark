#!/usr/bin/env bash
# Source only in candidate preparation/serving processes; never in host profiles.
FLARE_ROOT=/home/nvidia/b12x-flare
FLARE_DEPS="$FLARE_ROOT/deps"
export PATH="$FLARE_DEPS/usr/bin:/home/nvidia/.local/bin:/home/nvidia/.cargo/bin:/usr/local/cuda/bin:$PATH"
export PKG_CONFIG_PATH="$FLARE_DEPS/usr/lib/aarch64-linux-gnu/pkgconfig:$FLARE_DEPS/usr/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
export CPATH="$FLARE_DEPS/usr/include:$FLARE_DEPS/usr/include/aarch64-linux-gnu:$FLARE_DEPS/usr/include/python3.12${CPATH:+:$CPATH}"
export LIBRARY_PATH="$FLARE_DEPS/usr/lib/aarch64-linux-gnu${LIBRARY_PATH:+:$LIBRARY_PATH}"
export LD_LIBRARY_PATH="$FLARE_DEPS/usr/lib/aarch64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OPENSSL_INCLUDE_DIR="$FLARE_DEPS/usr/include"
export OPENSSL_LIB_DIR="$FLARE_DEPS/usr/lib/aarch64-linux-gnu"
export PROTOC="$FLARE_DEPS/usr/bin/protoc"
export BUILD_NVEP=0 FLASHINFER_BUILD_NO_PIP=1 CUTE_DSL_ARCH=sm_121a
export CARGO_BUILD_JOBS=2 MAX_JOBS=2 UV_CONCURRENT_BUILDS=1
export CUDA_HOME=/usr/local/cuda
