import { Notyf } from "notyf";
import "notyf/notyf.min.css";

class Notify {
    private notyf = new Notyf({
        duration: 3000,
        position: { x: "center", y: "top" },
        dismissible: true
    });
    public error(): void {
        this.notyf.error("Something went wrong. Please try again");
    }
}

export const notify = new Notify();
