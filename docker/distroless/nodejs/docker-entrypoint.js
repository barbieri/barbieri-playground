"use strict";
//! Copyright (C) 2023-2024 Gustavo Sverzut Barbieri <barbieri@profusion.mobi>
//! License: MIT
//! Source: https://github.com/barbieri/barbieri-playground/tree/master/docker/distroless/nodejs/
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
/* eslint-disable no-magic-numbers */
/* eslint-disable no-labels */
/* eslint-disable no-unused-labels */
/* eslint-disable no-restricted-syntax */
Object.defineProperty(exports, "__esModule", { value: true });
exports.waitServer = void 0;
exports.die = die;
exports.fileEnv = fileEnv;
exports.handleFileEnvFlag = handleFileEnvFlag;
exports.handleWaitServerFlag = handleWaitServerFlag;
exports.main = main;
const child_process_1 = __importDefault(require("child_process"));
const fs_1 = __importDefault(require("fs"));
const net_1 = __importDefault(require("net"));
function die(...err) {
    // eslint-disable-next-line no-console
    console.error('ERROR:', ...err);
    process.exit(1);
}
const DEBUG = process.env.DEBUG === '1';
const log = 
// eslint-disable-next-line no-console
DEBUG ? console.log : () => undefined;
const waitServerDefaultOptions = {
    interval: 1000,
    maxRetries: 10,
};
/**
 * Wait Server as a promise, useful to wait DB or some other dependency to be ready to use.
 */
const waitServer = (connectOpts, { interval = waitServerDefaultOptions.interval, maxRetries = waitServerDefaultOptions.maxRetries, } = {}) => new Promise((resolve, reject) => {
    let tries = 0;
    const startTime = Date.now();
    const { host, port, ...restConnectOpts } = connectOpts;
    const connParts = [host, port].concat(Object.entries(restConnectOpts).map(([k, v]) => `${k}=${JSON.stringify(v)}`));
    const connStr = `${connParts.join(':')}:`;
    function tryServer() {
        log(`${connStr} connecting to server!`);
        const client = net_1.default.createConnection(connectOpts, () => {
            log(`${connStr} connected to server!`);
            client.end();
        });
        client.on('data', data => {
            log(`${connStr} data=${data}`);
            client.end();
        });
        client.on('end', () => {
            log(`${connStr} disconnected from server`);
            resolve();
        });
        client.on('error', error => {
            tries += 1;
            log(`${connStr} #${tries} failed to connect:`, error);
            if (tries === maxRetries) {
                const millisecondsToSeconds = 1000;
                const elapsed = (Date.now() - startTime) / millisecondsToSeconds;
                reject(new Error(`${connStr} could not connect. ${tries} tries, elapsed ${elapsed} seconds`));
            }
            setTimeout(tryServer, interval);
        });
    }
    tryServer();
});
exports.waitServer = waitServer;
const fileEnvDefaultOptions = {
    exclusive: true,
    failFileReadError: true,
    trimFileContents: 'both',
    required: true,
};
/**
 * If needed, set `process.env[varName]` from contents of file given by `process.env[varFileName]`
 *
 * This is useful in cloud/containers/docker environments to load secrets provided as files.
 * */
function fileEnv(varName, { defaultValue, varFileName: givenVarFileName, exclusive = fileEnvDefaultOptions.exclusive, failFileReadError = fileEnvDefaultOptions.failFileReadError, trimFileContents = fileEnvDefaultOptions.trimFileContents, required = fileEnvDefaultOptions.required, } = {}) {
    const { env } = process;
    const varFileName = givenVarFileName ?? `${varName}_FILE`;
    const varValue = env[varName];
    const varFileNameValue = env[varFileName];
    log('fileEnv', { varName, varValue, varFileName, varFileNameValue });
    if (exclusive && varValue && varFileNameValue) {
        throw new Error(`both ${varName} and ${varFileName} are set, but they are mutually exclusive!`);
    }
    if (varValue) {
        return;
    }
    if (varFileNameValue) {
        try {
            let fileValue = fs_1.default.readFileSync(varFileNameValue, { encoding: 'utf-8' });
            switch (trimFileContents) {
                case 'both':
                    fileValue = fileValue.trim();
                    break;
                case 'start':
                    fileValue = fileValue.trimStart();
                    break;
                case 'end':
                    fileValue = fileValue.trimEnd();
                    break;
                case 'none':
                default:
                    break;
            }
            log(`fileEnv: set ${varName}=${JSON.stringify(fileValue)}`);
            env[varName] = fileValue;
            return;
        }
        catch (e) {
            if (failFileReadError) {
                throw e;
            }
            // else keep going and use the default
        }
    }
    if (defaultValue !== undefined) {
        env[varName] = defaultValue;
        return;
    }
    if (required) {
        throw new Error(`missing environment variable ${varName} (alternatively loaded from ${varFileName})`);
    }
}
// split(separator, count) will not keep the separator in the final part as we need
function splitN(s, separator, count) {
    const result = [];
    let remaining = s;
    while (result.length < count - 1) {
        const i = remaining.indexOf(separator);
        if (i < 0) {
            break;
        }
        result.push(remaining.substring(0, i));
        remaining = remaining.substring(i + 1);
    }
    result.push(remaining);
    return result;
}
function handleFileEnvFlag(value) {
    const [varName, optionsJson] = splitN(value, ':', 2);
    const options = optionsJson ? JSON.parse(optionsJson) : undefined;
    return fileEnv(varName, options);
}
function handleWaitServerFlag(value) {
    const [host, portStr, optionsJson] = splitN(value, ':', 3);
    const options = optionsJson ? JSON.parse(optionsJson) : undefined;
    if (!host) {
        throw new Error(`missing host, format: host:port[:options]`);
    }
    if (!portStr) {
        throw new Error(`missing port, format: host:port[:options]`);
    }
    const port = Number(portStr);
    return (0, exports.waitServer)({ host, port }, options);
}
const varNameRegExp = /[A-Za-z0-9_]/;
function replaceEnvVars(s) {
    let result = '';
    let isEscaped = false;
    let varNameMode;
    let varName = '';
    function expandVar(defaultValue) {
        const value = process.env[varName];
        if (value === undefined && defaultValue === undefined) {
            log(`missing env var ${varName} (expanded to empty string)`);
        }
        result += value ?? defaultValue ?? '';
        varName = '';
        varNameMode = undefined;
    }
    for (let i = 0; i < s.length; i += 1) {
        const c = s[i];
        if (varNameMode === 'simple') {
            if (varNameRegExp.test(c)) {
                varName += c;
            }
            else if (c === '{') {
                varNameMode = 'braces';
            }
            else {
                i -= 1; // process this character again so it's added to result later
                expandVar();
            }
        }
        else if (varNameMode === 'braces') {
            if (varNameRegExp.test(c)) {
                varName += c;
            }
            else if (c === ':' && s[i + 1] === '-') {
                const end = s.indexOf('}', i + 2); // not strictly correct as cannot handle other vars or escaping, but ok...
                if (end < 0) {
                    throw new Error(`missing '}' (variable: ${varName})`);
                }
                const defaultValue = s.substring(i + 2, end);
                i = end + 1;
                expandVar(defaultValue);
            }
            else if (c !== '}') {
                // TODO: ${X:+value}, ${X#pattern}, ${X%pattern}, ${X%%pattern}...
                throw new Error(`position ${i} '${c}' while '}' was expected (variable: ${varName})`);
            }
            else {
                expandVar();
            }
        }
        else if (isEscaped) {
            isEscaped = false;
            result += c;
        }
        else if (c === '\\') {
            isEscaped = true;
        }
        else if (c === '$') {
            varNameMode = 'simple';
        }
        else {
            result += c;
        }
    }
    if (varNameMode === 'simple') {
        expandVar();
    }
    else if (varNameMode === 'braces') {
        throw new Error(`unterminated env var ${varName} (missing '}')`);
    }
    return result;
}
async function main(argv = process.argv) {
    log('docker-entrypoint:', argv);
    const waitServersPromises = [];
    let i = 2;
    for (; i < argv.length; i += 1) {
        const arg = replaceEnvVars(argv[i]);
        if (!arg.startsWith('--')) {
            break;
        }
        // eslint-disable-next-line prefer-const
        let [flag, value] = splitN(arg.substring(2), '=', 2);
        if (flag === '') {
            i += 1; // stop and skip '--'
            break;
        }
        switch (flag) {
            case 'file-env':
                if (!value) {
                    i += 1;
                    value = argv[i];
                    if (!value) {
                        die('missing --file-env value');
                    }
                }
                handleFileEnvFlag(value);
                break;
            case 'wait-server':
                if (!value) {
                    i += 1;
                    value = argv[i];
                    if (!value) {
                        die('missing --wait-server value');
                    }
                }
                waitServersPromises.push(handleWaitServerFlag(value));
                break;
            default:
                die(`unknown flag ${flag} (${argv[i]})`);
        }
    }
    if (waitServersPromises.length) {
        log(`waiting ${waitServersPromises.length} servers...`);
        await Promise.all(waitServersPromises);
    }
    const modulePath = argv[i];
    if (!modulePath) {
        die('missing javascript file to run');
    }
    const childArgs = argv.slice(i + 1).map(replaceEnvVars);
    log('fork:', modulePath, childArgs);
    child_process_1.default.fork(modulePath, childArgs);
}
function isMain() {
    if (process.argv.length === 1) {
        return false; // interactive node prompt
    }
    // https://esbuild.github.io/api/#drop-labels
    CJS: return require.main === module;
    // NOTE: the following import.meta causes a harmless warning from esbuild
    // it will be removed by esbuild itself later on due --drop-labels=ESM
    // @ts-ignore this will be available in ESM modules
    ESM: return import.meta?.filename === process.argv[1];
    return false;
}
if (isMain()) {
    main().catch((error) => die(error));
}
