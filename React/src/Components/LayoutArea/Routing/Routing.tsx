import type { JSX } from 'react';
import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { useCurrentUser } from "../../../Hooks/useCurrentUser";
import { Login } from "../../LoginArea/login/login";
import { Home } from "../../HomeArea/Home/Home";
import { Statistics } from "../../StatisticsArea/Statistics/Statistics";
import { About } from "../../AboutArea/About/About";
import { PageNotFound } from "../PageNotFound/PageNotFound";

function RequireAdmin(): JSX.Element {
    const user = useCurrentUser();
    return user?.role === "Admin" ? <Outlet /> : <Navigate to="/login" replace />;
}

function LoginRoute(): JSX.Element {
    const user = useCurrentUser();
    return user?.role === "Admin" ? <Navigate to="/home" replace /> : <Login />;
}

export function Routing(): JSX.Element {
    return (
        <Routes>
            <Route path="/login" element={<LoginRoute />} />
            <Route element={<RequireAdmin />}>
                <Route index element={<Navigate to="/home" replace />} />
                <Route path="/home" element={<Home />} />
                <Route path="/statistics" element={<Statistics />} />
                <Route path="/about" element={<About />} />
            </Route>
            <Route path="*" element={<PageNotFound />} />
        </Routes>
    );
}
