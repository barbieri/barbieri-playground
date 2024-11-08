# distroless-docker-entrypoint

Docker entrypoint to use `gcr.io/distroless/python3` as base.

Distroless images don't have a shell, so the traditional setup to wait a
database server to be ready or replace `${var}_FILE` (ie: docker secrets)
is cumbersome to do.

This file is pure Python and copied to your project and used as `CMD`.
The following example waits (simple TCP connection, not a real DB connection) for
PostgresSQL at `${PGHOST}:${PGPORT}`. Since shell is not available, just basic variable
interpolation is allowed, only the special case `${VAR:-DEFAULT}` is supported.

```dockerfile
FROM gcr.io/distroless/python3-debian12

# ... copy your built files ...

CMD [ \
    "/docker_entrypoint.py", \
    "--file-env=PGPASSWORD", \
    "--wait-server=${PGHOST}:${PGPORT:-5432}", \
    "/path/to/your-app.js" \
]
```

See https://github.com/GoogleContainerTools/distroless/blob/main/python3/README.md

## Distribution

You may copy the Python file to your project.

## Command Line Usage

Format:
```
python3 ./docker_entrypoint.py [docker-entrypoint-flags] app.py [app-flags]
```

Where `[docker-entrypoint-flags]` can be multiple flags as below:

### --file-env=VARNAME[:OPTIONS]

if `$VARNAME` is not defined it will check `$VARNAME_FILE` and if that
exists, it should point to a file to be read and use its contents as
`$VARNAME`. This is useful to load secrets passed to containers.

`--file-env=VARNAME:OPTIONS` allows to specify `OPTIONS` as a JSON
object with keys defined at `FileEnvOptions`:
- `defaultValue: string`: if no variables were present, set `$VARNAME` to the given value;
- `varFileName: string`: overrides default `$VARNAME_FILE`;
- `exclusive: boolean`: if true (default), will fail if both `$VARNAME` and `$VARNAME_FILE` are set;
- `failFileReadError: boolean`: if true (default), will fail if file is specified and doesn't exist;
- `trimFileContents: 'start' | 'end' | 'both' | 'none'`: if given states how to trim the value read from file, useful to remove trailing `\n` (default: `both`);
- `required: boolean`; if true (default) it will abort if the env is not provided and doesn't have a default.

### --wait-server=HOST:PORT[:OPTIONS]

Attempts to connect to the server at given `HOST` and `PORT`.
By default it will try 10 attempts with an 1000 milliseconds interval
between them. Use `OPTIONS` as a JSON object with keys defined at
`WaitServerOptions`:
- `interval` in milliseconds, defaults to 1000;
- `maxRetries` number of retries.

### Variable Substitution

Since there is no shell available in distroless images and you may
want to expand environment variables in your command (see `${PGHOST}`
and `${PGPORT:-5432}` in the examples below), these will be
automatically expanded for every command line argument.

Escaping can be done by using a backslash (`\\`).

The replacement resembles shell, but it's not as complete:
- `$VARNAME` simple form, ex `$PGHOST:$PGPORT`.
- `${VARNAME}` braces can be used, ex `${PREFIX}_SUFFIX`.
- `${VARNAME:-default value}` to provide a default value if variable is unset.

### Examples:

```bash
python3 ./docker_entrypoint.py \
    --file-env=PGPASSWORD \
    --wait-server=${PGHOST}:${PGPORT:-5432} \
    /path/to/your-app.js --app-flag --other-app=flag

# Using --file-env=VARNAME:OPTIONS
python3 ./docker_entrypoint.py \
    '--file-env=OPTIONAL_SECRET:{"required":false}' \
    '--file-env=PRESERVE_NEWLINES_AND_SPACES:{"trimFileContents":"none"}' \
    /path/to/your-app.js --app-flag --other-app=flag


# Using --wait-server=HOST:PORT:OPTIONS
python3 ./docker_entrypoint.py \
    '--wait-server=${PGHOST}:${PGPORT:-5432}:{"interval":500}' \
    /path/to/your-app.js --app-flag --other-app=flag
```

## Debugging

The environment variable `DEBUG=1` turns on console logging, which
may be useful to debug variable expansion or server connections.
