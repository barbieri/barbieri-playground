/**
 * Create an executor that handles multiple concurrent/parallel requests, but execute only once and deliver the response to all requests.
 *
 * This is handy for refresh tokens, where multiple API calls may be done in parallel,
 * they may fail due `401 - Unauthorized`, which will trigger the refresh token process,
 * but only a single refresh call should be done to get the new access token,
 * which should be later delivered to all requesters of refresh token process.
 */
function createHandleMultipleRequestsSingleExecution<T>(executor: () => Promise<T>): () => Promise<T> {
  type PendingPromises = Readonly<{
    resolve: (value: T) => void; 
    reject: (reason: any) => void;
  }>;

  let pending: PendingPromises[] | undefined;

  function resolveAll(value: T): void {
    const all = pending;
    pending = undefined;
    all!.forEach(({ resolve }) => resolve(value));
  }

  function rejectAll(reason: any): void {
    const all = pending;
    pending = undefined;
    all!.forEach(({ reject }) => reject(reason));
  }

  return function execute(): Promise<T> {
    if (!pending) {
      executor().then(resolveAll, rejectAll);
      pending = [];
    }

    return new Promise<T>((resolve, reject) => {
      pending!.push({ resolve, reject });
    });
  }
}

// example usage:
async function exampleRefreshToken(): Promise<void> {
  // this would load the refresh token from the storage and call the server
  let counter = 0;
  function actualRefreshToken(): Promise<string> {
    return new Promise((resolve) => {
      console.log('called actualRefreshToken, counter:', counter);
      setTimeout(() => {
        resolve(`token:${counter}`);
        counter++;
      }, 100);
    });
  }

  // this would handle multiple calls in parallel, doing a single call to the server
  const refreshToken = createHandleMultipleRequestsSingleExecution(actualRefreshToken);

  for (let i = 0; i < 3; i++) {
    console.log(`run=${i}: call 3x refreshToken() in parallel`);
    const allAccessTokens = await Promise.all([
      refreshToken(),
      refreshToken(),
      refreshToken(),
    ]);
    console.log(`run=${i}: all access tokens:`, allAccessTokens);
    const firstAccessToken = allAccessTokens[0];
    if (!allAccessTokens.every((token) => token === firstAccessToken)) {
      throw new Error('tokens must all be the same');
    }
  }
}
exampleRefreshToken();
