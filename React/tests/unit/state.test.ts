import { store, userActions, usersCalcActions, likesCalcActions, vacationsStatActions, likesStatActions } from '../../src/Redux/state';

test('store starts with empty authentication and statistics', () => {
    expect(store.getState()).toEqual({ user: null, usersCalc: null, likesCalc: null, vacationsStat: null, likesStat: [] });
});

test.each<[keyof ReturnType<typeof store.getState>, (value: any) => any, unknown]>([
    ['user', userActions.login, { id: 1, role: 'Admin' }],
    ['usersCalc', usersCalcActions.members, { total_users: 12 }],
    ['likesCalc', likesCalcActions.liked, { total_likes: 4 }],
    ['vacationsStat', vacationsStatActions.vacationsStats, { past_vacations: 1, on_going_vacations: 2, future_vacations: 3 }],
    ['likesStat', likesStatActions.likedStats, [{ destination: 'Rome', likes: 4 }]],
])('%s updates independently without mutating the previous state', (key, action, value) => {
    const previous = store.getState();
    const snapshot = JSON.parse(JSON.stringify(previous));
    store.dispatch(action(value));
    expect(store.getState()[key]).toEqual(value);
    expect(previous).toEqual(snapshot);
    (Object.keys(previous) as (keyof typeof previous)[]).filter(name => name !== key).forEach(name => expect(store.getState()[name]).toBe(previous[name]));
});

test('logout clears the authenticated user', () => {
    store.dispatch(userActions.logout(undefined));
    expect(store.getState().user).toBeNull();
});
