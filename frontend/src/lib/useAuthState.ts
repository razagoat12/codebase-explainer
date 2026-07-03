import { useEffect, useState } from 'react';
import { getToken, subscribeAuthChanged } from '@/lib/api';

export function useAuthState(): boolean {
  const [loggedIn, setLoggedIn] = useState(() => !!getToken());

  useEffect(() => {
    const sync = () => setLoggedIn(!!getToken());
    sync();
    return subscribeAuthChanged(sync);
  }, []);

  return loggedIn;
}
