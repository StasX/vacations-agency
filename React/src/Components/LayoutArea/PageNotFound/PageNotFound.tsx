import type { JSX } from 'react';
import css from "./PageNotFound.module.css";
import { Link } from "react-router-dom";
import notFound from "../../../Assets/img/404.jpg?url";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";

export function PageNotFound(): JSX.Element {
    return (
        <Container maxWidth="xs" className={css.PageNotFound}>
            <Typography variant="h3" sx={{ mt: 10 }}>Page not found!</Typography>
            <img src={notFound} alt="Page not found" />
            <Typography>We sorry but requested page not found!<br />Please back to <Link to="/home">Home</Link>
            </Typography>
        </Container>
    );
}
