import { useEffect, useMemo, useSyncExternalStore, type JSX } from "react";
import { useTitle } from "../../../Hooks/useTitle";
import { statisticsService } from "../../../Services/StatisticsService";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";
import { PieChart } from "@mui/x-charts/PieChart";
import { store, type AppState } from "../../../Redux/state";
import type { ChartModel } from "../../../Models/ChartModel";
import type { LikesStatisticsModel } from "../../../Models/LikesStatisticsModel";

const colors = ["#E64B2F", "#E67640", "#E37507", "#E34E07", "#E63C4A", "#E6D3B1", "#E6A840", "#E6852E", "#E5C66D", "#E39107", "#E66F3C", "#E6DFB1"];
const getStatisticsState = (): AppState => store.getState();

export function Statistics(): JSX.Element {
    useTitle("Statistics");

    const { usersCalc: members, likesCalc: likes, vacationsStat: vacationsStatistics, likesStat } =
        useSyncExternalStore<AppState>(store.subscribe, getStatisticsState);
    const likesStatistics = useMemo<ChartModel[]>(() => {
        const statistics: LikesStatisticsModel[] = Array.isArray(likesStat) ? likesStat : [];
        return statistics.map((item: LikesStatisticsModel, index: number) => ({
            value: item.likes,
            label: `${item.destination} (${item.likes})`,
            color: colors[index % colors.length],
        }));
    }, [likesStat]);

    useEffect(() => {
        void statisticsService.getUsersCount();
        void statisticsService.getLikesCount();
        void statisticsService.getVacationsStatistics();
        void statisticsService.getLikesStatistics();
    }, []);

    return (
        <Grid container spacing={2} sx={{ textAlign: "center" }}>
            <Grid item md={6} xs={12}>
                <Card variant="outlined" sx={{ width: 600, margin: "5px auto", height: 300, mt: 2, }}>
                    <CardContent>
                        <Typography variant="h5" sx={{ mb: 5 }}>Members count:</Typography>
                        <Typography sx={{ fontWeight: 700, fontSize: "16pt" }}>{members?.total_users ?? 0}</Typography>
                    </CardContent>
                </Card>
            </Grid>
            <Grid item md={6} xs={12}>
                <Card variant="outlined" sx={{ width: 600, margin: "5px auto", height: 300, mt: 2, }}>
                    <CardContent>
                        <Typography variant="h5" sx={{ mb: 5 }}>Likes count:</Typography>
                        <Typography sx={{ fontWeight: 700, fontSize: "16pt" }}>{likes?.total_likes ?? 0}</Typography>
                    </CardContent>
                </Card>
            </Grid>
            <Grid item md={6} xs={12}>
                <Card variant="outlined" sx={{ width: 600, margin: "5px auto", height: 300, mt: 2, }}>
                    <CardContent>
                        <Typography variant="h5" sx={{ textAlign: "center" }}>Vacations statistics:</Typography>
                        <PieChart
                            series={[
                                {
                                    data: [
                                        { value: vacationsStatistics?.past_vacations ?? 0, label: `Vacations that over (${vacationsStatistics?.past_vacations ?? 0})`, color: "#0787E3" },
                                        { value: vacationsStatistics?.on_going_vacations ?? 0, label: `On going vacations (${vacationsStatistics?.on_going_vacations ?? 0})`, color: "#406CE5" },
                                        { value: vacationsStatistics?.future_vacations ?? 0, label: `Future vacations. (${vacationsStatistics?.future_vacations ?? 0})`, color: "#0742E3" },
                                    ],
                                },
                            ]}
                            width={600}
                            height={200}
                        />
                    </CardContent>
                </Card>
            </Grid>
            <Grid item md={6} xs={12}>
                <Card variant="outlined" sx={{ width: 600, margin: "5px auto", height: 300, mt: 2, }}>
                    <CardContent>
                        <Typography variant="h5" sx={{ textAlign: "center" }}>Likes statistics:</Typography>
                        <PieChart
                            series={[
                                {
                                    data: likesStatistics,
                                },
                            ]}
                            width={600}
                            height={200}
                        />
                    </CardContent>
                </Card>
            </Grid>
        </Grid>
    );
}
