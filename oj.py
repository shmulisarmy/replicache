import os

def split_code_dump(dump: str, root_dir="."):
    lines = dump.splitlines()
    file_path = None
    buffer = []

    for line in lines:
        if line.startswith("# ") and line.endswith(".py"):
            if file_path and buffer:
                os.makedirs(os.path.join(root_dir, os.path.dirname(file_path)), exist_ok=True)
                with open(os.path.join(root_dir, file_path), "w", encoding="utf-8") as f:
                    f.write("\n".join(buffer))
            file_path = line[2:].strip()
            buffer = []
        else:
            buffer.append(line)
    
    # Write the last file
    if file_path and buffer:
        os.makedirs(os.path.join(root_dir, os.path.dirname(file_path)), exist_ok=True)
        with open(os.path.join(root_dir, file_path), "w", encoding="utf-8") as f:
            f.write("\n".join(buffer))



if __name__ == "__main__":
    with open("dump.py") as f:
        dump_content = f.read()
    split_code_dump(dump_content, root_dir="./output")
