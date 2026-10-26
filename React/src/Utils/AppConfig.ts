class AppConfig {
    public readonly csrfUrl = "/api/auth/csrf";
    public readonly loginUrl = "/api/auth/login";
    public readonly logoutUrl = "/api/auth/logout";
    public readonly refreshUrl = "/api/auth/refresh-token";
    public readonly usersCountUrl = "/api/users/total";
    public readonly vacationsStatisticsUrl = "/api/vacations/statistics";
    public readonly likesCountUrl = "/api/likes/total";
    public readonly likesStatisticsUrl = "/api/likes/statistics";
}

export const appConfig = new AppConfig();

