import type { JSX } from 'react';
import AppBar from '@mui/material/AppBar';
import Box from '@mui/material/Box';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import Container from '@mui/material/Container';
import Button from '@mui/material/Button';
import { useLocation, useNavigate } from 'react-router-dom';
import logo from "../../../Assets/img/logo.png?url";
import Grid from '@mui/material/Grid';
import AccountCircle from '@mui/icons-material/AccountCircle';
import { useEffect, useState } from 'react';
import { store } from '../../../Redux/state';
import { userService } from '../../../Services/UserService';
import { notify } from '../../../Utils/Notify';



export function Header(): JSX.Element {
    const pages = [{ text: "Home", url: "/home" }, { text: "Statistics", url: "/statistics" }, { text: "About", url: "/about" }];

    const location = useLocation();
    const navigate = useNavigate();


    function handleNavigation(url: string) {
        navigate(url);
    };
    async function logout() {
        try {
            await userService.logout();
            navigate("/login", { replace: true });
            setName(undefined);
        } catch (err) {
                notify.error();
        }
    }
    const [name, setName] = useState<string>();
    useEffect(() => {
        // Watch for user changes
        setInterval(() => {
            const user = store.getState().user;
            if (!!user) {
                setName(`${user?.firstName} ${user?.lastName}`);
            }
        }, 1500);

    }, []);

    return (
        <AppBar position="static">
            <Container maxWidth="xl">
                <Toolbar disableGutters>
                    <img src={logo} alt="Logo" />
                    {
                        (!location.pathname.match("/login")) ?
                            (<Box sx={{ flexGrow: 1, display: 'flex' }}>
                                {pages.map((page, index) => (
                                    <Button
                                        key={index}
                                        onClick={() => handleNavigation(page.url)}
                                        sx={{ my: 2, color: 'white', display: 'block' }}
                                    >
                                        {page.text}
                                    </Button>))
                                }
                            </Box>) : (<Box />)}
                    {(!location.pathname.match("/login")) ?
                        (<Box sx={{ flexGrow: 0 }}>
                            <Grid container
                                direction="row"
                                justifyContent="center"
                                alignItems="center">
                                <Grid item xs={10}>
                                    <Typography>{name}</Typography>
                                    <Typography onClick={logout} sx={{ cursor: "pointer" }}>Logout</Typography>
                                </Grid>
                                <Grid item xs={2}>
                                    <AccountCircle sx={{ fontSize: "30pt" }} />
                                </Grid>
                            </Grid>
                        </Box>) : (<Box />)
                    }
                </Toolbar>
            </Container>
        </AppBar>
    );
}
