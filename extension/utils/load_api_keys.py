import os


def _load_api_keys(filepath):
    try:
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if line and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
