import { useSyncExternalStore } from 'react';
import { store } from '../Redux/state';

const getCurrentUser = () => store.getState().user;

export function useCurrentUser() {
    return useSyncExternalStore(store.subscribe, getCurrentUser);
}
