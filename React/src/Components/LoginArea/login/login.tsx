import type { JSX } from 'react';
import { useForm } from "react-hook-form";
import { useTitle } from "../../../Hooks/useTitle";
import type { CredentialsModel } from "../../../Models/CredentialsModel";
import { useNavigate } from "react-router-dom";
import { userService } from "../../../Services/UserService";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import Alert from "@mui/material/Alert";
import { useState } from "react";

export function Login(): JSX.Element {
    useTitle("Login");
    const { register, handleSubmit, formState: { errors } } = useForm<CredentialsModel>();
    const navigate = useNavigate();
    const [isError, setIsError] = useState<boolean>(false);
    const [errorText, setErrorText] = useState<string>("");
    async function send(credentials: CredentialsModel) {
        try {
            await userService.login(credentials);
            navigate("/home", { replace: true });
        }
        catch (err: any) {
            let text = "Something went wrong. Please try again.";
            if (err?.response?.status === 400) {
                text = "You can't login with this credentials.";
            } else if (!err?.response) {
                text = "Unable to reach the server. Please check your connection.";
            }
            setErrorText(text);
            setIsError(true);
        }
    }
    return (
        <Container maxWidth="xs">
            <Box
                sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    marginTop: 20,
                }}
            >
                <Typography variant="h4">
                    Sign in
                </Typography>
                <Box component="form" onSubmit={handleSubmit(send)} sx={{ marginTop: 1 }}>
                    <TextField
                        variant="outlined"
                        margin="normal"
                        required
                        fullWidth
                        id="email"
                        label="Email Address"
                        autoComplete="email"
                        autoFocus
                        {...register('email', { required: 'Email is required' })}
                        error={!!errors.email}
                        helperText={errors.email ? errors.email.message : ''}
                    />
                    <TextField
                        variant="outlined"
                        margin="normal"
                        required
                        fullWidth
                        label="Password"
                        type="password"
                        id="password"
                        autoComplete="current-password"
                        {...register('password', { required: 'Password is required', minLength: { value: 4, message: 'Password must be at least 4 characters' } })}
                        error={!!errors.password}
                        helperText={errors.password ? errors.password.message : ''}
                    />
                    <Button
                        type="submit"
                        fullWidth
                        variant="contained"
                        color="primary"
                        sx={{ mt: 3, mb: 2 }}
                    >
                        Sign In
                    </Button>
                </Box>
                {isError ? <Alert severity="warning">{errorText}</Alert> : null}
            </Box>
        </Container>
    );
}
