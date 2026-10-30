// Share a successful read, but do not permanently cache a transient failure.
// Calls after a rejection are explicit new reads, never automatic retries.
export function recoverableResource<T>(load: () => Promise<T>): () => Promise<T> {
  let pending: Promise<T> | undefined;
  return () => {
    pending ??= Promise.resolve().then(load).catch(error => {
      pending = undefined;
      throw error;
    });
    return pending;
  };
}
