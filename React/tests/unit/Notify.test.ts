export {};
jest.mock('notyf', () => ({ Notyf: jest.fn().mockImplementation(() => ({ error: jest.fn() })) }));

test('reports errors through a visible, dismissible notification', () => {
    // Instantiate inside the test because CRA clears mock call history per test.
    jest.resetModules();
    const { notify: freshNotify } = require('../../src/Utils/Notify');
    const { Notyf: FreshNotyf } = require('notyf');
    expect(FreshNotyf).toHaveBeenCalledWith({ duration: 3000, position: { x: 'center', y: 'top' }, dismissible: true });
    freshNotify.error();
    expect(FreshNotyf.mock.results[0].value.error).toHaveBeenCalledWith('Something went wrong. Please try again');
});
