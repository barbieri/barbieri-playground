/**
 * Docker entrypoint to use gcr.io/distroless/nodejs as base.
 *
 * Distroless images don't have a shell, so the traditional setup to wait a
 * database server to be ready or replace `${var}_FILE` (ie: docker secrets)
 * is cumbersome to do.
 *
 * This file is to be built do JavaScript and copied to your project and used as `CMD`.
 * The following example waits (simple TCP connection, not a real DB connection) for
 * PostgresSQL at `${PGHOST}:${PGPORT}`. Since shell is not available, just basic variable
 * interpolation is allowed, only the special case `${VAR:-DEFAULT}` is supported.
 *
 * ```dockerfile
 * FROM gcr.io/distroless/nodejs22-debian12
 *
 * # ... copy your built files ...
 *
 * CMD [ \
 *     "/docker-entrypoint.js", \
 *     "--file-env=PGPASSWORD", \
 *     "--wait-server=${PGHOST}:${PGPORT:-5432}", \
 *     "/path/to/your-app.js" \
 * ]
 * ```
 *
 * See https://github.com/GoogleContainerTools/distroless/blob/main/nodejs/README.md
 */
import net from 'net';
export declare function die(...err: unknown[]): never;
type WaitServerOptions = {
    interval?: number;
    maxRetries?: number;
};
/**
 * Wait Server as a promise, useful to wait DB or some other dependency to be ready to use.
 */
export declare const waitServer: (connectOpts: net.TcpNetConnectOpts, { interval, maxRetries, }?: WaitServerOptions) => Promise<void>;
type FileEnvOptions = {
    defaultValue?: string;
    varFileName?: string;
    exclusive?: boolean;
    failFileReadError?: boolean;
    trimFileContents?: 'start' | 'end' | 'both' | 'none';
    required?: boolean;
};
/**
 * If needed, set `process.env[varName]` from contents of file given by `process.env[varFileName]`
 *
 * This is useful in cloud/containers/docker environments to load secrets provided as files.
 * */
export declare function fileEnv(varName: string, { defaultValue, varFileName: givenVarFileName, exclusive, failFileReadError, trimFileContents, required, }?: FileEnvOptions): void;
export declare function handleFileEnvFlag(value: string): void;
export declare function handleWaitServerFlag(value: string): Promise<void>;
export declare function main(argv?: string[]): Promise<void>;
export {};
