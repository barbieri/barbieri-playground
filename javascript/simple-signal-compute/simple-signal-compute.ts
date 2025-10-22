/**
 * This is a simple example implementation that mimics Angular's signal() and computed() APIs.
 * https://angular.dev/guide/signals
 *
 * It's not feature complete, but demonstrates the basic concepts.
 */

type Getter<T> = () => T;

type NotifyDependencyUpdate = () => void;
const _needsDependencyUpdateNotificationStack: (
  | NotifyDependencyUpdate
  | undefined
)[] = [];

// yes, computed() returns a Signal<T>, while signal() returns a WritableSignal<T>
type Signal<T> = Getter<T>;
interface WritableSignal<T> extends Signal<T> {
  set(value: T): void;
  update(updater: (value: T) => T): void;
}

/**
 * Derive its value from other signals as returned by `computation` function.
 *
 * See https://angular.dev/guide/signals#computed-signals
 * and https://angular.dev/api/core/computed
 */
function computed<T>(computation: Getter<T>): Signal<T> {
  let value: T;
  let needsUpdate = true;

  const dependencies = new Set<NotifyDependencyUpdate>();

  function notifyAllDependencies(): void {
    // copy subscribers to avoid modification during iteration
    Array.from(dependencies).forEach((notifyUpdate) => notifyUpdate());
  }

  function notifyDependencyUpdate(): void {
    needsUpdate = true;
    notifyAllDependencies();
  }

  function recomputeAndNotifyDependenciesIfNeeded(): void {
    if (!needsUpdate) {
      return;
    }

    const previousValue = value;
    _needsDependencyUpdateNotificationStack.push(notifyDependencyUpdate);
    try {
      value = computation();
      needsUpdate = false;
    } catch (e) {
      console.error("Error computing value:", computation, e);
      throw e;
    } finally {
      _needsDependencyUpdateNotificationStack.pop();
    }

    if (previousValue === value) {
      return;
    }
  }

  function getter(): T {
    // do this before adding any new dependencies since the new dependency will already get the newest value,
    // thus do not need to be notified
    recomputeAndNotifyDependenciesIfNeeded();

    const parentNotifyDependencyUpdate =
      _needsDependencyUpdateNotificationStack[
        _needsDependencyUpdateNotificationStack.length - 1
      ];
    if (parentNotifyDependencyUpdate) {
      dependencies.add(parentNotifyDependencyUpdate);
    }
    return value;
  }

  return getter;
}

/**
 * A writable signal that can be read and updated.
 * Whenever the value is updated, all dependent computed signals and effects are notified.
 *
 * See https://angular.dev/guide/signals#writable-signals
 * and https://angular.dev/api/core/signal
 */
function signal<T>(initialValue: T): WritableSignal<T> {
  let value = initialValue;

  const dependencies = new Set<NotifyDependencyUpdate>();

  function notifyAllDependencies(): void {
    // copy subscribers to avoid modification during iteration
    Array.from(dependencies).forEach((notifyUpdate) => notifyUpdate());
  }

  function setter(newValue: T): void {
    if (value == newValue) {
      return;
    }

    value = newValue;
    notifyAllDependencies();
  }

  function updater(updaterFn: (value: T) => T): void {
    setter(updaterFn(value));
  }

  function getter(): T {
    const parentNotifyDependencyUpdate =
      _needsDependencyUpdateNotificationStack[
        _needsDependencyUpdateNotificationStack.length - 1
      ];
    if (parentNotifyDependencyUpdate) {
      dependencies.add(parentNotifyDependencyUpdate);
    }
    return value;
  }

  getter.set = setter;
  getter.update = updater;
  return getter;
}

/**
 * Allows reading signals without tracking dependencies.
 *
 * See https://angular.dev/api/core/untracked
 */
function untracked<T>(nonReactiveReadsFn: () => T): T {
  _needsDependencyUpdateNotificationStack.push(undefined);
  try {
    return nonReactiveReadsFn();
  } finally {
    _needsDependencyUpdateNotificationStack.pop();
  }
}

/**
 * Runs the provided `effectFn` function whenever any of the signals it depends on change.
 * To avoid tracking one or more dependencies, use `untracked()` within the effect function.
 *
 * See https://angular.dev/api/core/effect
 */
function effect(effectFn: () => void): void {
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  let runningEffect = false;

  function notifyDependencyUpdate(): void {
    if (timeoutId !== undefined) {
      return;
    }
    if (runningEffect) {
      // https://angular.dev/guide/signals#use-cases-for-effects
      // This is the reason for the warning:
      // Avoid using effects for propagation of state changes.
      // This can result in ExpressionChangedAfterItHasBeenChecked errors, infinite circular updates, or unnecessary change detection cycles
      console.warn("effect dependencies changed while it was running, this can lead to infinite loops or unnecessary updates.", effectFn);
      return;
    }

    // schedule to run effect asynchronously to batch multiple updates
    timeoutId = setTimeout(() => {
      timeoutId = undefined;
      runEffect();
    }, 0);
  }

  function runEffect(): void {
    runningEffect = true;
    _needsDependencyUpdateNotificationStack.push(notifyDependencyUpdate);
    try {
      effectFn();
    } catch (e) {
      console.error("Error running effect:", effectFn, e);
      throw e;
    } finally {
      _needsDependencyUpdateNotificationStack.pop();
      runningEffect = false;
    }
  }

  runEffect();
}

// example usage

console.log("-- BEGIN --");
const count = signal(0);
const message = signal("hello");

const doubleCount = computed(() => count() * 2);
const upperCaseMessage = computed(() => message().toLocaleUpperCase());

const nestedComputed = computed(() => `NestedComputed(doubleCount: ${doubleCount()}, upperCaseMessage: ${upperCaseMessage()})`);

const timedCount = signal(0);

effect(() => {
  // shows when any of the tracked signals change
  console.log(
    `[effect: all tracked] count: ${count()}, doubleCount: ${doubleCount()} -- message: ${message()}, upperCaseMessage: ${upperCaseMessage()} -- nestedComputed: ${nestedComputed()} -- timedCount: ${timedCount()}`
  );
});

effect(() => {
  // shows only at the beginning since all reads are untracked
  untracked(() => {
      console.log(
      `[effect: all UNTRACKED] count: ${count()}, doubleCount: ${doubleCount()} -- message: ${message()}, upperCaseMessage: ${upperCaseMessage()} -- nestedComputed: ${nestedComputed()} -- timedCount: ${timedCount()}`
    );
  });
});

effect(() => {
  // only shows when doubleCount changes
  console.log(`[effect: only doubleCount] doubleCount: ${doubleCount()}`);
});

effect(() => {
  // only shows when upperCaseMessage changes
  console.log(
    `[effect: only upperCaseMessage] upperCaseMessage: ${upperCaseMessage()}`
  );
});

effect(() => {
  // only shows when nestedComputed changes
  console.log(`[effect: only nestedComputed] nestedComputed: ${nestedComputed()}`);
});

effect(() => {
  // only shows when timedCount changes
  console.log(`[effect: only timedCount] timedCount: ${timedCount()}`);
});

// Simulate a timer that updates every second
let interval = setInterval(() => {
  console.log("-- updating timedCount --");
  timedCount.update((value) => {
    if (value === 4) {
      clearInterval(interval);
    }
    return value + 1;
  });
}, 1000);

// simulates an user input later on
setTimeout(() => {
  console.log("-- updating count --");
  count.set(1);
}, 500);

// simulates another user input later on
setTimeout(() => {
  console.log("-- updating message --");
  message.set("hi world");
}, 1500);

console.log("-- END --");
