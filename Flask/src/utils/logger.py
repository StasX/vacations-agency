import logging


class Logger:
    @staticmethod
    def write_log(error):
        """Stream errors to server logs with their original traceback."""
        logging.getLogger(__name__).error(
            'Unhandled application error',
            exc_info=(type(error), error, error.__traceback__),
        )
