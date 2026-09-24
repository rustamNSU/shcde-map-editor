"""Portable launcher. CLI mode never imports or starts Qt."""
import sys


def main():
    if '--cli' in sys.argv:
        from editor.cli import run
        args = sys.argv[1:]
        args.remove('--cli')
        return run(args)
    from editor.gui import run
    return run()


if __name__ == '__main__':
    raise SystemExit(main())
