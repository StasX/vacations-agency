import type { JSX } from 'react';
import { Footer } from "../Footer/Footer";
import { Header } from "../Header/Header";
import { Routing } from "../Routing/Routing";
import css from "./Layout.module.css";

export function Layout(): JSX.Element {
    return (
        <div className={css.Layout}>
            <Header />
            <main>
                <Routing />
            </main>
            <footer>
                <Footer />
            </footer>
        </div>
    );
}

