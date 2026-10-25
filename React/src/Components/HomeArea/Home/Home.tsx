import type { JSX } from 'react';
import stat from "../../../Assets/img/stat.png?url";
import { useTitle } from "../../../Hooks/useTitle";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";

export function Home(): JSX.Element {
    useTitle("Home");
    return (
        <Container maxWidth="xl" sx={{ mt: 5 }}>
            <Typography variant="h3">Explanation about the system.</Typography>
            <Grid container sx={{ mt: 10 }}>
                <Grid item md={4} sm={12} >
                    <Box sx={{ margin: "auto" }}>
                        <img src={stat} alt="Statistics" width={400} />
                    </Box>

                </Grid>
                <Grid item md={8} sm={12}>

                    <Typography>Another our system "Vacation agency" allows to user to like / unlike vacations.</Typography>
                    <Typography>Current our system display to administrators statistics about "Vacations agency".</Typography>
                </Grid>
            </Grid>
        </Container>
    );
}
