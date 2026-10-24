import axios from "axios";
import { appConfig } from "../Utils/AppConfig";
import { userService } from "./UserService";
import { likesCalcActions, likesStatActions, store, usersCalcActions, vacationsStatActions } from "../Redux/state";
import { notify } from "../Utils/Notify";

class StatisticsService {
    protected token: string = "";
    protected canRefreshToken: boolean;
    protected canGoToLogin: boolean;
    public constructor() {
        this.canRefreshToken = true;
        this.canGoToLogin = true;
    }
    public async getUsersCount(): Promise<void> {
        this.token = localStorage.getItem("token") || "";
        if (!this.token) return;

        try {
            const response = await axios.get(appConfig.usersCountUrl, { withCredentials: true, headers: { "Authorization": this.token } });
            const action = usersCalcActions.members(response.data);
            store.dispatch(action);
        } catch (err: any) {
            if (err?.response?.status === 406 && this.canRefreshToken) {
                this.refreshToken();
            } else if (err?.response?.status === 401 && this.canGoToLogin) {
                this.goToLogin();
            }else{
                notify.error();
            }
        }
    }
    public async getVacationsStatistics(): Promise<void> {
        this.token = localStorage.getItem("token") || "";
        if (!this.token) return;
        try {
            const response = await axios.get(appConfig.vacationsStatisticsUrl, { withCredentials: true, headers: { "Authorization": this.token } });
            const action = vacationsStatActions.vacationsStats(response.data);
            store.dispatch(action);
        } catch (err: any) {
            if (err?.response?.status === 406 && this.canRefreshToken) {
                this.refreshToken();
            } else if (err?.response?.status === 401 && this.canGoToLogin) {
                this.goToLogin();
            }else{
                notify.error();
            }
        }
    }
    public async getLikesCount(): Promise<void> {
        this.token = localStorage.getItem("token") || "";
        if (!this.token) return;
        try {
            const response = await axios.get(appConfig.likesCountUrl, { withCredentials: true, headers: { "Authorization": this.token } });
            const data = response.data;
            const action = likesCalcActions.liked(data);
            store.dispatch(action);
        } catch (err: any) {
            if (err?.response?.status === 406 && this.canRefreshToken) {
                this.refreshToken();
            } else if (err?.response?.status === 401 && this.canGoToLogin) {
                this.goToLogin();
            }else{
                notify.error();
            }
        }
    }
    public async getLikesStatistics(): Promise<void> {
        this.token = localStorage.getItem("token") || "";
        if (!this.token) return;
        try {
            const response = await axios.get(appConfig.likesStatisticsUrl, { withCredentials: true, headers: { "Authorization": this.token } });
            const data = response.data;
            const action = likesStatActions.likedStats(data);
            store.dispatch(action);
        } catch (err: any) {
            if (err?.response?.status === 406 && this.canRefreshToken) {
                this.refreshToken();
            } else if (err?.response?.status === 401 && this.canGoToLogin) {
                this.goToLogin();
            }else{
                notify.error();
            }
        }
    }
    private refreshToken() {
        if (!this.canRefreshToken) return;
        this.canRefreshToken = false;
        userService.refreshToken();
        // I assume that token token refreshing will take second other way it will attempt again  
        setTimeout(() => {
            this.getLikesCount();
            this.getLikesStatistics();
            this.getUsersCount();
            this.getVacationsStatistics();
            this.canRefreshToken = true;
        }, 1000);
    }
    private goToLogin() {
        if (!this.canGoToLogin) return;
        this.canGoToLogin = false;
        userService.logout();
        window.location.href = `${window.location.origin}/login`;
        setTimeout(() => {
            this.canGoToLogin = true;
        }, 5000);
    }
}

export const statisticsService: StatisticsService = new StatisticsService();
