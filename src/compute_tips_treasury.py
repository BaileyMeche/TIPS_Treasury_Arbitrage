import os
import pandas as pd
import numpy as np
from decouple import config

DATA_DIR = config('DATA_DIR')
OUTPUT_DIR = config("OUTPUT_DIR")


# ------------------------------------------------------------------------------
# Import inflation swap data
# ------------------------------------------------------------------------------
def import_inflation_swap_data():
	swaps_path = os.path.join(DATA_DIR, "treasury_inflation_swaps.xlsx")
	swaps = pd.read_excel(swaps_path, sheet_name="Data", header=0, skiprows=5)

	# might need to change this depending on the excel file we generate
	column_map = {
		swaps.columns[7]: "inf_swap_2y",  # H column
		swaps.columns[10]: "inf_swap_5y",  # K column
		swaps.columns[11]: "inf_swap_10y",  # L column
		swaps.columns[12]: "inf_swap_20y",  # M column
		swaps.columns[13]: "inf_swap_30y"  # N column
	}
	swaps = swaps.rename(columns=column_map)

	for col in ["inf_swap_2y", "inf_swap_5y", "inf_swap_10y", "inf_swap_20y", "inf_swap_30y"]:
		swaps[col] = pd.to_numeric(swaps[col], errors='coerce') / 100

	swaps = swaps.rename(columns={"Dates": "date"})
	swaps = swaps[["date"] + [col for col in swaps.columns if col.startswith("inf")]]

	return swaps


# ------------------------------------------------------------------------------
# Read in zero-coupon TIPS and Treasury yields
# ------------------------------------------------------------------------------
def import_treasury_yields():
	nom_path = os.path.join(DATA_DIR, "feds200628.parquet")
	nom = pd.read_parquet(nom_path)

	if not pd.api.types.is_datetime64_any_dtype(nom['date']):
		nom['date'] = pd.to_datetime(nom['date'], format="%m/%d/%Y")

	for t in [2, 5, 10, 20]:
		col = f"sveny{'0' + str(t) if t < 10 else str(t)}"
		nom[f"nom_zc{t}"] = 1e4 * (np.exp(nom[col] / 100) - 1)  # Put in basis points

	nom = nom[["date"] + [col for col in nom.columns if col.startswith("nom")]]

	return nom


def import_tips_yields():
	real_path = os.path.join(DATA_DIR, "feds200805.parquet")
	real = pd.read_parquet(real_path)

	if not pd.api.types.is_datetime64_any_dtype(real['date']):
		real['date'] = pd.to_datetime(real['date'], format="%Y-%m-%d")

	for t in [2, 5, 10, 20]:
		col = f"tipsy{'0' + str(t) if t < 10 else str(t)}"
		real[f"real_cc{t}"] = real[col] / 100

	real = real[["date"] + [col for col in real.columns if col.startswith("real")]]

	return real


# ------------------------------------------------------------------------------
# Merge all data, compute implied riskless rate from TIPS
# ------------------------------------------------------------------------------
def compute_tips_treasury():
	"""
	Create Constant-Maturity TIPS-Treasury Arbitrage Series

	This script calculates implied risk-free rates and arbitrage opportunities
	between TIPS (Treasury Inflation-Protected Securities) and regular Treasury bonds.
	It combines three data sources:
	1. Inflation swap data from Excel
	2. Zero-coupon Treasury yields (nominal rates)
	3. TIPS yields (real rates)

	The script merges these datasets and computes:
	- Implied risk-free rates derived from TIPS yields plus inflation expectations
	- Arbitrage opportunities between TIPS-derived rates and nominal Treasury rates
	- Missing value indicators to ensure data quality

	Output is saved as a parquet file with all relevant series for analysis.
	"""
	real = import_tips_yields()
	nom = import_treasury_yields()
	swaps = import_inflation_swap_data()

	merged = pd.merge(real, nom, on="date", how="inner")
	merged = pd.merge(merged, swaps, on="date", how="inner")

	# Compute implied riskless rate from TIPS
	missing_indicators = []
	for t in [2, 5, 10, 20]:
		merged[f"tips_treas_{t}_rf"] = 1e4 * (np.exp(merged[f"real_cc{t}"] +
													 np.log(1 + merged[f"inf_swap_{t}y"])) - 1)

		merged[f"mi_{t}"] = merged[f"tips_treas_{t}_rf"].isna().astype(int)
		missing_indicators.append(f"mi_{t}")

		merged[f"arb{t}"] = merged[f"tips_treas_{t}_rf"] - merged[f"nom_zc{t}"]

	merged["miss_count"] = merged[missing_indicators].sum(axis=1)
	merged = merged[merged["miss_count"] < 4]

	merged = merged.drop(missing_indicators + ["miss_count"], axis=1)

	cols_to_keep = (["date"] +
					[col for col in merged.columns if col.startswith("real_")] +
					[col for col in merged.columns if col.startswith("nom_")] +
					[col for col in merged.columns if col.startswith("tips_")])

	merged = merged[cols_to_keep]

	output_path = os.path.join(OUTPUT_DIR, "tips_treasury_implied_rf.parquet")
	merged.to_parquet(output_path, compression="snappy")

	print(f"Data saved to {output_path}")


if __name__ == "__main__":
	compute_tips_treasury()