# Copyright (C) 2023-2024 Gustavo Sverzut Barbieri <barbieri@profusion.mobi>
# License: MIT
# https://github.com/barbieri/barbieri-playground/tree/master/docker/distroless/python/

##
#
# Docker entrypoint to use `gcr.io/distroless/python3` as base.
#
# Distroless images don't have a shell, so the traditional setup to wait a
# database server to be ready or replace `${var}_FILE` (ie: docker secrets)
# is cumbersome to do.
#
# This file is pure Python and copied to your project and used as `CMD`.
# The following example waits (simple TCP connection, not a real DB
# connection) for PostgresSQL at `${PGHOST}:${PGPORT}`. Since shell is not
# available, just basic variable interpolation is allowed, only the special
# case `${VAR:-DEFAULT}` is supported.
#
# ```dockerfile
# FROM gcr.io/distroless/python3-debian12
#
# # ... copy your built files ...
#
# CMD [ \
#     "/docker-entrypoint.py", \
#     "--file-env=PGPASSWORD", \
#     "--wait-server=${PGHOST}:${PGPORT:-5432}", \
#     "/path/to/your-app.js" \
# ]
# ```
#
# See
# https://github.com/GoogleContainerTools/distroless/blob/main/python3/README.md

import asyncio
import json
import os
import re
import socket
import sys
import time

from typing import (
    Literal,
    NamedTuple,
    NoReturn,
    Optional,
)


def die(*err) -> NoReturn:
    print("ERROR:", *err, file=sys.stderr)
    sys.exit(1)


DEBUG = os.environ.get("DEBUG") == "1"
log = print if DEBUG else lambda *a: None


class WaitServerOptions(NamedTuple):
    interval: Optional[int] = None
    max_retries: Optional[int] = None


wait_server_default_opts = WaitServerOptions(interval=1000, max_retries=10)


class WaitServerConnectOptions(NamedTuple):
    host: str
    port: int
    family: socket.AddressFamily | int = socket.AF_UNSPEC


async def wait_server(
    connect_opts: WaitServerConnectOptions,
    wait_opts: Optional[WaitServerOptions] = None,
) -> None:
    """
    Wait Server as a promise,
    useful to wait DB or some other dependency to be ready to use.
    """

    if wait_opts is None:
        wait_opts = wait_server_default_opts

    tries = 0
    start_time = time.time()

    conn_parts = [connect_opts.host, str(connect_opts.port)]
    if connect_opts.family != socket.AF_UNSPEC:
        family_str = socket.AddressFamily(connect_opts.family).name
        conn_parts.append("family=" + family_str)
    conn_str = ":".join(conn_parts)

    while tries < wait_opts.max_retries:
        try:
            log(f"{conn_str} connecting to server!")
            r, w = await asyncio.open_connection(
                host=connect_opts.host,
                port=connect_opts.port,
                family=connect_opts.family,
            )
            log(f"{conn_str} connected to server!")
            w.close()  # has the ownership, there is no r.close()
            return
        except Exception as error:
            tries += 1
            log(f"{conn_str} #{tries} failed to connect:", error)
            if tries == wait_opts.max_retries:
                elapsed = time.time() - start_time
                raise Exception(
                    f"{conn_str} could not connect. {tries} tries, "
                    + f"elapsed {elapsed} seconds",
                ) from error

            asyncio.sleep(wait_opts.interval / 1000.0)


TrimFileContents = Literal["start", "end", "both", "none"]


class FileEnvOptions(NamedTuple):
    default_value: Optional[str] = None
    var_file_name: Optional[str] = None  # overrides default `${varName}_FILE`
    exclusive: bool = (
        # if true (default), will fail if both `${varName}` and
        # `${varName}_FILE` are set
        True
    )
    fail_file_read_error: bool = (
        # if true (default), will fail if file is specified and doesn't exist
        True
    )
    trim_file_contents: TrimFileContents = (
        # if given states how to trim the value read from file,
        # useful to remove trailing `\n` (default 'both')
        "both"
    )
    required: bool = True


file_env_default_options = FileEnvOptions(
    exclusive=True,
    fail_file_read_error=True,
    trim_file_contents="both",
    required=True,
)


def file_env(var_name: str, options: Optional[FileEnvOptions] = None):
    if options is None:
        options = file_env_default_options

    env = os.environ
    var_file_name = options.var_file_name or f"{var_name}_FILE"

    var_value = env.get(var_name)
    var_file_name_value = env.get(var_file_name)

    log(
        "file_ev",
        {
            "var_name": var_name,
            "var_value": var_value,
            "var_file_name": var_file_name,
            "var_file_name_value": var_file_name_value,
        },
    )

    if options.exclusive and var_value and var_file_name_value:
        raise ValueError(
            f"both {var_name} and {var_file_name} are set, "
            + "but they are mutually exclusive!"
        )

    if var_value:
        return

    if var_file_name_value:
        try:
            with open(var_file_name_value, "r", encoding="utf-8") as file:
                file_value = file.read()

                if options.trim_file_contents == "both":
                    file_value = file_value.strip()
                elif options.trim_file_contents == "start":
                    file_value = file_value.lstrip()
                elif options.trim_file_contents == "end":
                    file_value = file_value.rstrip()

                log(f"file_env: set {var_name}={json.dumps(file_value)}")
                env[var_name] = file_value
                return
        except Exception as e:
            if options.fail_file_read_error:
                raise e
            # else keep going and use the default

    if options.default_value is not None:
        env[var_name] = options.default_value
        return

    if options.required:
        raise ValueError(
            f"missing environment variable {var_name} "
            + f"(alternatively loaded from {var_file_name})"
        )


def split_n(s: str, separator: str, count: int) -> list[str]:
    """'
    split(separator, count) will return a shorter list, extend with None
    NOTE: also count is the return length, not split count!
    """
    parts = s.split(separator, count - 1)
    parts.extend([None] * (count - len(parts)))
    return parts


def handle_file_env_flag(value: str) -> None:
    var_name, options_json = split_n(value, ":", 2)
    options = json.loads(options_json) if options_json else None
    return file_env(var_name, options)


async def handle_wait_server_flag(value: str) -> asyncio.Future[None]:
    [host, port_str, options_json] = split_n(value, ":", 3)
    if not host:
        raise Exception("missing host, format: host:port[:options]")

    if not port_str:
        raise Exception("missing port, format: host:port[:options]")

    port = int(port_str)
    conn_opts = WaitServerConnectOptions(host, port)

    options_kwargs = json.loads(options_json) if options_json else None
    wait_opts = WaitServerOptions(*options_kwargs) if options_kwargs else None
    return await wait_server(conn_opts, wait_opts)


var_name_reg_exp = re.compile(r"[A-Za-z0-9_]")


def replace_env_vars(s: str) -> str:
    result = ""
    is_escaped = False
    var_name_mode = None
    var_name = ""

    def expand_var(default_value: Optional[str] = None):
        nonlocal result, var_name, var_name_mode
        value = os.getenv(var_name)
        if value is None and default_value is None:
            log(f"missing env var {var_name} (expanded to empty string)")
        result += value or default_value or ""
        var_name = ""
        var_name_mode = None

    i = 0
    while i < len(s):
        c = s[i]
        if var_name_mode == "simple":
            if var_name_reg_exp.match(c):
                var_name += c
            elif c == "{":
                var_name_mode = "braces"
            else:
                # process this character again so it's added to result later
                i -= 1
                expand_var()
        elif var_name_mode == "braces":
            if var_name_reg_exp.match(c):
                var_name += c
            elif c == ":" and i + 1 < len(s) and s[i + 1] == "-":
                end = s.find("}", i + 2)
                if end < 0:
                    raise ValueError(f"missing '}}' (variable: {var_name})")
                start = i + 2
                default_value = s[start:end]
                i = end
                expand_var(default_value)
            elif c != "}":
                raise ValueError(
                    f"position {i} '{c}' while '}}' was expected "
                    + f"(variable: {var_name})"
                )
            else:
                expand_var()
        elif is_escaped:
            is_escaped = False
            result += c
        elif c == "\\":
            is_escaped = True
        elif c == "$":
            var_name_mode = "simple"
        else:
            result += c
        i += 1

    if var_name_mode == "simple":
        expand_var()
    elif var_name_mode == "braces":
        raise ValueError(f"unterminated env var {var_name} (missing '}}')")

    return result


async def main(argv=sys.argv) -> asyncio.Future[None]:
    log("docker-entrypoint:", argv)

    wait_servers_futures: list[asyncio.Future] = []
    i = 0
    last_i = len(argv) - 1
    while i < last_i:
        i += 1
        arg = replace_env_vars(argv[i])
        if not arg.startswith("--"):
            break

        [flag, value] = split_n(arg[2:], "=", 2)
        if flag == "":
            i += 1  # stop and skip '--'
            break

        if flag == "file-env":
            if not value:
                i += 1
                value = argv[i]
                if not value:
                    die("missing --file-env value")

            handle_file_env_flag(value)

        elif flag == "wait-server":
            if not value:
                i += 1
                value = argv[i]
                if not value:
                    die("missing --wait-server value")

            wait_servers_futures.append(handle_wait_server_flag(value))

        else:
            die(f"unknown flag {flag} ({argv[i]})")

    if wait_servers_futures:
        log(f"waiting {len(wait_servers_futures)} servers...")
        await asyncio.gather(*wait_servers_futures)

    child_path = argv[i]
    if not child_path:
        die("missing python file to run")

    child_args_start = i + 1
    child_args = [replace_env_vars(a) for a in argv[child_args_start:]]
    child_args.insert(0, child_path)
    child_args.insert(0, sys.executable)
    log("fork:", child_args)
    sys.stdout.flush()
    sys.stderr.flush()
    os.execv(sys.executable, child_args)


if __name__ == "__main__":
    asyncio.run(main())
