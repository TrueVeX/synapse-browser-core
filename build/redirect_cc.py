"""Compiler wrapper (GN cc_wrapper) that applies Brave's chromium_src overrides.

Brave replaces some Chromium .cc files with brave/chromium_src/<same path>.
Its siso build config does that swap (the "redirect_cc" handler in
brave/build/config/siso/brave_siso_config.star). SYNAPSE builds with plain
ninja, which can be stopped and resumed between stages, so this wrapper does
the same swap: if the file after /c (or -c) has an override, compile the
override instead. Everything else is passed on to the compiler unchanged.

Used as: cc_wrapper = "<python.exe> -S -E <this file>"
It runs once per compile, so it only uses built-in modules (fast start).
"""
import _winapi
import os
import sys


def override_for(source):
    s = source.replace("\\", "/")
    if s.startswith("../../"):
        cand = "../../brave/chromium_src/" + s[6:]
    elif s.startswith("gen/"):
        cand = "../../brave/chromium_src/" + s[4:]
    else:
        parts = s.split("/")
        if len(parts) > 2 and parts[1] == "gen":
            cand = "../../brave/chromium_src/" + "/".join(parts[2:])
        else:
            return None
    return cand if os.path.isfile(cand) else None


def quote(arg):
    # Same rules as subprocess.list2cmdline (the inverse of the MSVC runtime's
    # argument parsing, which clang-cl uses too).
    if arg and not any(c in arg for c in ' \t"'):
        return arg
    out, bs = ['"'], []
    for c in arg:
        if c == "\\":
            bs.append(c)
        elif c == '"':
            out.append("\\" * len(bs) * 2 + '\\"')
            bs = []
        else:
            if bs:
                out.extend(bs)
                bs = []
            out.append(c)
    if bs:
        out.extend(bs * 2)
    out.append('"')
    return "".join(out)


def main():
    args = sys.argv[1:]
    if not args:
        return 1
    for i in range(len(args) - 1):
        if args[i] in ("/c", "-c"):
            ovr = override_for(args[i + 1])
            if ovr:
                args[i + 1] = ovr
            break
    cmd = " ".join(quote(a) for a in args)
    class StartupInfo:  # hand ninja's pipes straight to the compiler
        dwFlags = _winapi.STARTF_USESTDHANDLES
        hStdInput = _winapi.GetStdHandle(_winapi.STD_INPUT_HANDLE)
        hStdOutput = _winapi.GetStdHandle(_winapi.STD_OUTPUT_HANDLE)
        hStdError = _winapi.GetStdHandle(_winapi.STD_ERROR_HANDLE)
        wShowWindow = 0
        lpAttributeList = None
    proc, thread, _, _ = _winapi.CreateProcess(None, cmd, None, None, True, 0, None, None, StartupInfo)
    _winapi.CloseHandle(thread)
    _winapi.WaitForSingleObject(proc, _winapi.INFINITE)
    code = _winapi.GetExitCodeProcess(proc)
    _winapi.CloseHandle(proc)
    return code


if __name__ == "__main__":
    sys.exit(main())
