import axios from "axios";
import { appConfig } from "../Utils/AppConfig";
import { userService } from "./UserService";
import { likesCalcActions, likesStatActions, store, usersCalcActions, vacationsStatActions } from "../Redux/state";
import { notify } from "../Utils/Notify";
import type { LikesStatisticsModel } from "../Models/LikesStatisticsModel";
import type { TotalUsersModel } from "../Models/TotalUsersModel";
import type { TotalLikesModel } from "../Models/TotalLikesModel";
import type { VacationsStatisticsModel } from "../Models/VacationsStatisticsModel";

function errorStatus(error: unknown): number | undefined {
    return (error as { response?: { status?: number } } | null)?.response?.status;
}

export class StatisticsService {
    private refreshRequest: Promise<boolean> | null = null;
    private logoutRequest: Promise<void> | null = null;

    public getUsersCount(): Promise<void> {
        return this.request<TotalUsersModel>(appConfig.usersCountUrl,
            data => { store.dispatch(usersCalcActions.members(data)); });
    }

    public getVacationsStatistics(): Promise<void> {
        return this.request<VacationsStatisticsModel>(appConfig.vacationsStatisticsUrl,
            data => { store.dispatch(vacationsStatActions.vacationsStats(data)); });
    }

    public getLikesCount(): Promise<void> {
        return this.request<TotalLikesModel>(appConfig.likesCountUrl,
            data => { store.dispatch(likesCalcActions.liked(data)); });
    }

    public getLikesStatistics(): Promise<void> {
        return this.request<unknown>(appConfig.likesStatisticsUrl, data => {
            if (!Array.isArray(data) || !data.every((item): item is LikesStatisticsModel =>
                item !== null && typeof item === "object" &&
                typeof item.destination === "string" &&
                typeof item.likes === "number" && Number.isFinite(item.likes)
            )) {
                throw new Error("Invalid likes statistics response");
            }
            store.dispatch(likesStatActions.likedStats(data));
        });
    }

    private async request<T>(url: string, receive: (data: T) => void): Promise<void> {
        for (let attempt = 0; attempt < 2; attempt++) {
            const token = localStorage.getItem("token");
            if (!token || this.logoutRequest) return;
            try {
                const response = await axios.get<T>(url, {
                    withCredentials: true, headers: { Authorization: token },
                });
                // Ignore a response belonging to a session that has changed.
                if (localStorage.getItem("token") === token && !this.logoutRequest) {
                    receive(response.data);
                }
                return;
            } catch (error: unknown) {
                const currentToken = localStorage.getItem("token");
                if (!currentToken || this.logoutRequest) return;
                if (currentToken !== token) {
                    if (attempt === 0) continue;
                    return;
                }
                const status = errorStatus(error);
                if (status === 406 && attempt === 0) {
                    if (await this.refreshToken()) continue;
                    return;
                }
                if (status === 401) {
                    await this.goToLogin();
                } else {
                    notify.error();
                }
                return;
            }
        }
    }

    private refreshToken(): Promise<boolean> {
        if (!this.refreshRequest) {
            this.refreshRequest = userService.refreshToken().then(
                () => true,
                (error: unknown) => {
                    // UserService clears the session and redirects on refresh 401.
                    if (errorStatus(error) !== 401 && !this.logoutRequest && localStorage.getItem("token")) {
                        notify.error();
                    }
                    return false;
                },
            ).finally(() => { this.refreshRequest = null; });
        }
        return this.refreshRequest;
    }

    private goToLogin(): Promise<void> {
        if (!this.logoutRequest) {
            this.logoutRequest = userService.logout().catch(() => {
                notify.error();
            }).finally(() => {
                window.location.href = `${window.location.origin}/login`;
                this.logoutRequest = null;
            });
        }
        return this.logoutRequest;
    }
}

export const statisticsService = new StatisticsService();
