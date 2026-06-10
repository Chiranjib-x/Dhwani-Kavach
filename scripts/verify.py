import sys, os
print("=" * 50)
print("Dhwani-Kavach — Phase 0 Verification")
print("=" * 50)

errors = []

# 1. Python imports
packages = ["fastapi","uvicorn","torch","librosa","soundfile","redis","numpy","scipy","sklearn","websockets","huggingface_hub"]
for pkg in packages:
    try:
        __import__(pkg if pkg != "sklearn" else "sklearn")
        print(f"  [OK] {pkg}")
    except ImportError:
        print(f"  [FAIL] {pkg}")
        errors.append(pkg)

# 2. AASIST model file
model_path = "backend/models/AASIST.pth"
if os.path.exists(model_path):
    size_mb = os.path.getsize(model_path) / 1024 / 1024
    print(f"  [OK] AASIST.pth ({size_mb:.1f} MB)")
else:
    print(f"  [FAIL] AASIST.pth not found at {model_path}")
    errors.append("AASIST.pth")

# 3. PyTorch loads model
if not errors:
    try:
        import torch
        ckpt = torch.load(model_path, map_location="cpu")
        print(f"  [OK] torch.load() — keys: {list(ckpt.keys())[:3]}...")
    except Exception as e:
        print(f"  [WARN] torch.load() issue: {e}")

# 4. Folder structure
dirs = ["backend/app","backend/ml","backend/models","frontend/src/components","frontend/src/hooks","scripts","docker"]
for d in dirs:
    status = "[OK]" if os.path.isdir(d) else "[FAIL]"
    print(f"  {status} {d}/")
    if status == "[FAIL]": errors.append(d)

# 5. Docker Compose exists
dc = "docker-compose.yml"
print(f"  {'[OK]' if os.path.exists(dc) else '[FAIL]'} {dc}")

print("=" * 50)
if errors:
    print(f"FAILED: {errors}")
    sys.exit(1)
else:
    print("Phase 0 complete. Ready for Phase 1A.")
