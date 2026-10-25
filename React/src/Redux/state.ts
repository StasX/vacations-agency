import { configureStore, createSlice, type PayloadAction } from "@reduxjs/toolkit";
import { liked, login, logout, members, vacationsStats } from "./reducers";
import { UserModel } from "../Models/UserModel";
import { TotalLikesModel } from "../Models/TotalLikesModel";
import { TotalUsersModel } from "../Models/TotalUsersModel";
import { VacationsStatisticsModel } from "../Models/VacationsStatisticsModel";
import type { LikesStatisticsModel } from "../Models/LikesStatisticsModel";

export type AppState = {
    user: UserModel;
    usersCalc: TotalUsersModel;
    likesCalc: TotalLikesModel;
    vacationsStat: VacationsStatisticsModel;
    likesStat: LikesStatisticsModel[];
};

const userSlice = createSlice({
    name: "user",
    initialState: new UserModel(),
    reducers: { login, logout }
});

const usersCalcSlice = createSlice({
    name: "usersCalc",
    initialState: new TotalUsersModel(),
    reducers: { members }
});

const likesCalcSlice = createSlice({
    name: "likesCalc",
    initialState: new TotalLikesModel(),
    reducers: { liked }
});

const vacationsStatSlice = createSlice({
    name: "vacationsStat",
    initialState: new VacationsStatisticsModel(),
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
