import { jwtDecode } from "jwt-decode";
import type { UserModel } from "../Models/UserModel";
import { store, userActions } from "../Redux/state";
import type { CredentialsModel } from "../Models/CredentialsModel";
import axios from "axios";
import { appConfig } from "../Utils/AppConfig";

class UserService {
    public constructor() {

        const token = localStorage.getItem("token");
        if (!token) return;
        try {
            const user = jwtDecode<{ user: UserModel }>(token).user;
            if (!user || !user.id) throw new Error("Invalid saved session");
            store.dispatch(userActions.login(user));
        } catch {
            localStorage.removeItem("token");
        }
    }
    public async login(credentials: CredentialsModel): Promise<void> {
        const response = await axios.post<{ access_token: string }>(appConfig.loginUrl, credentials, {
            withCredentials: true,
        });
        const token = response.data.access_token;
        if (!token) return;
        const action = userActions.login(jwtDecode<{ user: UserModel }>(token).user);
        store.dispatch(action);
        localStorage.setItem("token", token);
    }
    public async logout(): Promise<void> {
        await axios.delete<string>(appConfig.logoutUrl, { withCredentials: true });
        const action = userActions.logout();
        store.dispatch(action);
        localStorage.removeItem("token");
    }
    public async refreshToken(): Promise<void> {
        try {
            const response = await axios.get<{ access_token: string }>(appConfig.refreshUrl, {
                withCredentials: true,
            });
            const token = response.data.access_token;
            const action = userActions.login(jwtDecode<{ user: UserModel }>(token).user);
            store.dispatch(action);
            localStorage.setItem("token", token);
        } catch (err: any) {
            if (err?.response?.status === 401) {
                try {
                    await this.logout();
                } finally {
                    store.dispatch(userActions.logout());
                    localStorage.removeItem("token");
                    window.location.href = `${window.location.origin}/login`;
                }
            }
        }
    }
}

export const userService = new UserService();
