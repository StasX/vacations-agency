import { jwtDecode } from "jwt-decode";
import type { UserModel } from "../Models/UserModel";
import { store, userActions } from "../Redux/state";
import type { CredentialsModel } from "../Models/CredentialsModel";
import axios from "axios";
import { appConfig } from "../Utils/AppConfig";

class UserService {
    private refreshRequest: Promise<void> | null = null;
    private sessionVersion = 0;

    private clearSession(): void {
        store.dispatch(userActions.logout());
        localStorage.removeItem("token");
    }

    private async csrfOptions(): Promise<{ withCredentials: true; headers: Record<string, string> }> {
        const response = await axios.get<{ csrf_token: string }>(appConfig.csrfUrl, { withCredentials: true });
        if (!response.data.csrf_token) throw new Error("Missing CSRF token");
        return { withCredentials: true, headers: { "X-CSRFToken": response.data.csrf_token } };
    }

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
        const version = ++this.sessionVersion;
        if (this.refreshRequest) await this.refreshRequest.catch(() => undefined);
        const options = await this.csrfOptions();
        const response = await axios.post<{ access_token: string }>(appConfig.loginUrl, credentials, options);
        const token = response.data.access_token;
        if (!token || version !== this.sessionVersion) return;
        const action = userActions.login(jwtDecode<{ user: UserModel }>(token).user);
        store.dispatch(action);
        localStorage.setItem("token", token);
    }
    public async logout(): Promise<void> {
        ++this.sessionVersion;
        const token = localStorage.getItem("token");
        this.clearSession();
        if (this.refreshRequest) await this.refreshRequest.catch(() => undefined);
        const options = await this.csrfOptions();
        if (token) options.headers.Authorization = token;
        await axios.delete(appConfig.logoutUrl, options);
    }
    public refreshToken(): Promise<void> {
        if (!this.refreshRequest) {
            this.refreshRequest = this.performRefresh().finally(() => { this.refreshRequest = null; });
        }
        return this.refreshRequest;
    }
    private async performRefresh(): Promise<void> {
        const version = this.sessionVersion;
        try {
            const options = await this.csrfOptions();
            if (version !== this.sessionVersion) throw new Error("Session changed during refresh");
            const response = await axios.post<{ access_token: string }>(appConfig.refreshUrl, {}, options);
            if (version !== this.sessionVersion) throw new Error("Session changed during refresh");
            const token = response.data.access_token;
            if (!token) throw new Error("Missing access token");
            const action = userActions.login(jwtDecode<{ user: UserModel }>(token).user);
            store.dispatch(action);
            localStorage.setItem("token", token);
        } catch (err: any) {
            if (version === this.sessionVersion && err?.response?.status === 401) {
                ++this.sessionVersion;
                this.clearSession();
                window.location.href = `${window.location.origin}/login`;
            }
            throw err;
        }
    }
}

export const userService = new UserService();
