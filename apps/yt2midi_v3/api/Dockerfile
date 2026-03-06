FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive     PIP_NO_CACHE_DIR=1     PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends     python3 python3-pip python3-dev     ffmpeg sox libsox-fmt-all     build-essential     && rm -rf /var/lib/apt/lists/*

# cuDNN workaround: provide unversioned nvrtc soname expected by Conv_v8
RUN ln -sf /usr/local/cuda/targets/x86_64-linux/lib/libnvrtc.so.11.2     /usr/local/cuda/targets/x86_64-linux/lib/libnvrtc.so     && ldconfig

RUN pip3 install --upgrade pip
RUN pip3 install "numpy<2"

# PyTorch CUDA 11.8 wheels (works with Pascal / sm_61)
RUN pip3 install     torch==2.2.2 torchvision==0.17.2 torchaudio==2.2.2     --index-url https://download.pytorch.org/whl/cu118

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip3 install -r /app/requirements.txt

COPY app.py /app/app.py

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
