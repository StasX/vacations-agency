import axios from 'axios';
import { statisticsService } from '../../src/Services/StatisticsService';
import { userService } from '../../src/Services/UserService';
import { store } from '../../src/Redux/state';
import { notify } from '../../src/Utils/Notify';
import { appConfig } from '../../src/Utils/AppConfig';

test('retries wait for refresh completion', async () => {
    localStorage.setItem('token', 'expired');
    jest.mocked(userService.refreshToken).mockReturnValue(new Promise(() => {}));
    jest.mocked(axios.get).mockRejectedValueOnce({ response: { status: 406 } });
    await statisticsService.getUsersCount();
    jest.mocked(axios.get).mockResolvedValue({ data: {} });
    jest.mocked(axios.get).mockClear();
    jest.advanceTimersByTime(2000);
    expect(axios.get).not.toHaveBeenCalled();
});

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

beforeEach(() => {
    jest.resetAllMocks();
    jest.useFakeTimers();
    localStorage.clear();
    Reflect.set(statisticsService, 'canRefreshToken', true);
    Reflect.set(statisticsService, 'canGoToLogin', true);
    window.location.href = 'http://localhost/statistics';
});
afterEach(() => { jest.clearAllTimers(); jest.useRealTimers(); });

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

test('simultaneous expired responses trigger one refresh and retry all endpoints', async () => {
    localStorage.setItem('token', 'expired');
    jest.mocked(axios.get).mockRejectedValue({ response: { status: 406 } });
    await Promise.all(endpoints.map(([method]) => statisticsService[method]()));
    expect(userService.refreshToken).toHaveBeenCalledTimes(1);
    jest.mocked(axios.get).mockResolvedValue({ data: {} });
    jest.mocked(axios.get).mockClear();
    jest.advanceTimersByTime(1000);
    await Promise.resolve();
    expect(axios.get).toHaveBeenCalledTimes(4);
});

test.each(endpoints)('%s requests a refresh on an expired token', async (method) => {
    localStorage.setItem('token', 'expired');
    jest.mocked(axios.get).mockRejectedValue({ response: { status: 406 } });
    await statisticsService[method]();
    expect(userService.refreshToken).toHaveBeenCalledTimes(1);
});

test.each(endpoints)('%s logs out and redirects on unauthorized responses', async (method) => {
    localStorage.setItem('token', 'invalid');
    jest.mocked(axios.get).mockRejectedValue({ response: { status: 401 } });
    await statisticsService[method]();
    expect(userService.logout).toHaveBeenCalledTimes(1);
    expect(window.location.href).toBe('http://localhost/login');
    jest.advanceTimersByTime(5000);
    expect(Reflect.get(statisticsService, 'canGoToLogin')).toBe(true);
});

test('simultaneous unauthorized responses only trigger one logout', async () => {
    localStorage.setItem('token', 'invalid');
    jest.mocked(axios.get).mockRejectedValue({ response: { status: 401 } });
    await Promise.all(endpoints.map(([method]) => statisticsService[method]()));
    expect(userService.logout).toHaveBeenCalledTimes(1);
});
