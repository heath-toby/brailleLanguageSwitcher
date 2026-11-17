import zipfile, os
out = "brailleLanguageSwitcher-2.0.0.nvda-addon"
if os.path.exists(out):
    os.remove(out)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk("addon"):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(".pyc"):
                continue
            full = os.path.join(root, f)
            arc = os.path.relpath(full, "addon").replace(os.sep, "/")
            z.write(full, arc)
print("packaged", os.path.getsize(out), "bytes ->", out)
