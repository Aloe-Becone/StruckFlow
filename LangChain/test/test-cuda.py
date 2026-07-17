import torch
print("PyTorch 版本:", torch.__version__)
print("CUDA 可用:", torch.cuda.is_available())
print("CUDA 版本:", torch.version.cuda)
print("GPU 数量:", torch.cuda.device_count())
if torch.cuda.is_available():
    print("GPU 名称:", torch.cuda.get_device_name(0))
    print("显存总量:", torch.cuda.get_device_properties(0).total_memory / 1024**3, "GB")