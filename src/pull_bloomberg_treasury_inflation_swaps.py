import os
from xbbg import blp
from decouple import config

OUTPUT_DIR = config("OUTPUT_DIR")
START_DATE = config("START_DATE")
END_DATE = config("END_DATE")

def pull_treasury_inflation_swaps():
    """
    Bloomberg Treasury Inflation Swap Data Retrieval

    This script retrieves historical US Treasury Inflation Swap (TIS) rates from Bloomberg
    using the xbbg package. It fetches daily 'PX_LAST' prices for various maturities
    ranging from 1-month to 30-year, starting from the start date and ending date specified.

    The script:
    1. Connects to Bloomberg via the xbbg package
    2. Pulls historical data for 11 different TIS tickers/maturities
    3. Processes the multi-index dataframe to simplify column structure
    4. Saves the result as a CSV file in the specified output directory

    """
    tickers = [
        "USSWITA BGN Curncy",   # 1M
        "USSWITC BGN Curncy",   # 3M
        "USSWITF BGN Curncy",   # 6M
        "USSWIT1 BGN Curncy",   # 1Y
        "USSWIT2 BGN Curncy",   # 2Y
        "USSWIT3 BGN Curncy",   # 3Y
        "USSWIT4 BGN Curncy",   # 4Y
        "USSWIT5 BGN Curncy",   # 5Y
        "USSWIT10 BGN Curncy",  # 10Y
        "USSWIT20 BGN Curncy",  # 20Y
        "USSWIT30 BGN Curncy",  # 30Y
    ]

    fields = ["PX_LAST"]

    df = blp.bdh(
        tickers=tickers,
        flds=fields,
        start_date=START_DATE,
        end_date=END_DATE
    )
    # df has a Date index and a MultiIndex for columns: (ticker, field).
    # Because fields=["PX_LAST"], we can drop that extra field level for simplicity:
    df.columns = df.columns.droplevel(level=1)  # Remove the "PX_LAST" level

    out_path = os.path.join(OUTPUT_DIR, "treasury_inflation_swaps.csv")
    df.to_csv(out_path, index=True)

    print(f"Treasury Inflation Swaps data saved to: {out_path}")


if __name__ == "__main__":
    pull_treasury_inflation_swaps()
