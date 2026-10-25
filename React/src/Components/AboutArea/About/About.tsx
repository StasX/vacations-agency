import type { JSX } from 'react';

import { useTitle } from "../../../Hooks/useTitle";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Grid from "@mui/material/Grid";
import css from "./About.module.css";

export function About(): JSX.Element {
    useTitle("About...");
    const frontEndTech: string[] = [
        "React",
        "Bootstrap",
        "JavaScript",
        "TypeScript",
        "Material UI",
        "Redux",
    ];
    const backEndTech: string[] = [
        "Flask",
        "Django",
        "Python",
        "MySQL",
        "Docker",
        "AWS"
    ];
    return (
        <Container maxWidth="md" className={css.About}>
            <Typography variant="h3" sx={{ mt: 3 }}>
                About me:
            </Typography>
            <Typography paragraph sx={{ textAlign: "left", mt: 2 }}>
                My name is Stanislav Mestechkin, and I am a full stack developer...
                I have passion to software developing web applications, and I am will happy to get part in all stages of the project - from planning and development to testing and bug fixing.
            </Typography>
            <Grid container sx={{ mt: 2 }}>
                <Grid item md={6} sm={12}>
                    <Typography>
                        My Email: <a href="mailto:s.mestechkin@gmail.com">s.mestechkin@gmail.com</a>
                    </Typography>
                </Grid>
                <Grid item md={6} sm={12}>
                    <Typography>
                        My Phone number: <a href="tel:+972546279900">+972546279900</a>
                    </Typography>
                </Grid>
            </Grid>
            <Typography variant="h5" sx={{ mt: 3, mb: 4 }}>
                Tools and Technologies Used in current project (But I know more...):
            </Typography>
            <Grid container>
                <Grid item md={6} xs={12}>
                    <Typography variant="h6">Front End:</Typography>
                    <List>
                        {frontEndTech.map((tech, index) => (
                            <ListItem key={index}>
                                <ListItemText primary={tech} style={{ textAlign: 'center' }} />
                            </ListItem>
                        ))}
                    </List>
                </Grid>

                <Grid item md={6} xs={12}>
                    <Typography variant="h6">Back End:</Typography>
                    <List>
                        {backEndTech.map((tech, index) => (
                            <ListItem key={index}>
                                <ListItemText primary={tech} style={{ textAlign: 'center' }} />
                            </ListItem>
                        ))}
                    </List>
                </Grid>
            </Grid>
        </Container>
    );
}
