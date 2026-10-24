import { useEffect, useState } from "react";
import { useRouteProtect } from "../../../Hooks/useRouteProtect";
import { useTitle } from "../../../Hooks/useTitle";
import { statisticsService } from "../../../Services/StatisticsService";
import { Card, CardContent, Grid, Typography } from "@mui/material";
import { PieChart } from "@mui/x-charts";
import { store } from "../../../Redux/state";
import { TotalUsersModel } from "../../../Models/TotalUsersModel";
import { TotalLikesModel } from "../../../Models/TotalLikesModel";
import { VacationsStatisticsModel } from "../../../Models/VacationsStatisticsModel";
import { ChartModel } from "../../../Models/ChartModel";


export function Statistics(): JSX.Element {
    useTitle("Statistics");
    useRouteProtect();

    const [members, setMembers] = useState<TotalUsersModel>();
    const [likes, setLikes] = useState<TotalLikesModel>();
    const [vacationsStatistics, setVacationsStatistics] = useState<VacationsStatisticsModel>();
    const [likesStatistics, setLikesStatistics] = useState<ChartModel[]>([]);
    useEffect(() => {
        const colors: string[] = ["#E64B2F", "#E67640", "#E37507", "#E34E07", "#E63C4A", "#E6D3B1", "#E6A840", "#E6852E", "#E5C66D", "#E39107", "#E66F3C", "#E6DFB1",];
        const statsService = statisticsService;
        statsService.getUsersCount();
        statsService.getLikesCount();
        statsService.getVacationsStatistics();
        statsService.getLikesStatistics();
        setTimeout(() => {
            setMembers(store.getState().usersCalc);
            setLikes(store.getState().likesCalc);
            setVacationsStatistics(store.getState().vacationsStat);
            const likesStats = store.getState().likesStat;
            const stats = likesStats.map((item, index) => {
                return {
                    value: item.likes,
                    label: `${item.destination} (${item.likes})`,
                    color: colors[index],
                };
            });
            setLikesStatistics(stats);
        }, 1000);
    }, []);

    return (
        <Grid container spacing={2} sx={{ textAlign: "center" }}>
            <Grid item md={6} xs={12}>
                <Card variant="outlined" sx={{ width: 600, margin: "5px auto", height: 300, mt: 2, }}>
                    <CardContent>
                        <Typography variant="h5" sx={{ mb: 5 }}>Members count:</Typography>
                        <Typography sx={{ fontWeight: 700, fontSize: "16pt" }}>{members?.total_users}</Typography>
                    </CardContent>
                </Card>
            </Grid>
            <Grid item md={6} xs={12}>
                <Card variant="outlined" sx={{ width: 600, margin: "5px auto", height: 300, mt: 2, }}>
                    <CardContent>
                        <Typography variant="h5" sx={{ mb: 5 }}>Likes count:</Typography>
                        <Typography sx={{ fontWeight: 700, fontSize: "16pt" }}>{likes?.total_likes}</Typography>
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
