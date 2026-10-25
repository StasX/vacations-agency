import axios from 'axios';
import { userService } from '../../src/Services/UserService';
import { store, userActions } from '../../src/Redux/state';
import { appConfig } from '../../src/Utils/AppConfig';

test('logout includes cookies so Django can delete the refresh cookie', async () => {
    jest.mocked(axios.delete).mockResolvedValue({});
    await userService.logout();
    expect(axios.delete).toHaveBeenCalledWith(appConfig.logoutUrl, { withCredentials: true });
});

test('a malformed saved token does not crash startup', () => {
    localStorage.setItem('token', 'broken-token');
    expect(() => jest.isolateModules(() => require('../../src/Services/UserService'))).not.toThrow();
});

jest.mock('axios', () => ({ post: jest.fn(), get: jest.fn(), delete: jest.fn() }));
const user = { id: 1, firstName: 'Ada', lastName: 'Lovelace', email: 'ada@example.com', role: 'Admin' };
const tokenFor = (value: import('../../src/Models/UserModel').UserModel) => `eyJhbGciOiJIUzI1NiJ9.${btoa(JSON.stringify({ user: value }))}.signature`;
const originalLocation = window.location;
beforeAll(() => {
    Object.defineProperty(window, 'location', { configurable: true, value: { origin: 'http://localhost', href: 'http://localhost/statistics' } });
});
afterAll(() => { Object.defineProperty(window, 'location', { configurable: true, value: originalLocation }); });

beforeEach(() => {
    jest.resetAllMocks();
    localStorage.clear();
    store.dispatch(userActions.logout(undefined));
});

test('login sends credentials with cookies and persists the decoded user', async () => {
    const token = tokenFor(user);
    const credentials = { email: user.email, password: 'secret' };
    jest.mocked(axios.post).mockResolvedValue({ data: { access_token: token } });
    await userService.login(credentials);
    expect(axios.post).toHaveBeenCalledWith(appConfig.loginUrl, credentials, { withCredentials: true });
    expect(localStorage.getItem('token')).toBe(token);
    expect(store.getState().user).toEqual(user);
});

test('rejected credentials do not create a session', async () => {
    jest.mocked(axios.post).mockRejectedValue(new Error('invalid credentials'));
    await expect(userService.login({ email: 'ada@example.com', password: 'secret' })).rejects.toThrow('invalid credentials');
    expect(store.getState().user).toBeNull();
    expect(localStorage.getItem('token')).toBeNull();
});

test('an empty login response does not create a session', async () => {
    jest.mocked(axios.post).mockResolvedValue({ data: {} });
    await userService.login({ email: 'ada@example.com', password: 'secret' });
    expect(store.getState().user).toBeNull();
});

test('logout clears the local session after a successful response', async () => {
    store.dispatch(userActions.login(user));
    localStorage.setItem('token', tokenFor(user));
    jest.mocked(axios.delete).mockResolvedValue({});
    await userService.logout();
    expect(jest.mocked(axios.delete).mock.calls[0][0]).toBe(appConfig.logoutUrl);
    expect(store.getState().user).toBeNull();
    expect(localStorage.getItem('token')).toBeNull();
});

test('refresh replaces the token and user using the refresh cookie', async () => {
    const token = tokenFor(user);
    jest.mocked(axios.get).mockResolvedValue({ data: { access_token: token } });
    await userService.refreshToken();
    expect(axios.get).toHaveBeenCalledWith(appConfig.refreshUrl, { withCredentials: true });
    expect(localStorage.getItem('token')).toBe(token);
    expect(store.getState().user).toEqual(user);
});

test('startup restores a saved session', () => {
    localStorage.setItem('token', tokenFor(user));
    jest.isolateModules(() => {
        require('../../src/Services/UserService');
        expect(require('../../src/Redux/state').store.getState().user).toEqual(user);
    });
});

test('a rejected refresh logs out and redirects to login', async () => {
    localStorage.setItem('token', tokenFor(user));
    store.dispatch(userActions.login(user));
    jest.mocked(axios.get).mockRejectedValue({ response: { status: 401 } });
    jest.mocked(axios.delete).mockResolvedValue({});
    await userService.refreshToken();
    expect(window.location.href).toBe('http://localhost/login');
    expect(store.getState().user).toBeNull();
    expect(localStorage.getItem('token')).toBeNull();
});

test('a temporary refresh failure preserves the existing session', async () => {
    const token = tokenFor(user);
    localStorage.setItem('token', token);
    store.dispatch(userActions.login(user));
    jest.mocked(axios.get).mockRejectedValue(new Error('offline'));
    await userService.refreshToken();
    expect(localStorage.getItem('token')).toBe(token);
    expect(store.getState().user).toEqual(user);
    expect(axios.delete).not.toHaveBeenCalled();
});
