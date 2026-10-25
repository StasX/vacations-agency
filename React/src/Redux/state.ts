import { configureStore, createSlice, type PayloadAction } from "@reduxjs/toolkit";
import { liked, login, logout, members, vacationsStats } from "./reducers";
import type { UserModel } from "../Models/UserModel";
import type { TotalLikesModel } from "../Models/TotalLikesModel";
import type { TotalUsersModel } from "../Models/TotalUsersModel";
import type { VacationsStatisticsModel } from "../Models/VacationsStatisticsModel";
import type { LikesStatisticsModel } from "../Models/LikesStatisticsModel";

export type AppState = {
    user: UserModel | null;
    usersCalc: TotalUsersModel | null;
    likesCalc: TotalLikesModel | null;
    vacationsStat: VacationsStatisticsModel | null;
    likesStat: LikesStatisticsModel[];
};

const userSlice = createSlice({
    name: "user",
    initialState: null as UserModel | null,
    reducers: { login, logout }
});

const usersCalcSlice = createSlice({
    name: "usersCalc",
    initialState: null as TotalUsersModel | null,
    reducers: { members }
});

const likesCalcSlice = createSlice({
    name: "likesCalc",
    initialState: null as TotalLikesModel | null,
    reducers: { liked }
});

const vacationsStatSlice = createSlice({
    name: "vacationsStat",
    initialState: null as VacationsStatisticsModel | null,
    reducers: { vacationsStats }
});

const likesStatSlice = createSlice({
    name: "likesStat",
    initialState: [] as LikesStatisticsModel[],
    reducers: {
        likedStats(state, action: PayloadAction<LikesStatisticsModel[]>) {
            return action.payload;
        }
    }
});

export const userActions = userSlice.actions;
export const usersCalcActions = usersCalcSlice.actions;
export const likesCalcActions = likesCalcSlice.actions;
export const vacationsStatActions = vacationsStatSlice.actions;
export const likesStatActions = likesStatSlice.actions;
export const store = configureStore<AppState>({
    reducer: {
        user: userSlice.reducer,
        usersCalc: usersCalcSlice.reducer,
        likesCalc: likesCalcSlice.reducer,
        vacationsStat: vacationsStatSlice.reducer,
        likesStat: likesStatSlice.reducer,
    }
});
