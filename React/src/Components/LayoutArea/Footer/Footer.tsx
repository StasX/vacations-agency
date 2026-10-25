import type { JSX } from 'react';
import { useState, useEffect } from "react";
import Typography from "@mui/material/Typography";

export function Footer(): JSX.Element {
    const [year, setYear] = useState<number>(2024);

    useEffect(() => {
        const date = new Date();
        setYear(date.getFullYear());
    }, []);

    return (
        <Typography sx={{ textAlign: "center" }}>All rights reserved by Stanislav Mestechkin {year}&copy;</Typography>
    );
}
