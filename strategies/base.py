class Strategy:
    def apply(self, df):
        """
        Apply strategy logic to a DataFrame
        and return a raw decision.
        """
        raise NotImplementedError("Strategy must implement apply()")
