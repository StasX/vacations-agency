import axios from 'axios';
import { StatisticsService } from '../../src/Services/StatisticsService';
import { userService } from '../../src/Services/UserService';
import { store } from '../../src/Redux/state';
import { notify } from '../../src/Utils/Notify';
import { appConfig } from '../../src/Utils/AppConfig';

jest.mock('axios', () => ({ get: jest.fn() }));
jest.mock('../../src/Services/UserService', () => ({ userService: { refreshToken: jest.fn(), logout: jest.fn() } }));
jest.mock('../../src/Utils/Notify', () => ({ notify: { error: jest.fn() } }));

type Method = 'getUsersCount' | 'getLikesCount' | 'getVacationsStatistics' | 'getLikesStatistics';
const endpoints: [Method, keyof typeof appConfig, keyof ReturnType<typeof store.getState>, unknown][] = [
    ['getUsersCount', 'usersCountUrl', 'usersCalc', { total_users: 12 }],
    ['getLikesCount', 'likesCountUrl', 'likesCalc', { total_likes: 7 }],
    ['getVacationsStatistics', 'vacationsStatisticsUrl', 'vacationsStat', { past_vacations: 1, on_going_vacations: 2, future_vacations: 3 }],
    ['getLikesStatistics', 'likesStatisticsUrl', 'likesStat', [{ destination: 'Rome', likes: 7 }]],
];
const originalLocation = window.location;
beforeAll(() => {
    Object.defineProperty(window, 'location', { configurable: true, value: { origin: 'http://localhost', href: 'http://localhost/statistics' } });
});
afterAll(() => { Object.defineProperty(window, 'location', { configurable: true, value: originalLocation }); });

let statisticsService: StatisticsService;
beforeEach(() => {
    jest.resetAllMocks();
    statisticsService = new StatisticsService();
    jest.mocked(userService.logout).mockImplementation(async () => { localStorage.removeItem('token'); });
    localStorage.clear();
    window.location.href = 'http://localhost/statistics';
});

test.each(endpoints)('%s skips requests without a token', async (method) => {
    await statisticsService[method]();
    expect(axios.get).not.toHaveBeenCalled();
});

test.each(endpoints)('%s sends authorization and stores the response', async (method, url, key, data) => {
    localStorage.setItem('token', 'access-token');
    jest.mocked(axios.get).mockResolvedValue({ data });
    await statisticsService[method]();
    expect(axios.get).toHaveBeenCalledWith(appConfig[url], { withCredentials: true, headers: { Authorization: 'access-token' } });
    expect(store.getState()[key]).toEqual(data);
});

test.each(endpoints)('%s notifies on network failure', async (method) => {
    localStorage.setItem('token', 'access-token');
    jest.mocked(axios.get).mockRejectedValue(new Error('offline'));
    await statisticsService[method]();
    expect(notify.error).toHaveBeenCalledTimes(1);
});

test.each([null, {}, { data: [] }, [{ destination: 'Rome', likes: '7' }], [null]])(
    'invalid likes statistics do not replace the chart array: %p', async (data) => {
        localStorage.setItem('token', 'access-token');
        const previous = store.getState().likesStat;
        jest.mocked(axios.get).mockResolvedValue({ data });
        await statisticsService.getLikesStatistics();
        expect(store.getState().likesStat).toBe(previous);
        expect(notify.error).toHaveBeenCalledTimes(1);
    }
);

function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
    return { promise, resolve, reject };
}

const flushPromises = async () => { await Promise.resolve(); await Promise.resolve(); };

function successfulRefresh(): void {
    jest.mocked(userService.refreshToken).mockImplementation(async () => {
        localStorage.setItem('token', 'renewed');
    });
}

test('request waits for refresh and its own retry without fetching unrelated endpoints', async () => {
    localStorage.setItem('token', 'expired');
    const refresh = deferred<void>();
    const retry = deferred<{ data: { total_users: number } }>();
    jest.mocked(userService.refreshToken).mockReturnValue(refresh.promise);
    jest.mocked(axios.get).mockRejectedValueOnce({ response: { status: 406 } }).mockReturnValueOnce(retry.promise);
    let settled = false;
    const request = statisticsService.getUsersCount().then(() => { settled = true; });
    await flushPromises();
    expect(axios.get).toHaveBeenCalledTimes(1);
    expect(settled).toBe(false);
    localStorage.setItem('token', 'renewed');
    refresh.resolve();
    await flushPromises();
    expect(settled).toBe(false);
    retry.resolve({ data: { total_users: 42 } });
    await request;
    expect(axios.get).toHaveBeenCalledTimes(2);
    expect(axios.get).toHaveBeenLastCalledWith(appConfig.usersCountUrl,
        { withCredentials: true, headers: { Authorization: 'renewed' } });
    expect(store.getState().usersCalc).toEqual({ total_users: 42 });
});

test('simultaneous expired responses share one refresh and retry each requested endpoint', async () => {
    localStorage.setItem('token', 'expired');
    successfulRefresh();
    jest.mocked(axios.get).mockImplementation(async (url, options) => {
        if (options?.headers?.Authorization === 'expired') throw { response: { status: 406 } };
        return { data: endpoints.find(([, key]) => appConfig[key] === url)![3] };
    });
    await Promise.all(endpoints.map(([method]) => statisticsService[method]()));
    expect(userService.refreshToken).toHaveBeenCalledTimes(1);
    expect(axios.get).toHaveBeenCalledTimes(8);
    for (const [, , key, data] of endpoints) expect(store.getState()[key]).toEqual(data);
    expect(notify.error).not.toHaveBeenCalled();
});

test('a late expired response reuses the renewed token without another refresh', async () => {
    localStorage.setItem('token', 'expired');
    const late = deferred<never>();
    successfulRefresh();
    jest.mocked(axios.get).mockReturnValueOnce(late.promise)
        .mockRejectedValueOnce({ response: { status: 406 } })
        .mockResolvedValue({ data: { total_users: 5, total_likes: 2 } });
    const first = statisticsService.getUsersCount();
    await statisticsService.getLikesCount();
    late.reject({ response: { status: 406 } });
    await first;
    expect(userService.refreshToken).toHaveBeenCalledTimes(1);
    expect(axios.get).toHaveBeenCalledTimes(4);
    expect(notify.error).not.toHaveBeenCalled();
});

test.each(endpoints)('%s refreshes and retries at most once', async (method) => {
    localStorage.setItem('token', 'expired');
    successfulRefresh();
    jest.mocked(axios.get).mockRejectedValue({ response: { status: 406 } });
    await statisticsService[method]();
    expect(userService.refreshToken).toHaveBeenCalledTimes(1);
    expect(axios.get).toHaveBeenCalledTimes(2);
    expect(notify.error).toHaveBeenCalledTimes(1);
});

test.each(endpoints)('%s logs out and redirects on unauthorized responses', async (method) => {
    localStorage.setItem('token', 'invalid');
    jest.mocked(axios.get).mockRejectedValue({ response: { status: 401 } });
    await statisticsService[method]();
    expect(userService.logout).toHaveBeenCalledTimes(1);
    expect(window.location.href).toBe('http://localhost/login');
});

test('simultaneous unauthorized responses only trigger one logout', async () => {
    localStorage.setItem('token', 'invalid');
    jest.mocked(axios.get).mockRejectedValue({ response: { status: 401 } });
    await Promise.all(endpoints.map(([method]) => statisticsService[method]()));
    expect(userService.logout).toHaveBeenCalledTimes(1);
});

test('a failed shared refresh notifies once, does not retry, and allows a later attempt', async () => {
    localStorage.setItem('token', 'expired');
    jest.mocked(axios.get).mockRejectedValue({ response: { status: 406 } });
    jest.mocked(userService.refreshToken).mockRejectedValue(new Error('offline'));
    await Promise.all(endpoints.map(([method]) => statisticsService[method]()));
    expect(userService.refreshToken).toHaveBeenCalledTimes(1);
    expect(axios.get).toHaveBeenCalledTimes(4);
    expect(notify.error).toHaveBeenCalledTimes(1);
    successfulRefresh();
    jest.mocked(axios.get).mockRejectedValueOnce({ response: { status: 406 } })
        .mockResolvedValueOnce({ data: { total_users: 1 } });
    await statisticsService.getUsersCount();
    expect(userService.refreshToken).toHaveBeenCalledTimes(2);
    expect(store.getState().usersCalc).toEqual({ total_users: 1 });
});

test('a rejected refresh leaves unauthorized handling to UserService', async () => {
    localStorage.setItem('token', 'expired');
    jest.mocked(axios.get).mockRejectedValue({ response: { status: 406 } });
    jest.mocked(userService.refreshToken).mockRejectedValue({ response: { status: 401 } });
    await statisticsService.getUsersCount();
    expect(axios.get).toHaveBeenCalledTimes(1);
    expect(userService.logout).not.toHaveBeenCalled();
    expect(notify.error).not.toHaveBeenCalled();
});

test('an unauthorized retry logs out without starting another refresh', async () => {
    localStorage.setItem('token', 'expired');
    successfulRefresh();
    jest.mocked(axios.get).mockRejectedValueOnce({ response: { status: 406 } })
        .mockRejectedValueOnce({ response: { status: 401 } });
    await statisticsService.getUsersCount();
    expect(userService.refreshToken).toHaveBeenCalledTimes(1);
    expect(userService.logout).toHaveBeenCalledTimes(1);
});

test('a late unauthorized response does not log out a changed session', async () => {
    localStorage.setItem('token', 'old-session');
    const late = deferred<never>();
    jest.mocked(axios.get).mockReturnValueOnce(late.promise).mockResolvedValueOnce({ data: { total_users: 8 } });
    const request = statisticsService.getUsersCount();
    localStorage.setItem('token', 'new-session');
    late.reject({ response: { status: 401 } });
    await request;
    expect(userService.logout).not.toHaveBeenCalled();
    expect(store.getState().usersCalc).toEqual({ total_users: 8 });
});

test('responses after logout do not overwrite statistics', async () => {
    localStorage.setItem('token', 'old-session');
    const late = deferred<{ data: { total_users: number } }>();
    jest.mocked(axios.get).mockReturnValueOnce(late.promise);
    const previous = store.getState().usersCalc;
    const request = statisticsService.getUsersCount();
    localStorage.removeItem('token');
    late.resolve({ data: { total_users: 999 } });
    await request;
    expect(store.getState().usersCalc).toBe(previous);
});

test('logout failure still redirects and is reported once', async () => {
    localStorage.setItem('token', 'invalid');
    jest.mocked(axios.get).mockRejectedValue({ response: { status: 401 } });
    jest.mocked(userService.logout).mockImplementation(async () => {
        localStorage.removeItem('token');
        throw new Error('offline');
    });
    await Promise.all(endpoints.map(([method]) => statisticsService[method]()));
    expect(userService.logout).toHaveBeenCalledTimes(1);
    expect(notify.error).toHaveBeenCalledTimes(1);
    expect(window.location.href).toBe('http://localhost/login');
});

test('refresh cancelled by logout does not retry or show an extra error', async () => {
    localStorage.setItem('token', 'expired');
    const refresh = deferred<void>();
    jest.mocked(userService.refreshToken).mockReturnValue(refresh.promise);
    jest.mocked(axios.get).mockRejectedValueOnce({ response: { status: 406 } })
        .mockRejectedValueOnce({ response: { status: 401 } });
    const request = statisticsService.getUsersCount();
    await flushPromises();
    await statisticsService.getLikesCount();
    refresh.reject(new Error('Session changed during refresh'));
    await request;
    expect(axios.get).toHaveBeenCalledTimes(2);
    expect(userService.logout).toHaveBeenCalledTimes(1);
    expect(notify.error).not.toHaveBeenCalled();
});
