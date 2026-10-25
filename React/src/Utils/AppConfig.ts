class AppConfig {
    private host: string = "localhost";
    private port: number = 8000;
    public readonly loginUrl = `http://${this.host}:${this.port}/api/auth/login`;
    public readonly logoutUrl = `http://${this.host}:${this.port}/api/auth/logout`;
    public readonly refreshUrl = `http://${this.host}:${this.port}/api/auth/refresh-token`;
    public readonly usersCountUrl = `http://${this.host}:${this.port}/api/users/total`;
    public readonly vacationsStatisticsUrl = `http://${this.host}:${this.port}/api/vacations/statistics`;
    public readonly likesCountUrl = `http://${this.host}:${this.port}/api/likes/total`;
    public readonly likesStatisticsUrl = `http://${this.host}:${this.port}/api/likes/statistics`;
}

export const appConfig = new AppConfig();

