import type { PayloadAction } from "@reduxjs/toolkit";
import { UserModel } from "../Models/UserModel";
import type { TotalLikesModel } from "../Models/TotalLikesModel";
import type { TotalUsersModel } from "../Models/TotalUsersModel";
import type { VacationsStatisticsModel } from "../Models/VacationsStatisticsModel";
import type { LikesStatisticsModel } from "../Models/LikesStatisticsModel";

// Login and Token Refresh
export function login(currentState: UserModel | null, action: PayloadAction<UserModel>): UserModel {
    const newState = action.payload;
    return newState;
}

// Logout
export function logout(currentState: UserModel | null, action: PayloadAction): null {
    return null;
}

// Users count
export function members(currentState: TotalUsersModel | null, action: PayloadAction<TotalUsersModel>): TotalUsersModel {
    const newState = action.payload;
    return newState;
}

// Likes count
export function liked(currentState: TotalLikesModel | null, action: PayloadAction<TotalLikesModel>): TotalLikesModel {
    const newState = action.payload;
    return newState;
}

// Vacations statistics
export function vacationsStats(currentState: VacationsStatisticsModel | null, action: PayloadAction<VacationsStatisticsModel>): VacationsStatisticsModel {
    const newState = action.payload;
    return newState;
}

// Likes statistics
export function likedStats(currentState: LikesStatisticsModel[], action: PayloadAction<LikesStatisticsModel[]>): LikesStatisticsModel[] {
    const newState = action.payload;
    return newState;
}
