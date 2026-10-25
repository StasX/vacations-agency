import { act, type ReactNode } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useNavigate, useNavigationType } from 'react-router-dom';
import { Login } from '../../src/Components/LoginArea/login/login';
import { Routing } from '../../src/Components/LayoutArea/Routing/Routing';
import { Header } from '../../src/Components/LayoutArea/Header/Header';
import { Footer } from '../../src/Components/LayoutArea/Footer/Footer';
import { Layout } from '../../src/Components/LayoutArea/Layout/Layout';
import { Statistics } from '../../src/Components/StatisticsArea/Statistics/Statistics';
import { userService } from '../../src/Services/UserService';
import { statisticsService } from '../../src/Services/StatisticsService';
import { notify } from '../../src/Utils/Notify';
import { store, userActions, usersCalcActions, likesCalcActions, vacationsStatActions, likesStatActions } from '../../src/Redux/state';

test('statistics updates when responses arrive after one second', () => {
    store.dispatch(userActions.login(admin));
    jest.mocked(statisticsService.getUsersCount).mockImplementation(async () => { setTimeout(() => store.dispatch(usersCalcActions.members({ total_users: 42 })), 2000); });
    at(<Statistics />);
    act(() => jest.advanceTimersByTime(3000));
    expect(screen.getByText('42')).toBeInTheDocument();
});

test('header releases its polling timer when unmounted', () => {
    const { unmount } = at(<Header />, '/home');
    unmount();
    expect(jest.getTimerCount()).toBe(0);
});

jest.mock('../../src/Services/UserService', () => ({ userService: { login: jest.fn(), logout: jest.fn() } }));
jest.mock('../../src/Services/StatisticsService', () => ({ statisticsService: {
    getUsersCount: jest.fn(), getLikesCount: jest.fn(), getVacationsStatistics: jest.fn(), getLikesStatistics: jest.fn(),
} }));
jest.mock('../../src/Utils/Notify', () => ({ notify: { error: jest.fn() } }));
jest.mock('@mui/x-charts/PieChart', () => ({ PieChart: ({ series }: { series: { data: unknown[] }[] }) => <div data-testid="chart">{JSON.stringify(series[0].data)}</div> }));

const admin = { id: 1, firstName: 'Ada', lastName: 'Lovelace', email: 'ada@example.com', role: 'Admin' };
const at = (component: ReactNode, path = '/') => render(<MemoryRouter initialEntries={[path]}>{component}</MemoryRouter>);

beforeEach(() => {
    jest.resetAllMocks();
    jest.useFakeTimers();
    store.dispatch(userActions.logout(undefined));
    store.dispatch(usersCalcActions.members({ total_users: 0 }));
    store.dispatch(likesCalcActions.liked({ total_likes: 0 }));
    store.dispatch(vacationsStatActions.vacationsStats({ past_vacations: 0, on_going_vacations: 0, future_vacations: 0 }));
    store.dispatch(likesStatActions.likedStats([]));
});
afterEach(() => { jest.clearAllTimers(); jest.useRealTimers(); });

function fillLogin(password = 'secret') {
    fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: admin.email } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: password } });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));
}

test('login submits credentials and navigates on success', async () => {
    jest.mocked(userService.login).mockResolvedValue(undefined);
    at(<Routes><Route path="/login" element={<Login />} /><Route path="/home" element={<p>Welcome home</p>} /></Routes>, '/login');
    fillLogin();
    expect(await screen.findByText('Welcome home')).toBeInTheDocument();
    expect(userService.login).toHaveBeenCalledWith({ email: admin.email, password: 'secret' });
});

test('short passwords prevent submission', async () => {
    at(<Login />);
    fillLogin('abc');
    expect(await screen.findByText('Password must be at least 4 characters')).toBeInTheDocument();
    expect(userService.login).not.toHaveBeenCalled();
});

test.each([
    [{ response: { status: 400 } }, "You can't login with this credentials."],
    [new Error('offline'), 'Unable to reach the server. Please check your connection.'],
    [{ response: { status: 500 } }, 'Something went wrong. Please try again.'],
])('login displays a useful error for %p', async (error, message) => {
    jest.mocked(userService.login).mockRejectedValue(error);
    at(<Login />);
    fillLogin();
    expect(await screen.findByRole('alert')).toHaveTextContent(message);
});

test.each(['/', '/home', '/statistics', '/about'])('anonymous users visiting %s are redirected to login', async (path) => {
    at(<Routing />, path);
    expect(await screen.findByRole('button', { name: /sign in/i })).toBeInTheDocument();
});

test('routing redirects signed-in admins away from login', () => {
    store.dispatch(userActions.login(admin));
    at(<Routing />, '/login');
    expect(screen.getByRole('heading', { name: 'Explanation about the system.' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /sign in/i })).not.toBeInTheDocument();
});

test('non-admin users are redirected to login', async () => {
    store.dispatch(userActions.login({ ...admin, role: 'User' }));
    at(<Routing />, '/statistics');
    expect(await screen.findByRole('button', { name: /sign in/i })).toBeInTheDocument();
});

test('unauthorized statistics visits never start protected requests', () => {
    at(<Routing />, '/statistics');
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    Object.values(statisticsService).forEach(method => expect(method).not.toHaveBeenCalled());
});

test('losing admin access redirects an already mounted protected route', () => {
    store.dispatch(userActions.login(admin));
    at(<Routing />, '/home');
    expect(screen.getByRole('heading', { name: 'Explanation about the system.' })).toBeInTheDocument();
    act(() => { store.dispatch(userActions.login({ ...admin, role: 'User' })); });
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Explanation about the system.' })).not.toBeInTheDocument();
});

test('unauthorized redirects replace the protected entry in browser history', () => {
    function HistoryControls() {
        const navigate = useNavigate();
        const navigationType = useNavigationType();
        return <><span data-testid="navigation-type">{navigationType}</span><button onClick={() => navigate(-1)}>Back</button></>;
    }
    render(<MemoryRouter initialEntries={['/missing', '/statistics']}>
        <HistoryControls /><Routing />
    </MemoryRouter>);
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    expect(screen.getByTestId('navigation-type')).toHaveTextContent('REPLACE');
    fireEvent.click(screen.getByRole('button', { name: 'Back' }));
    expect(screen.getByRole('heading', { name: 'Page not found!' })).toBeInTheDocument();
});

test.each([
    ['/home', 'Explanation about the system.'],
    ['/about', 'About me:'],
    ['/', 'Explanation about the system.'],
    ['/missing', 'Page not found!'],
])('route %s displays its screen', (path, heading) => {
    store.dispatch(userActions.login(admin));
    at(<Routing />, path);
    expect(screen.getByRole('heading', { name: heading })).toBeInTheDocument();
});

test('login page hides authenticated navigation', () => {
    at(<Header />, '/login');
    expect(() => screen.getByRole('button', { name: 'Statistics' })).toThrow();
    expect(() => screen.getByText('Logout')).toThrow();
});

test('header displays the user and supports navigation', () => {
    jest.useFakeTimers();
    store.dispatch(userActions.login(admin));
    at(<><Header /><Routes><Route path="/statistics" element={<p>Dashboard destination</p>} /></Routes></>);
    act(() => jest.advanceTimersByTime(1500));
    expect(screen.getByText('Ada Lovelace')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Statistics' }));
    expect(screen.getByText('Dashboard destination')).toBeInTheDocument();
});

test('header logs out and navigates to login', async () => {
    jest.mocked(userService.logout).mockResolvedValue(undefined);
    at(<><Header /><Routes><Route path="/login" element={<p>Login destination</p>} /></Routes></>, '/home');
    fireEvent.click(screen.getByText('Logout'));
    expect(await screen.findByText('Login destination')).toBeInTheDocument();
    expect(userService.logout).toHaveBeenCalledTimes(1);
});

test('header reports logout failures', async () => {
    jest.mocked(userService.logout).mockRejectedValue(new Error('offline'));
    at(<Header />, '/home');
    fireEvent.click(screen.getByText('Logout'));
    await waitFor(() => expect(notify.error).toHaveBeenCalledTimes(1));
});

test('footer displays the current year', () => {
    render(<Footer />);
    expect(screen.getByText(/All rights reserved/)).toHaveTextContent(String(new Date().getFullYear()));
});

test('layout composes the header, routed screen, and footer', () => {
    at(<Layout />, '/login');
    expect(screen.getByAltText('Logo')).toBeInTheDocument();
    expect(screen.getByRole('main')).toContainElement(screen.getByRole('button', { name: /sign in/i }));
    expect(screen.getByText(/All rights reserved/)).toBeInTheDocument();
});

test('statistics displays counts and chart data returned by services', () => {
    jest.useFakeTimers();
    store.dispatch(userActions.login(admin));
    jest.mocked(statisticsService.getUsersCount).mockImplementation(async () => { store.dispatch(usersCalcActions.members({ total_users: 42 })); });
    jest.mocked(statisticsService.getLikesCount).mockImplementation(async () => { store.dispatch(likesCalcActions.liked({ total_likes: 17 })); });
    jest.mocked(statisticsService.getVacationsStatistics).mockImplementation(async () => { store.dispatch(vacationsStatActions.vacationsStats({ past_vacations: 2, on_going_vacations: 3, future_vacations: 4 })); });
    jest.mocked(statisticsService.getLikesStatistics).mockImplementation(async () => { store.dispatch(likesStatActions.likedStats([{ destination: 'Rome', likes: 17 }])); });
    at(<Statistics />);
    act(() => jest.advanceTimersByTime(1000));
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('17')).toBeInTheDocument();
    expect(screen.getAllByTestId('chart')[0]).toHaveTextContent('Future vacations. (4)');
    expect(screen.getAllByTestId('chart')[1]).toHaveTextContent('Rome (17)');
    Object.values(statisticsService).forEach(method => expect(method).toHaveBeenCalledTimes(1));
});
