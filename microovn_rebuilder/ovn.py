import subprocess


def rebuild(ovn_dir: str, jobs: int) -> bool:
    print(f"[local] Rebuilding OVN at {ovn_dir}")
    result = subprocess.run(["make", f"-j{jobs}"], cwd=ovn_dir, capture_output=True)
    if result.returncode != 0:
        print(result.stdout.decode("utf-8"))
        print(result.stderr.decode("utf-8"))
    return not result.returncode
