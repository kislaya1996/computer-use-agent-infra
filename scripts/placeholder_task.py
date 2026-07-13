import sys


def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else "unnamed"
    payload = sys.argv[2] if len(sys.argv) > 2 else ""
    print(f"placeholder ran for task={name} payload={payload}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
