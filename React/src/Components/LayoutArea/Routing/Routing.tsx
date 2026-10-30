import { lazy, Suspense, type JSX } from 'react';
import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { useCurrentUser } from "../../../Hooks/useCurrentUser";
import { Login } from "../../LoginArea/login/login";
import { Home } from "../../HomeArea/Home/Home";
import { About } from "../../AboutArea/About/About";
import { PageNotFound } from "../PageNotFound/PageNotFound";

const Statistics = lazy(() => import("../../StatisticsArea/Statistics/Statistics")
    .then(module => ({ default: module.Statistics })));

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
                <Route path="/statistics" element={
                    <Suspense fallback={<p role="status">Loading statistics…</p>}>
                        <Statistics />
                    </Suspense>
                } />
                <Route path="/about" element={<About />} />
            </Route>
            <Route path="*" element={<PageNotFound />} />
        </Routes>
    );
}

