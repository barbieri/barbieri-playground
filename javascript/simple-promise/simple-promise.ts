type ResultOrPromise<R> = R | PromiseLike<R>;

/**
 * Used by `then(onFulFilled)`,
 * receives the original input result (`I`) and
 * returns another, possibly converted, output result (`O`).
 *
 * Optionally may throw, that continues as a rejection (`catch()`) for the next promise.
 */
type SimplePromiseOnFulfilled<I, O = I> =
  | undefined
  | null
  | ((result: I) => ResultOrPromise<O>);

/**
 * Used by `then(_, onRejected)` or `catch(onRejected)`,
 * receives the error reason (`E`) and
 * returns an output result (`O`).
 *
 * If the function does not throw, then the promise chain continues to the next `then()`.
 * If the function throws, then it will keep the rejection chain for the next promise.
 */
type SimplePromiseOnRejected<E, O> =
  | undefined
  | null
  | ((reason: E) => ResultOrPromise<O>);

/**
 * The resolver is called by the executor to report the result of the promise, which may be another promise.
 * If the result is a promise, then it will be unwrapped automatically.
 */
type SimplePromiseResolver<R> = (result: ResultOrPromise<R>) => void;

/**
 * The rejector is called by the executor to report the error of the promise.
 */
type SimplePromiseRejector<E> = (reason: E) => void;

/**
 * The executor is always called right away from inside the `SimplePromise` constructor.
 *
 * It's always called and called only once.
 *
 * The executor should call either `resolve` or `reject` exactly once.
 *
 * If the executor throws, then `reject()` is called automatically.
 */
type SimplePromiseExecutor<R, E> = (
  resolve: SimplePromiseResolver<R>,
  reject: SimplePromiseRejector<E>,
) => void;

/**
 * Internal class to represent the next promise in the chain, created by `then()` or `catch()`.
 *
 * The constructor callbacks `onFulfilled` and `onRejected` are the ones provided to
 * `SimplePromise.then(onFulfilled, onRejected)` or `SimplePromise.catch(onRejected)`.
 *
 * It exposes a new `promise: SimplePromise<ResultOutput, ErrorOutput>` that
 * will be resolved or rejected when the public methods `resolve()` or `reject()` are called,
 * effectively chaining the promises.
 *
 * @internal
 */
class SimplePromiseNext<ResultInput, ErrorInput, ResultOutput = ResultInput, ErrorOutput = ErrorInput> {
  // Callbacks given to `SimplePromise.then()` or `SimplePromise.catch()`.
  private readonly _onFulfilled: SimplePromiseOnFulfilled<ResultInput, ResultOutput>;
  private readonly _onRejected: SimplePromiseOnRejected<ErrorInput, ResultOutput>;

  /**
   * The internal promise that will be resolved or rejected when `resolve()` or `reject()` are called.
   */
  public readonly promise: SimplePromise<ResultOutput, ErrorOutput>;

  // These will always be set, but not immediately in the constructor, rather when the promise executor is called.
  private _resolve!: SimplePromiseResolver<ResultOutput>;
  private _reject!: SimplePromiseRejector<ErrorOutput>;

  constructor(
    onFulfilled: SimplePromiseOnFulfilled<ResultInput, ResultOutput>,
    onRejected: SimplePromiseOnRejected<ErrorInput, ResultOutput>,
  ) {
    this._onFulfilled = onFulfilled;
    this._onRejected = onRejected;
    this.promise = new SimplePromise<ResultOutput, ErrorOutput>((resolve, reject) => {
      this._resolve = resolve;
      this._reject = reject;
    });
  }

  /**
   * Called by the previous promise in the chain when it is fulfilled, will call `onFulFilled` if given.
   *
   * @internal
   */
  public resolve(inputResult: ResultInput): void {
    if (!this._onFulfilled) {
      // No then(), just propagate the result as is to the next.
      this._resolve(inputResult as unknown as ResultOutput);
      return;
    }

    try {
      const outputResult = this._onFulfilled(inputResult);
      this._resolve(outputResult);
    } catch (reason) {
      this._reject(reason as ErrorOutput);
    }
  }

  /**
   * Called by the previous promise in the chain when it is rejected, will call `onRejected` if given.
   *
   * @internal
   */
  public reject(reason: ErrorInput): void {
    if (!this._onRejected) {
      // No catch(), just propagate the error reason as is to the next.
      this._reject(reason as unknown as ErrorOutput);
      return;
    }

    try {
      const outputResult = this._onRejected(reason);
      this._resolve(outputResult);
    } catch (reason) {
      this._reject(reason as ErrorOutput);
    }
  }
}

/**
 * Educative example of a very simple Promise implementation in pure TypeScript.
 *
 * This complies with https://promisesaplus.com/
 *
 * It mimics the native JavaScript Promise, but is more strict in some aspects for clarity:
 * - Only one `then()` or `catch()` is allowed per promise for clarity.
 *   If multiple are needed, we could use an array of `SimplePromiseNext`.
 * - It throws if `resolve()` or `reject()` are called more than once.
 * - It logs if the value is resolved or rejected but there is no `then()` or `catch()`.
 * - No utilities such as `finally()`, `all()`, `race()`, etc.
 * - The "stack that contains only platform code" requirement is implemented with a 0ms timeout.
 *
 * Note that the JS implementation calls both ends `Promise`,
 * in other languages they are called `Future` and `Promise`,
 * being the `Promise` end the one that can be resolved or rejected,
 * while the `Future` end is the one that can be awaited with `then()` or `catch()`.
 */
class SimplePromise<R, E = unknown> {
  private _state: 'pending' | 'awaiting' | 'fulfilled' | 'rejected';

  private get _isSettled(): boolean {
    return this._state === 'fulfilled' || this._state === 'rejected';
  }

  constructor(executor: SimplePromiseExecutor<R, E>) {
    this._state = 'pending';
    try {
      executor(this._resolve, this._reject);
    } catch (reason) {
      this._reject(reason as E);
    }
  }

  // -- SECTION: Utilities

  /**
   * Let's use a 0ms timeout to comply with the "stack that contains only platform code" condition.
   *
   * This could be replaced with `process.nextTick()` in Node.js or
   * `requestIdleCallback()` in newer browsers.
   */
  private _timeoutId: ReturnType<typeof setTimeout> | undefined;

  private _runWithOnlyPlatformCode(fn: () => void) {
    if (this._timeoutId !== undefined) {
      throw new Error('Programming error: should not schedule two things at once');
    }
    this._timeoutId = setTimeout(() => {
      this._timeoutId = undefined;
      fn();
    }, 0);
  }

  // -- SECTION: Fulfillment and Rejection

  /**
   * If the result is another promise, then we need to await for it.
   * Otherwise, we can just resolve with the value.
   *
   * Returns true if the result was a promise and we are now awaiting it.
   * Returns false if the result was a value and we can continue resolving.
   */
  private _handlePromiseLikeResult(result: R | PromiseLike<R>): result is PromiseLike<R> {
    if (!result || typeof result !== 'object' || !('then' in result)) {
      return false;
    }

    // Another promise was given, await for its results or rejection.
    this._state = 'awaiting';
    result.then(this._resolve, this._reject);
    return true;
  }

  /**
   * Called by the provided executor to report the value of the promise.
   *
   * It must not be previously settled and it will settle as `fulfilled`
   * if the given `result` is not a promise, otherwise it will
   * change the state to `awaiting` until the given promise settles.
   *
   * It must be called **at most once**, otherwise it will throw.
   * Whenever called after `_reject()`, it will throw as well.
   */
  private readonly _resolve = (result: ResultOrPromise<R>) => {
    if (this._isSettled) {
      // JS Promise does not throw here, but we will for clarity.
      throw new Error('Promise already settled, cannot resolve');
    }

    if (this._handlePromiseLikeResult(result)) {
      return;
    }

    this._state = 'fulfilled';
    this._runWithOnlyPlatformCode(() => {
        if (!this._next) {
          if (result !== undefined) {
            // JS Promise is silent here, just ignores. Let's show debug for clarity.
            console.debug('Promise resolved, but no then():', result);
          }
          return;
        }
        this._next.resolve(result);
    });
  };

  /**
   * Called by the provided executor to report the error of the promise.
   *
   * It must not be previously settled and it will settle as `rejected`.
   *
   * It must be called **at most once**, otherwise it will throw.
   * Whenever called after `_resolve()`, it will throw as well.
   */
  private readonly _reject = (error: E) => {
    if (this._isSettled) {
      // JS Promise does not throw here, but we will for clarity.
      throw new Error('Promise already settled, cannot reject');
    }

    this._state = 'rejected';
    this._runWithOnlyPlatformCode(() => {
        if (!this._next) {
          // JS Promise logs this as an error as well.
          console.error('Promise rejected, but no catch():', error);
          return;
        }
        this._next.reject(error);
    });
  };

  // -- SECTION: Then-able

  /**
   * The next promise in the chain, created by `then()` or `catch()`.
   *
   * Only one `then()` or `catch()` is allowed per promise for clarity.
   * If multiple are needed, we could use an array of `SimplePromiseNext` instead of a single one,
   * but that would complicate the implementation.
   */
  private _next: SimplePromiseNext<any, any> | undefined;

  public then<R2, E2 = E>(
    onFulfilled?: SimplePromiseOnFulfilled<R, R2>,
    onRejected?: SimplePromiseOnRejected<E, R2>,
  ): SimplePromise<R2, E2> {
    if (this._next) {
      // JS Promise allows multiple then()/catch() calls, but we will not for clarity.
      // We could support it with an array of `SimplePromiseNext` instead of a single one.
      throw new Error('Programming error: then()/catch() called twice on the same promise');
    }
    const next = new SimplePromiseNext<R, E, R2, E2>(onFulfilled, onRejected);
    this._next = next;
    return next.promise;
  }

  public catch<R2, E2 = E>(
    onRejected?: SimplePromiseOnRejected<E, R2>,
  ): SimplePromise<R2, E2> {
    if (this._next) {
      // JS Promise allows multiple then()/catch() calls, but we will not for clarity.
      // We could support it with an array of `SimplePromiseNext` instead of a single one.
      throw new Error('Programming error: then()/catch() called twice on the same promise');
    }
    const next = new SimplePromiseNext<R, E, R2, E2>(undefined, onRejected);
    this._next = next;
    return next.promise;
  }
}

const p1 = new SimplePromise<number>((resolve) => {
  resolve(0);
});
p1.then((value) => { // value type is: number
  console.log('p1: resolved with', value, '-- should be: 0');
  return 'string-here';
}).then((value) => { // value type is: string
  console.log('p1.then(): resolved with', value, '-- should be: string-here');
  return 123;
});
// should get a log of "Promise resolved, but no then(): 123" here

const p2 = new SimplePromise<never, Error>((_, reject) => {
  reject(new Error('forced error for testing'));
});
p2.catch((reason) => { // reason type is: Error
  console.log('p2: rejected with', reason, '-- should be: forced error for testing');
  return 1;
}).then((value) => { // value type is: number
  console.log('p2.catch(): resolved with', value, '-- should be: 1');
});
// no lots here since we return `undefined`, it's a special case

const p3 = new SimplePromise<number>((resolve) => {
  try {
    resolve(42);
    resolve(43); // should throw!
  } catch (e) {
    console.log('p3: error calling resolve() twice:', e, '-- should be: Promise already settled, cannot resolve');
  }
});
p3.then((value) => {
  console.log('p3: resolved with', value, '-- should be: 42');
});

const p4 = new SimplePromise<number>(() => {
  throw new Error('forced error from executor');
});
p4.catch((reason) => {
  console.log('p4: rejected with', reason, '-- should be: forced error from executor');
});