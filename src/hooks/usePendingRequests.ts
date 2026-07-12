import { useEffect, useState } from "react";
import { requestsApi, RequestItem } from "@/api/requestsApi";
import { useApp } from "@/app/context/AppContext";

export function usePendingRequests() {
  const { token, profileUnavailable } = useApp();
  const [count, setCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function fetchRequests() {
      if (!token || profileUnavailable) {
        if (mounted) {
          setCount(0);
          setLoading(false);
        }
        return;
      }

      try {
        setLoading(true);
        const data = await requestsApi.getRequests(token);
        if (mounted) {
          setCount(data.length);
          setError(null);
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : "Failed to fetch requests count");
          setCount(0);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    fetchRequests();

    return () => {
      mounted = false;
    };
  }, [token, profileUnavailable]);

  return { count, loading, error };
}
